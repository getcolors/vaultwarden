"""The graph, the port of io.github.getcolors.vaultwarden.workflow.

Package-owned validation runs first; everything after it — the workflow start
behaviour, all four OpenTofu stages, both Ansible stages and the optional
GitHub credential publication — is ONCE's, reused unmodified.
"""

from __future__ import annotations

from blue import dry_run, progress, tofu
from blue.cli import read_pars
from blue.lifecycle import preflight
from blue.workflow import advice_add, failed, workflow
from package_once_blue import github as once_github
from package_once_blue import tools as once_tools
from package_once_blue.workflow import start_step as once_start_step

from . import tools, validate

DEFAULTS = {"compute-prevent-destroy": True,
            "provider-compute": "digitalocean",
            "provider-dns": "cloudflare",
            "provider-smtp": "resend",
            "provider-backend": "local",
            "workdir": ".colors"}


async def start_step(original: dict, env: dict[str, str] | None = None) -> dict:
    checked = await preflight(
        original, defaults=DEFAULTS, overlay=read_pars, env=env,
        validators=[
            lambda _o, e, _c: validate.env_errors(e),
            lambda o, _e, _c: validate.state_errors(o),
            lambda o, _e, c: (validate.secret_errors(o)
                              if c["real"] and c["event"] == "create" else []),
        ])
    if failed(checked):
        return checked
    return await once_start_step(tools.with_once_shape(checked), env)


async def ansible_cleanup_step(opts: dict) -> dict:
    return await once_tools.ansible_remote_step(await once_tools.ansible_local_step(opts))


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
            "vaultwarden/compute": (once_tools.tofu_compute_step,),
        }.get(step)
    return {
        "vaultwarden/start": (start_step, "vaultwarden/compute", "vaultwarden/smtp"),
        "vaultwarden/compute": (once_tools.tofu_compute_step, "vaultwarden/dns"),
        "vaultwarden/smtp": (once_tools.tofu_smtp_step, "vaultwarden/dns"),
        "vaultwarden/dns": (once_tools.tofu_dns_step, "vaultwarden/smtp-post"),
        "vaultwarden/smtp-post": (once_tools.tofu_smtp_post_step,
                                  "vaultwarden/ansible-local", "vaultwarden/ansible-remote"),
        "vaultwarden/ansible-local": (once_tools.ansible_local_step,),
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
    for step, tool in [("vaultwarden/compute", tools.COMPUTE_TOOL),
                       ("vaultwarden/smtp", tools.SMTP_TOOL),
                       ("vaultwarden/dns", tools.DNS_TOOL),
                       ("vaultwarden/smtp-post", tools.SMTP_POST_TOOL)]:
        wf = advice_add(wf, step, "before", "vaultwarden.workflow/backend",
                        backend_advice(tool))
    return dry_run.advise(progress.advise(wf), side_effecting_steps)


vaultwarden_workflow = create_workflow()
