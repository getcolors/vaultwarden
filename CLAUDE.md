# CLAUDE.md

## Repository

`vaultwarden` is a tri-colour Package Skill (green, red, blue) for one
Vaultwarden application on a single Basecamp ONCE server. It deliberately
reuses ONCE's complete compute, DNS, Resend and Ansible stages, plus optional
GitHub deployment credentials — in every colour. Package-owned code validates
the flat Vaultwarden configuration and adapts it to ONCE's application shape;
the package renders no template of its own.

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
at the repository root — `test/fixtures/` and `test/resources/golden/` — with
`green/test/fixtures` and `green/test/resources` symlinks pointing at them.
Each colour dir holds a launcher symlink to its skill payload (`green/green`,
`red/red`, `blue/blue`).

```sh
cd green && bb test
cd green && bb golden
cd green && bb golden:accept   # regenerate after an intended change — read the diff first
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

The package pins Green and ONCE in `green/deps.edn`, the Red SDK and
`package-once-red` in `red/package.json`, and the Blue SDK and
`package-once-blue` in `blue/pyproject.toml`. All three colours pin ONCE at the
**same rev** (`6952711`) — ONCE's own parity is what guarantees its colours
agree per commit. This package deliberately stays on that older ONCE pin: a
bump would adopt later ONCE behaviour and churn the golden, and is its own
change. `blue/pyproject.toml` carries a `[tool.uv] override-dependencies`
block because `package-once-blue@6952711` pins an older Blue rev (`369c5aa`);
the override makes this package's Blue pin win.

The ONCE reuse surface includes its workflow start behavior, provider registry,
all four OpenTofu stages, both Ansible stages, optional GitHub credential
publication and the stage directory/state names. In red, ONCE's index exports
cover everything but the github module, which `red/src/once.ts` resolves from
the package entry by path; in blue every `package_once_blue` module is
importable directly. `bb golden` protects this coupling. Inspect diffs before
`bb golden:accept`.

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
