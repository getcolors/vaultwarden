---
name: package-vaultwarden-green
description: Provisions a Basecamp ONCE server and deploys Vaultwarden with Litestream replication to Cloudflare R2. Use when building, dry-running, creating, recovering, or deleting a Vaultwarden deployment managed by Colors.
license: MIT
---

# Vaultwarden with Green

Operate one Vaultwarden deployment from non-secret `colors.yml`. The package
calls colors-compute directly for the host and remote state. It reuses ONCE for
Cloudflare DNS, Resend, host convergence, HTTPS and
optional GitHub deploy credentials. Its custom image runs Vaultwarden and
Litestream under Hivemind and satisfies ONCE's `/up` health contract. The
official `ghcr.io/getcolors/vaultwarden` image needs no repository or GitHub
token; set `vaultwarden-repo` only for a repository the operator controls.

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

## Compute and SSH

Use `provider-compute` with azure, aws, google, digitalocean, hcloud, vultr,
yandex, or oci. The library owns provider validation, resources, state and keys.
Set `compute-ssh-sources` and `compute-http-sources` explicitly. State uses R2
or S3. Compute `no-infra` and local state are unsupported.

The default keypair is managed at `~/.ssh/<profile>`. Explicit provider key
references select external ownership. The SSH alias is exactly the profile,
with the recorded address and login. External mode adds no IdentityFile or
IdentitiesOnly directive. An explicit `ssh-private-key-path` still reaches
Ansible. Delete reads recorded inventory and removes the alias before compute.
A legacy `tofu-compute.tfstate` requires explicit migration before create.

Create and build serialize the package-owned SSH alias stage before remote Ansible. A failed local ownership check stops application convergence; GitHub publication remains after remote convergence.

Delete serializes DNS, SMTP, then compute destruction. A validated retired compute journal stops repeated delete at the start step without reading key files or running application cleanup. Credential and destruction-protection checks still apply; absent or unreadable ownership never counts as successful cleanup.
