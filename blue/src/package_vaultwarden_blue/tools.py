"""The ONCE adaptation, the port of io.github.getcolors.vaultwarden.tools.

This package renders no template of its own: the four OpenTofu stages and both
Ansible stages are ONCE's, driven through ``package_once_blue.tools``. What
lives here is the adapter that turns the flat Vaultwarden desired state into
ONCE's application shape.
"""

from __future__ import annotations

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
