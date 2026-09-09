#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
state="$root/test/fixtures/colors.yml"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
build_variant() {
  local variant=$1
  shift
  echo "checking $variant"
  (cd "$root/green" && env VAULTWARDEN_LIB_ROOT="$root" COLORS_PAR_WORKDIR="$tmp/$variant/green" "$@" ./green build -f "$state" >/dev/null)
  (cd "$root/red" && env VAULTWARDEN_LIB_ROOT="$root/red" COLORS_PAR_WORKDIR="$tmp/$variant/red" "$@" ./red build -f "$state" >/dev/null)
  (cd "$root/blue" && env COLORS_PAR_WORKDIR="$tmp/$variant/blue" "$@" uv run python -m package_vaultwarden_blue build -f "$state" >/dev/null)
  diff -qr "$tmp/$variant/green" "$tmp/$variant/red"
  diff -qr "$tmp/$variant/green" "$tmp/$variant/blue"
}
for provider in azure aws google digitalocean hcloud vultr yandex oci; do
  build_variant "$provider" "COLORS_PAR_PROVIDER_COMPUTE=$provider"
done
build_variant ipv6-http 'COLORS_PAR_COMPUTE_HTTP_SOURCES=0.0.0.0/0,::/0'
build_variant external-identity COLORS_PAR_SSH_PRIVATE_KEY_PATH=/tmp/fixture-identity
sed '/^.*-ssh-authorized-keys:/d; /^.*-ssh-keys:/d; /^compute-pubkey:/d' "$state" > "$tmp/managed.yml"
state="$tmp/managed.yml"
build_variant managed-r2 COLORS_PAR_PROVIDER_BACKEND=r2
build_variant managed-resend-cloudflare COLORS_PAR_PROVIDER_SMTP=resend COLORS_PAR_PROVIDER_DNS=cloudflare
(cd "$root/green" && bb ../scripts/machine-green.clj "$root/test/fixtures/machine.json") > "$tmp/machine-green"
(cd "$root/red" && bun ../scripts/machine-red.ts "$root/test/fixtures/machine.json") > "$tmp/machine-red"
(cd "$root/blue" && uv run python ../scripts/machine-blue.py "$root/test/fixtures/machine.json") > "$tmp/machine-blue"
python3 - "$tmp" <<'PYTHON'
import json,pathlib,sys
root=pathlib.Path(sys.argv[1])
a=[json.loads((root/('machine-'+color)).read_text()) for color in ['green','red','blue']]
assert a[0]==a[1]==a[2], 'recorded node parameters differ'
PYTHON
echo 'All three colors produce identical artifacts and recorded node parameters.'
