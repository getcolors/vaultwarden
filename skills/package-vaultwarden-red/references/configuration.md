# Configuration

All keys below are non-secret and belong in `colors.yml`.

## Core

- `profile`, `workdir` — project identity and generated work directory.
- `provider-compute`, `provider-dns`, `provider-smtp`, `provider-backend` — ONCE
  provider selections.
- `compute-prevent-destroy` — keep `true` in committed desired state.
- `vaultwarden-host` — public FQDN.
- `vaultwarden-image` — explicit image tag or immutable digest.
- `vaultwarden-repo` — optional `owner/repo` receiving ONCE deployment
  credentials. Omit it when consuming the official
  `ghcr.io/getcolors/vaultwarden` image. A custom image requires a repository
  the operator controls and `COLORS_PAR_GITHUB_TOKEN` with access to it.
- `vaultwarden-owner-email` — initial invitation recipient.
- `vaultwarden-signups-allowed` — must be `false`.
- `vaultwarden-admin-enabled` — must be `false` in converged state.

## Litestream

- `litestream-r2-bucket`, `litestream-r2-endpoint`,
  `litestream-r2-region`, `litestream-r2-prefix` — existing R2 replica.
- `litestream-retention` — snapshot retention, for example `720h`.
- `litestream-snapshot-interval` — snapshot cadence, for example `24h`.
- `litestream-restore-check-oncalendar` — supported weekly schedule,
  `Sun *-*-* 03:00:00`.

## Credentials

Provider credentials follow ONCE. The package additionally requires:

- `COLORS_PAR_LITESTREAM_R2_ACCESS_KEY_ID`
- `COLORS_PAR_LITESTREAM_R2_SECRET_ACCESS_KEY`
- `COLORS_PAR_VAULTWARDEN_ADMIN_TOKEN`

The bootstrap token is used only against the loopback admin endpoint to send the
initial invitation. It is removed from the steady-state Hivemind environment.
Never set `COLORS_PAR_PROFILE`.
