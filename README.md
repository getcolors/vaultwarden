# vaultwarden

A Green Package Skill that provisions a Basecamp ONCE server and deploys
Vaultwarden with continuous SQLite replication to Cloudflare R2.

The public image `ghcr.io/getcolors/vaultwarden:1.0.0` pins Vaultwarden 1.35.4,
Litestream 0.5.5, and Hivemind 1.1.0. It uses ONCE's `/storage` volume, restores
before startup, serves ONCE's `/up` health contract, sends the initial owner
invitation, disables public signup and the admin endpoint, and verifies a real
replica restore weekly.

```sh
npx skills add getcolors/vaultwarden
cp .agents/skills/package-vaultwarden-green/green ./green
./green build
./green create --dry-run
./green create
```

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
bb test
bb golden
./scripts/launcher.sh
```
