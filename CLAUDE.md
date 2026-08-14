# CLAUDE.md

## Repository

`vaultwarden` is a Green-only Package Skill for one Vaultwarden application on
a single Basecamp ONCE server. It deliberately reuses ONCE's complete compute,
DNS, Resend, Ansible and GitHub deployment stages. Package-owned code validates
the flat Vaultwarden configuration and adapts it to ONCE's application shape.

The repository also builds `ghcr.io/getcolors/vaultwarden:1.0.0`, a pinned
Vaultwarden 1.35.4 image containing Litestream 0.5.5 and Hivemind 1.1.0. ONCE's
persistent volume is `/storage`. Startup restores SQLite before Vaultwarden;
Hivemind then runs Vaultwarden, Litestream, the ONCE `/up` proxy and weekly
restore verification. The admin endpoint is used on loopback only for the first
invitation and is absent in converged steady state.

## Commands

```sh
bb test
bb golden
./scripts/launcher.sh
./green build
./green create --dry-run
./green create                 # requires explicit authorization
./green delete                 # guarded and destructive
```

Never read `.envrc.private`, edit `.colors/`, export `COLORS_PAR_PROFILE`, or
weaken `compute-prevent-destroy`. Build and dry-run are credential-free.

## Coupling

The package pins Green and ONCE in `deps.edn`. Work across checkouts with
`GREEN_LIB_ROOT`, `ONCE_LIB_ROOT`, and `VAULTWARDEN_LIB_ROOT`; final launchers
must use pushed SHAs managed by `bb pin`. A deployment's root launcher is a copy
of `skills/package-vaultwarden-green/green`, not a symlink.

The ONCE reuse surface includes its workflow start behavior, provider registry,
all four OpenTofu stages, both Ansible stages, GitHub deploy-key publication and
the stage directory/state names. `bb golden` protects this coupling. Inspect
diffs before `bb golden:accept`.

## Git

Work on the current branch. Do not commit or push unless explicitly authorized.
