#!/usr/bin/env bash
set -euo pipefail

# One desired state, three colours, byte for byte. golden.sh is green's
# regression net against the committed golden; this is the net across colours:
# the one fixture is rendered by green, red, and blue into separate work
# directories and the trees must be identical. This package carries no template
# tree of its own — every rendered file is ONCE's, whose own parity guarantees
# its colours agree per pinned commit — so the rendered trees are the whole
# surface.
#
# Renders resolve each colour's package from this working tree (the
# VAULTWARDEN_LIB_ROOT overrides), while green, once, red, and blue stay on
# their pins — a change that lands here passes parity before it is pushed or
# pinned anywhere.

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
state="$root/test/fixtures/colors.yml"
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT

(cd "$root/green" && env VAULTWARDEN_LIB_ROOT="$root" \
  COLORS_PAR_WORKDIR="$tmp/green" ./green build -f "$state" >/dev/null)
(cd "$root/red" && env VAULTWARDEN_LIB_ROOT="$root/red" \
  COLORS_PAR_WORKDIR="$tmp/red" ./red build -f "$state" >/dev/null)
(cd "$root/blue" && env COLORS_PAR_WORKDIR="$tmp/blue" \
  uv run python -m package_vaultwarden_blue build -f "$state" >/dev/null)
diff -r "$tmp/green" "$tmp/red"
diff -r "$tmp/green" "$tmp/blue"

echo "green, red, and blue Vaultwarden artifacts are byte-identical"
