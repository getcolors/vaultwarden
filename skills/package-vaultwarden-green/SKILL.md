---
name: package-vaultwarden-green
description: Provisions a Basecamp ONCE server and deploys Vaultwarden with Litestream replication to Cloudflare R2. Use when building, dry-running, creating, recovering, or deleting a Vaultwarden deployment managed by Colors.
license: MIT
---

# Vaultwarden with Green

Operate one Vaultwarden deployment from non-secret `colors.yml`. The package
reuses ONCE for compute, Cloudflare DNS, Resend, host convergence, HTTPS and
GitHub deploy keys. Its custom image runs Vaultwarden and Litestream under
Hivemind and satisfies ONCE's `/up` health contract.

## Safety

- Never request or print secrets. Put credentials in gitignored
  `.envrc.private` as `COLORS_PAR_*` variables.
- Never set `COLORS_PAR_PROFILE`.
- Never edit or commit `.colors/`.
- Keep `compute-prevent-destroy: true`. A real delete requires separate explicit
  authorization and a one-run `COLORS_PAR_COMPUTE_PREVENT_DESTROY=false`.
- Run `build` and `create --dry-run` before a real create.
- Do not remove the R2 replica when deleting compute unless separately asked.

Read [references/configuration.md](references/configuration.md) before changing
desired state or running a real lifecycle operation.

## Commands

```sh
./green build
./green create --dry-run
./green create
./green delete
```

A first create sends an invitation to `vaultwarden-owner-email`. Public signup
remains disabled. The admin endpoint exists only during loopback bootstrap and
is disabled before the ONCE health proxy becomes available.

## Recovery

When `/storage/db.sqlite3` is absent, startup restores the newest R2 replica
before Vaultwarden starts. For non-destructive verification, restore to a
separate file and run SQLite `pragma integrity_check`; never restore over a live
database. The image performs this isolated check weekly.
