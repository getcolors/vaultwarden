// Launcher contract and small helpers, the port of
// io.github.getcolors.vaultwarden.utils.

// Bump on any change a launcher pinned to an older commit could not survive.
export const contract = 2;

export function registrableDomain(host: unknown): string {
  return String(host ?? "").split(".").slice(-2).join(".");
}

// The Ansible-side environment lookup for a credential key: the secret is
// resolved on the operator's machine at play time and never enters a rendered
// artifact.
export function parLookup(key: string): string {
  return `{{ lookup('env','COLORS_PAR_${key.replaceAll("-", "_").toUpperCase()}') }}`;
}
