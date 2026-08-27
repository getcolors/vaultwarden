"""Desired-state validation, the port of io.github.getcolors.vaultwarden.validate."""

from __future__ import annotations

import re

from blue.cli import par_name
from blue.providers import placeholder

OWN_REQUIRED = [
    "vaultwarden-host", "vaultwarden-image",
    "vaultwarden-owner-email", "vaultwarden-signups-allowed",
    "vaultwarden-admin-enabled",
    "litestream-r2-bucket", "litestream-r2-endpoint", "litestream-r2-region",
    "litestream-r2-prefix", "litestream-retention", "litestream-snapshot-interval",
    "litestream-restore-check-oncalendar",
]

OWN_SECRETS = [
    "litestream-r2-access-key-id", "litestream-r2-secret-access-key",
    "vaultwarden-admin-token",
]

PROFILE_PAR = par_name("profile")
_host_re = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+$")
_repo_re = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")
_official_image_re = re.compile(r"^ghcr\.io/getcolors/vaultwarden(?::[^@\s]+|@sha256:[0-9a-fA-F]{64})$")
_email_re = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_duration_re = re.compile(r"^[1-9][0-9]*(?:ms|s|m|h)$")


def env_errors(env: dict) -> list[str]:
    if str(env.get(PROFILE_PAR) or ""):
        return [f"{PROFILE_PAR} is set. This package takes profile from colors.yml only."]
    return []


def state_errors(opts: dict) -> list[str]:
    errors: list[str] = []
    for key in ["profile", "workdir", *OWN_REQUIRED]:
        if placeholder(opts.get(key)):
            errors.append(f":{key} is required")
    if not placeholder(opts.get("vaultwarden-host")) and \
            not _host_re.match(str(opts.get("vaultwarden-host"))):
        errors.append(":vaultwarden-host must be a fully qualified hostname")
    if placeholder(opts.get("vaultwarden-repo")) and \
            not _official_image_re.match(str(opts.get("vaultwarden-image"))):
        errors.append(":vaultwarden-repo is required unless :vaultwarden-image uses "
                      "ghcr.io/getcolors/vaultwarden with an explicit tag or digest")
    if not placeholder(opts.get("vaultwarden-repo")) and \
            not _repo_re.match(str(opts.get("vaultwarden-repo"))):
        errors.append(":vaultwarden-repo must be owner/name")
    if not placeholder(opts.get("vaultwarden-owner-email")) and \
            not _email_re.match(str(opts.get("vaultwarden-owner-email"))):
        errors.append(":vaultwarden-owner-email must be an email address")
    if not placeholder(opts.get("vaultwarden-image")) and \
            not re.search(r"[:@]", str(opts.get("vaultwarden-image"))):
        errors.append(":vaultwarden-image must carry an explicit tag or digest")
    if not isinstance(opts.get("vaultwarden-signups-allowed"), bool):
        errors.append(":vaultwarden-signups-allowed must be true or false")
    if opts.get("vaultwarden-signups-allowed") is not False:
        errors.append(":vaultwarden-signups-allowed must remain false; bootstrap uses an invitation")
    if opts.get("vaultwarden-admin-enabled") is not False:
        errors.append(":vaultwarden-admin-enabled must remain false in converged desired state")
    for key in ["litestream-retention", "litestream-snapshot-interval"]:
        if not placeholder(opts.get(key)) and not _duration_re.match(str(opts.get(key))):
            errors.append(f":{key} must be a positive duration such as 24h")
    if not placeholder(opts.get("litestream-restore-check-oncalendar")) and \
            str(opts.get("litestream-restore-check-oncalendar")) != "Sun *-*-* 03:00:00":
        errors.append(":litestream-restore-check-oncalendar must be Sun *-*-* 03:00:00; "
                      "the image supports one weekly restore-check schedule")
    return errors


def secret_errors(opts: dict) -> list[str]:
    return [f"required credential is not set: {par_name(key)}"
            for key in OWN_SECRETS if placeholder(opts.get(key))]
