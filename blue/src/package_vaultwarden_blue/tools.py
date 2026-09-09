from __future__ import annotations

from pathlib import Path
from blue.ansible import ansible_with_spec
from blue.scaffold import PRESERVE_JINJA_DELIMITERS

from package_once_blue import tools as once_tools

from .utils import par_lookup

COMPUTE_TOOL = "tofu-compute"
SMTP_TOOL = "tofu-smtp"
DNS_TOOL = "tofu-dns"
SMTP_POST_TOOL = "tofu-smtp-post"


def tool_dir(opts: dict, tool: str) -> str:
    return once_tools.tool_dir(opts, tool)


def backend_credential_env(opts: dict) -> dict[str, str] | None:
    return once_tools.backend_credential_env(opts)


def _text(value: object) -> str:
    """Render a scalar the way green's `str` does: YAML booleans are lowercase.
    Python's str(False) is "False", which would break byte parity."""
    if value is True:
        return "true"
    if value is False:
        return "false"
    return str(value)


def app_env(opts: dict) -> list[str]:
    return [
        f"DOMAIN=https://{opts.get('vaultwarden-host')}",
        "DATA_FOLDER=/storage",
        "ROCKET_ADDRESS=127.0.0.1",
        "ROCKET_PORT=8080",
        f"SIGNUPS_ALLOWED={_text(opts.get('vaultwarden-signups-allowed'))}",
        f"OWNER_EMAIL={opts.get('vaultwarden-owner-email')}",
        f"LITESTREAM_BUCKET={opts.get('litestream-r2-bucket')}",
        f"LITESTREAM_ENDPOINT={opts.get('litestream-r2-endpoint')}",
        f"LITESTREAM_REGION={opts.get('litestream-r2-region')}",
        f"LITESTREAM_PREFIX={opts.get('litestream-r2-prefix')}",
        f"LITESTREAM_RETENTION={opts.get('litestream-retention')}",
        f"LITESTREAM_SNAPSHOT_INTERVAL={opts.get('litestream-snapshot-interval')}",
        f"RESTORE_CHECK_ONCALENDAR={opts.get('litestream-restore-check-oncalendar')}",
        f"LITESTREAM_ACCESS_KEY_ID={par_lookup('litestream-r2-access-key-id')}",
        f"LITESTREAM_SECRET_ACCESS_KEY={par_lookup('litestream-r2-secret-access-key')}",
        f"VAULTWARDEN_BOOTSTRAP_ADMIN_TOKEN={par_lookup('vaultwarden-admin-token')}",
    ]


def with_once_shape(opts: dict) -> dict:
    app: dict = {
        "host": opts.get("vaultwarden-host"),
        "image": opts.get("vaultwarden-image"),
        "env": app_env(opts),
    }
    if opts.get("vaultwarden-repo") is not None:
        app["github"] = opts.get("vaultwarden-repo")
    return {**opts, "once": {"applications": [app]}}


async def ansible_local_step(opts):
    directory = tool_dir(opts, 'ansible-local')
    data = {**opts, **opts.get('once/compute-params', {})}
    root = Path(__file__).parent / 'resources/tools/ansible-local'
    specs = [{'template': {'name': 'tools/ansible-local/' + name, 'content': (root/name).read_text()},
              'target': directory + '/' + name, 'data': data, 'opts': PRESERVE_JINJA_DELIMITERS}
             for name in ['ansible.cfg', 'inventory.ini', 'main.yml']]
    return await ansible_with_spec(opts, specs, dir=directory, inventory='inventory.ini',
        playbooks={'create': 'main.yml', 'delete': 'main.yml'}, extra_vars={
            'host_alias': data.get('profile'),
            'ssh_hosts': [{'name': data.get('profile'), 'ip': data.get('ip'), 'user': data.get('user'),
                           'identity_file': data.get('ssh-private-key-path')}],
            'block_state': 'absent' if opts.get('blue/event') == 'delete' else 'present'})
