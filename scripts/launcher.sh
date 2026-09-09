#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
launcher="$root/skills/package-vaultwarden-green/green"
grep -q 'io.github.getcolors.vaultwarden.workflow/workflow' "$launcher"
grep -qE '\(def \^:private vaultwarden-sha (nil|"[0-9a-f]{40}")\)' "$launcher"
[[ -L "$root/green/green" ]] && [[ $(readlink "$root/green/green") == ../skills/package-vaultwarden-green/green ]]
[[ -L "$root/red/red" ]] && [[ $(readlink "$root/red/red") == ../skills/package-vaultwarden-red/red ]]
[[ -L "$root/blue/blue" ]] && [[ $(readlink "$root/blue/blue") == ../skills/package-vaultwarden-blue/blue ]]
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
cp "$launcher" "$tmp/green"; chmod +x "$tmp/green"
cp "$root/test/fixtures/colors.yml" "$tmp/colors.yml"
(cd "$tmp" && VAULTWARDEN_LIB_ROOT="$root" ./green build >/dev/null)
[[ -f "$tmp/.colors/vaultwarden-fixture/tofu-compute/nodes/0/node-none.tf.json" ]]
mkdir -p "$tmp/a/b"
(cd "$tmp/a/b" && VAULTWARDEN_LIB_ROOT="$root" ../../green build >/dev/null)
out=$(cd "$tmp" && VAULTWARDEN_LIB_ROOT="$root" COLORS_PAR_PROFILE=wrong ./green build 2>&1 || true)
grep -q COLORS_PAR_PROFILE <<<"$out"
[[ ! -d "$tmp/.colors/wrong" ]]
echo 'launcher: all checks passed'
