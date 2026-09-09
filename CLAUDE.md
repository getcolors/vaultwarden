# CLAUDE.md

## Repository

`vaultwarden` is a three-color package for one Vaultwarden application.
Each color depends directly on colors-compute for VM provisioning, remote
state and SSH key ownership. The package reuses ONCE's SMTP, DNS, remote
application and GitHub stages. It owns the locked local SSH configuration play.

The repository also builds `ghcr.io/getcolors/vaultwarden:1.0.0`, a pinned
Vaultwarden 1.35.4 image containing Litestream 0.5.16 and Hivemind 1.1.0. ONCE's
persistent volume is `/storage`. Startup restores SQLite before Vaultwarden;
Hivemind then runs Vaultwarden, Litestream, the ONCE `/up` proxy and weekly
restore verification. The admin endpoint is used on loopback only for the first
invitation and is absent in converged steady state.

## Layout and commands

The three implementations live in the tri-colour layout, matching `netbird`
and `clickstack`: canonical Clojure in `green/` (`green/bb.edn`,
`green/deps.edn`, `green/src/`, `green/tasks/`, tests under `green/test/clj`),
TypeScript/Bun in `red/`, and Python/uv in `blue/`. Green is canonical: a
behavioural change lands in all three colours in the same commit and passes
`scripts/parity.sh`, which renders the fixture through every colour and diffs
the trees byte for byte. The fixture and the golden are shared across colours
at the repository root. `test/fixtures/` and `test/resources/golden/`. with
`green/test/fixtures` and `green/test/resources` symlinks pointing at them.
Each colour dir holds a launcher symlink to its skill payload (`green/green`,
`red/red`, `blue/blue`).

```sh
cd green && bb test
cd green && bb golden
cd green && bb golden:accept   # regenerate after an intended change. read the diff first
cd red && bun test && bun run typecheck
cd blue && uv run pytest
./scripts/parity.sh            # three colours, byte for byte
./scripts/launcher.sh          # from the repository root
cd green && ./green build
cd green && ./green create --dry-run
cd green && ./green create     # requires explicit authorization
cd green && ./green delete     # guarded and destructive
```

Never read `.envrc.private`, edit `.colors/`, export `COLORS_PAR_PROFILE`, or
weaken `compute-prevent-destroy`. Build and dry-run are credential-free.

## Coupling

The package pins colors-compute in each color. ONCE's application modules
accept the caller's library version. Provider additions require only a compute
version bump. Compute runs before SMTP, and returns the recorded node params
through `once/compute-params` for the application stages. The package start
step performs its own validation and calls colors-compute directly.

The local SSH play must preserve the canonical locked updater from the
workspace SSH config standard. Build parity covers all eight providers,
managed and external keys, both backends, and recorded node parameters.
Legacy `tofu-compute.tfstate` requires explicit migration. No-infra remains
available for SMTP and DNS only.

Use `VAULTWARDEN_LIB_ROOT` (the repository root, for every colour; red also
accepts the `red/` dir directly), `GREEN_LIB_ROOT`, and `ONCE_LIB_ROOT` for
working-tree development. Final launchers use a pushed SHA managed by `bb pin`
(in `green/`), which stamps all three payloads from their unpinned birth forms;
a deployment's root launcher is a copy of its skill payload, not a symlink.

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

Create and build serialize the package-owned SSH alias stage before remote Ansible. A failed local ownership check stops application convergence; GitHub publication remains after remote convergence.

Delete serializes DNS, SMTP, then compute destruction. A validated retired compute journal stops repeated delete at the start step without reading key files or running application cleanup. Credential and destruction-protection checks still apply; absent or unreadable ownership never counts as successful cleanup.
