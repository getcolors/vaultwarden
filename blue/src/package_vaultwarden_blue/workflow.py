from __future__ import annotations

from blue import dry_run, progress, tofu
from blue.cli import read_pars, par_name
from pathlib import Path
from blue.lifecycle import preflight
from blue.workflow import advice_add, failed, workflow
from package_once_blue import github as once_github
from package_once_blue import tools as once_tools

from . import tools, validate, machine

DEFAULTS = {"compute-prevent-destroy": True,
            "provider-compute": "digitalocean",
            "provider-dns": "cloudflare",
            "provider-smtp": "resend",
            "provider-backend": "r2",
            "workdir": ".colors"}


async def _with_deploy_keys(opts: dict, real: bool) -> dict:
    """Attach the keys ansible-remote installs and the github step publishes.

    Generating them is a create-time side effect, so a build or a dry-run takes
    fixed placeholders instead: a fresh key rendered into the artifact would make
    the build nondeterministic and break byte parity between the colours.
    """
    if real and opts.get("blue/event") == "create":
        keys, err = await once_github.generate_keys(opts)
        if err:
            return {**opts, "blue/exit": 1, "blue/err": err}
        key_dir = {"once/key-dir": str(Path(keys[0]["private-file"]).parent)} if keys else {}
        return {**opts, "blue/exit": 0, "once/deploy-keys": keys, **key_dir}
    return {**opts, "blue/exit": 0, "once/deploy-keys": once_github.placeholder_keys(opts)}


async def _state_output(opts: dict, tool: str) -> dict | None:
    try:
        return (await tofu.outputs(tools.tool_dir(opts, tool), tools.backend_credential_env(opts))).get("params")
    except Exception:
        return None


async def _adopt_existing_state(opts: dict) -> dict:
    loaded = await machine.load(opts)
    if loaded.get('blue/exit'):
        return loaded
    smtp = await _state_output(opts, 'tofu-smtp')
    return {**loaded, **(smtp or {}), **({'once/smtp-params': smtp} if smtp else {})}


async def start_step(original: dict, env: dict[str, str] | None = None) -> dict:
    async def after(opts, _env, context):
        opts = tools.with_once_shape(opts)
        if context['real'] and context['event'] == 'delete':
            return await _adopt_existing_state(opts)
        return await _with_deploy_keys(opts, context['real'])
    return await preflight(
        original, defaults=DEFAULTS, overlay=read_pars, env=env,
        validators=[
            lambda _o, e, _c: validate.env_errors(e),
            lambda o, _e, _c: validate.state_errors(o) + validate.integration_errors(o),
            lambda o, _e, c: validate.credential_errors(o) if c['real'] and c['event'] in ('create', 'delete') else [],
            lambda o, _e, c: validate.secret_errors(o) if c['real'] and c['event'] == 'create' else [],
            lambda o, _e, c: [f"compute destruction is protected; set {par_name('compute-prevent-destroy')}=false to delete"] if c['real'] and c['event'] == 'delete' and o.get('compute-prevent-destroy') else [],
        ], after_validate=after)


async def ansible_cleanup_step(opts: dict) -> dict:
    return await once_tools.ansible_remote_step(await tools.ansible_local_step(opts))


def wire_fn(step: str, run_opts: dict):
    github = run_opts.get("vaultwarden-repo") is not None
    if run_opts.get("blue/event") == "delete":
        return {
            "vaultwarden/start": ((start_step, "vaultwarden/github") if github
                                  else (start_step, "vaultwarden/ansible-cleanup")),
            "vaultwarden/github": (once_github.github_step, "vaultwarden/ansible-cleanup"),
            "vaultwarden/ansible-cleanup": (ansible_cleanup_step, "vaultwarden/smtp-post"),
            "vaultwarden/smtp-post": (once_tools.tofu_smtp_post_step, "vaultwarden/dns"),
            "vaultwarden/dns": (once_tools.tofu_dns_step, "vaultwarden/smtp", "vaultwarden/compute"),
            "vaultwarden/smtp": (once_tools.tofu_smtp_step,),
            "vaultwarden/compute": (machine.step,),
        }.get(step)
    return {
        "vaultwarden/start": (start_step, "vaultwarden/compute"),
        "vaultwarden/compute": (machine.step, "vaultwarden/smtp"),
        "vaultwarden/smtp": (once_tools.tofu_smtp_step, "vaultwarden/dns"),
        "vaultwarden/dns": (once_tools.tofu_dns_step, "vaultwarden/smtp-post"),
        "vaultwarden/smtp-post": (once_tools.tofu_smtp_post_step,
                                  "vaultwarden/ansible-local", "vaultwarden/ansible-remote"),
        "vaultwarden/ansible-local": (tools.ansible_local_step,),
        "vaultwarden/ansible-remote": ((once_tools.ansible_remote_step, "vaultwarden/github")
                                       if github else (once_tools.ansible_remote_step,)),
        "vaultwarden/github": (once_github.github_step,),
    }.get(step)


def backend_advice(tool: str):
    return tofu.conventional_backend_advice(
        dir=lambda o, tool=tool: tools.tool_dir(o, tool),
        key=lambda o, tool=tool: f"{o.get('profile') or 'vaultwarden'}/{tool}.tfstate")


side_effecting_steps = [
    "vaultwarden/compute", "vaultwarden/smtp", "vaultwarden/dns",
    "vaultwarden/smtp-post", "vaultwarden/ansible-local",
    "vaultwarden/ansible-remote", "vaultwarden/ansible-cleanup",
    "vaultwarden/github",
]


def create_workflow():
    wf = workflow(start="vaultwarden/start", wire_fn=wire_fn)
    for step, tool in [("vaultwarden/smtp", tools.SMTP_TOOL),
                       ("vaultwarden/dns", tools.DNS_TOOL),
                       ("vaultwarden/smtp-post", tools.SMTP_POST_TOOL)]:
        wf = advice_add(wf, step, "before", "vaultwarden.workflow/backend",
                        backend_advice(tool))
    return dry_run.advise(progress.advise(wf), side_effecting_steps)


vaultwarden_workflow = create_workflow()
