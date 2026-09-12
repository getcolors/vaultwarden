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

# Every record of the colors-compute pin must name the commit green resolves.
compute_sha=$(grep -oE 'colors-compute\.git" :git/sha "[0-9a-f]{40}"' "$root/green/deps.edn" | grep -oE '[0-9a-f]{40}')
[[ -n $compute_sha ]]
grep -q "getcolors/colors-compute#$compute_sha" "$root/red/package.json"
grep -q "getcolors/colors-compute#$compute_sha" "$root/package.json"
grep -q "colors-compute.git@$compute_sha#subdirectory=blue" "$root/blue/pyproject.toml"

# colors-compute-red declares the Red SDK as a peer, not a dependency. Bun
# satisfies a peer only from the install root's own dependencies, so the
# payload PINS the SDK itself; the facade manifest names it only as an
# optional peer plus a devDependency (which keeps the repository root lockfile
# off npm's unrelated `red`), never as a dependency, because Bun cannot
# resolve one GitHub specifier at two depths. Every record must be the commit
# red/package.json tests against, and a cold cache must actually resolve it:
# the working-tree builds above reuse installed node_modules and cannot see a
# missing peer.
red_launcher="$root/skills/package-vaultwarden-red/red"
red_sdk_sha=$(grep -oE '"red": "github:getcolors/red#[0-9a-f]{40}"' "$root/red/package.json" | grep -oE '[0-9a-f]{40}')
[[ -n $red_sdk_sha ]]
grep -q "\"red\": \"github:getcolors/red#$red_sdk_sha\"" "$root/package.json"
grep -q "\"red\": \"github:getcolors/red#$red_sdk_sha\"" "$red_launcher"
mkdir "$tmp/red-cold"
cp "$red_launcher" "$tmp/red-cold/red"; chmod +x "$tmp/red-cold/red"
cp "$root/test/fixtures/colors.yml" "$tmp/red-cold/colors.yml"
# One retry: a cold install fetches GitHub tarballs and a transient fetch
# failure is not a payload defect. Each attempt starts from empty caches.
cold_ok=0
for attempt in 1 2; do
  rm -rf "$tmp/red-cold/xdg" "$tmp/red-cold/bun" "$tmp/red-cold/.colors"
  if (cd "$tmp/red-cold" && XDG_CACHE_HOME="$tmp/red-cold/xdg" BUN_INSTALL_CACHE_DIR="$tmp/red-cold/bun" ./red build >"$tmp/red-cold/build.log" 2>&1); then cold_ok=1; break; fi
done
[[ $cold_ok == 1 ]] || { tail -5 "$tmp/red-cold/build.log" >&2; echo 'launcher: red payload does not build from a cold cache' >&2; exit 1; }
[[ -f "$tmp/red-cold/.colors/vaultwarden-fixture/tofu-compute/nodes/0/node-none.tf.json" ]]
echo 'launcher: all checks passed'
