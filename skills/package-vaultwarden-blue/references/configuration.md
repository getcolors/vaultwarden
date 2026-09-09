# Configuration

All keys below are non-secret and belong in `colors.yml`.

## Core

- `profile`, `workdir`: project identity and generated work directory.
- `provider-compute`, `provider-dns`, `provider-smtp`, `provider-backend`: ONCE
  provider selections. Compute and backend are library selections.
- `compute-prevent-destroy`: keep `true` in committed desired state.
- `vaultwarden-host`: public FQDN.
- `vaultwarden-image`: explicit image tag or immutable digest.
- `vaultwarden-repo`: optional `owner/repo` receiving ONCE deployment
  credentials. Omit it when consuming the official
  `ghcr.io/getcolors/vaultwarden` image. A custom image requires a repository
  the operator controls and `COLORS_PAR_GITHUB_TOKEN` with access to it.
- `vaultwarden-owner-email`: initial invitation recipient.
- `vaultwarden-signups-allowed`: must be `false`.
- `vaultwarden-admin-enabled`: must be `false` in converged state.

## Litestream

- `litestream-r2-bucket`, `litestream-r2-endpoint`,
  `litestream-r2-region`, `litestream-r2-prefix`: existing R2 replica.
- `litestream-retention`: snapshot retention, for example `720h`.
- `litestream-snapshot-interval`: snapshot cadence, for example `24h`.
- `litestream-restore-check-oncalendar`: supported weekly schedule,
  `Sun *-*-* 03:00:00`.

## Credentials

Compute credentials follow colors-compute. Azure, AWS and Google use ambient
credentials. OCI uses `oci-config-file-profile` from `~/.oci/config`. The token
providers use `COLORS_PAR_DO_TOKEN`, `COLORS_PAR_HCLOUD_TOKEN`,
`COLORS_PAR_VULTR_API_KEY`, or `COLORS_PAR_YANDEX_TOKEN`, respectively. R2 state
uses `COLORS_PAR_R2_ACCESS_KEY_ID` and `COLORS_PAR_R2_SECRET_ACCESS_KEY`; S3
state uses the ambient AWS credential chain. Resend uses
`COLORS_PAR_RESEND_API_KEY` and `COLORS_PAR_RESEND_PASSWORD`. External SMTP
uses `COLORS_PAR_NO_INFRA_SMTP_PASSWORD`. Cloudflare DNS uses
`COLORS_PAR_CLOUDFLARE_API_TOKEN`. GitHub is required only for a named repo.

The package additionally requires these create-time credentials:

- `COLORS_PAR_LITESTREAM_R2_ACCESS_KEY_ID`
- `COLORS_PAR_LITESTREAM_R2_SECRET_ACCESS_KEY`
- `COLORS_PAR_VAULTWARDEN_ADMIN_TOKEN`

The bootstrap token is used only against the loopback admin endpoint to send the
initial invitation. It is removed from the steady-state Hivemind environment.
Never set `COLORS_PAR_PROFILE`.

## Host and remote state

Select a supported VM provider and its library parameters. Set
`compute-ssh-sources` and `compute-http-sources` to the permitted CIDR lists.
The host receives TCP 22, 80 and 443. Providers that require a network use the
library network stages; providers with public singleton support need no owned
private network.

Use `provider-backend: r2` with `r2-bucket` and `r2-endpoint`, or
`provider-backend: s3` with `s3-bucket` and `s3-region`. Compute state uses
`<profile>/compute/shared.tfstate` and per-node state keys. SMTP and DNS retain
their separate stage keys. The local coordination journal records ownership
and node inventory. Existing compute state must be migrated explicitly; a
new create refuses the legacy state key.

Omit key references for a managed keypair, or supply the provider's external
key reference. `ssh-keygen: false` opts out of generation. The package does
not remove external keys. A provider addition changes the colors-compute
version only; no Vaultwarden provider template or branch is needed.
