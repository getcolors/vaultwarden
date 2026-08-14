#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
launcher="$root/skills/package-vaultwarden-green/green"
[[ -L "$root/green" ]] && [[ $(readlink "$root/green") == skills/package-vaultwarden-green/green ]]
grep -q 'io.github.getcolors.vaultwarden.workflow/workflow' "$launcher"
grep -q 'def \^:private vaultwarden-sha' "$launcher"
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
cp "$launcher" "$tmp/green"; chmod +x "$tmp/green"
cp "$root/test/fixtures/colors.yml" "$tmp/colors.yml"
(cd "$tmp" && VAULTWARDEN_LIB_ROOT="$root" ./green build >/dev/null)
[[ -f "$tmp/.colors/vaultwarden-fixture/tofu-compute/main.tf" ]]
mkdir -p "$tmp/a/b"
(cd "$tmp/a/b" && VAULTWARDEN_LIB_ROOT="$root" ../../green build >/dev/null)
out=$(cd "$tmp" && VAULTWARDEN_LIB_ROOT="$root" COLORS_PAR_PROFILE=wrong ./green build 2>&1 || true)
grep -q COLORS_PAR_PROFILE <<<"$out"
[[ ! -d "$tmp/.colors/wrong" ]]
echo 'launcher: all checks passed'
