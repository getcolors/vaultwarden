# CLAUDE.md

## Repository

`vaultwarden` is a Green-only Package Skill for one Vaultwarden application on
a single Basecamp ONCE server. It deliberately reuses ONCE's complete compute,
DNS, Resend and Ansible stages, plus optional GitHub deployment credentials. Package-owned code validates
the flat Vaultwarden configuration and adapts it to ONCE's application shape.

The repository also builds `ghcr.io/getcolors/vaultwarden:1.0.0`, a pinned
Vaultwarden 1.35.4 image containing Litestream 0.5.16 and Hivemind 1.1.0. ONCE's
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
all four OpenTofu stages, both Ansible stages, optional GitHub credential publication and
the stage directory/state names. `bb golden` protects this coupling. Inspect
diffs before `bb golden:accept`.

## Documentation

`index.html` is this repository's landing page and carries two analytics tags:
GA4 measurement ID `G-4VKP1WY4QJ`, whose explicit `page_title` must exactly
equal the decoded HTML `<title>` and stay distinct and stable so one Analytics
property can separate repositories, and the self-hosted Rybbit snippet
`<script src="https://rybbit.getcolors.ai/api/script.js" data-site-id="9fb9c41a6d49" defer></script>`,
which shares one site ID across every page because `getcolors.github.io/<repo>/`
paths already encode the repository. Never add one tag without the other.

## Git

Work on the current branch. Do not commit or push unless explicitly authorized.
