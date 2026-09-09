# vaultwarden

A package in Green, Red and Blue that provisions a Basecamp ONCE server and deploys Vaultwarden with
continuous SQLite replication to Cloudflare R2. Green is canonical; the three
implementations render byte-identical artifacts.

The public image `ghcr.io/getcolors/vaultwarden:1.0.0` pins Vaultwarden 1.35.4,
Litestream 0.5.16, and Hivemind 1.1.0. It uses ONCE's `/storage` volume, restores
before startup, serves ONCE's `/up` health contract, sends the initial owner
invitation, disables public signup and the admin endpoint, and verifies a real
replica restore weekly.

The official public image needs no GitHub access. Omit `vaultwarden-repo` to
consume it directly. Set `vaultwarden-repo` only when a repository you control
should receive ONCE deployment credentials; custom images require that explicit
repository.

```sh
npx skills add getcolors/vaultwarden
cp .agents/skills/package-vaultwarden-green/green ./green
./green build
./green create --dry-run
./green create
```

The red and blue skills (`package-vaultwarden-red`, `package-vaultwarden-blue`)
install the same way and run the same verbs through `./red` and `./blue`.

Desired state is `colors.yml`; credentials are `COLORS_PAR_*` values sourced
from a gitignored `.envrc.private`. Never set `COLORS_PAR_PROFILE`.

## Recovery

A fresh container automatically restores `/storage/db.sqlite3` from Litestream
when the database is absent. To test recovery without replacing live data:

```sh
litestream restore -config /etc/vaultwarden/litestream.yml \
  -o /tmp/vaultwarden-restore.db /storage/db.sqlite3
sqlite3 /tmp/vaultwarden-restore.db 'pragma integrity_check;'
```

The container runs this isolated check every Sunday at 03:00 UTC and records a
successful timestamp in `/storage/.last-restore-check`.

## Development

```sh
cd green && bb test && bb golden
cd red && bun test && bun run typecheck
cd blue && uv run pytest
./scripts/parity.sh
./scripts/launcher.sh
```

## Compute library

All three colors call colors-compute directly. The library supports Azure,
AWS, Google, DigitalOcean, Hetzner, Vultr, Yandex and OCI, and stores state in
R2 or S3. Provider additions require only a library version bump. Set explicit
SSH and HTTP source CIDRs. Compute no-infra is unsupported. Existing compute
state requires migration before the new lifecycle can create resources.

Create and build serialize the package-owned SSH alias stage before remote Ansible. A failed local ownership check stops application convergence; GitHub publication remains after remote convergence.

Delete serializes DNS, SMTP, then compute destruction. A validated retired compute journal stops repeated delete at the start step without reading key files or running application cleanup. Credential and destruction-protection checks still apply; absent or unreadable ownership never counts as successful cleanup.
