"""Launcher contract and small helpers, the port of
io.github.getcolors.vaultwarden.utils."""

from __future__ import annotations

# Bump on any change a launcher pinned to an older commit could not survive.
CONTRACT = 2


def registrable_domain(host: object) -> str:
    return ".".join(str(host or "").split(".")[-2:])


def par_lookup(key: str) -> str:
    """The Ansible-side environment lookup for a credential key: the secret is
    resolved on the operator's machine at play time and never enters a rendered
    artifact."""
    return "{{ lookup('env','COLORS_PAR_%s') }}" % key.replace("-", "_").upper()
