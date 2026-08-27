// The ONCE adaptation, the port of io.github.getcolors.vaultwarden.tools.
//
// This package renders no template of its own: the four OpenTofu stages and
// both Ansible stages are ONCE's, driven through the `tools` namespace ONCE
// exports. What lives here is the adapter that turns the flat Vaultwarden
// desired state into ONCE's application shape.

import { tools as onceTools } from "package-once-red";
import type { Opts } from "red/workflow";
import { parLookup } from "./utils.ts";

export const computeTool = "tofu-compute";
export const smtpTool = "tofu-smtp";
export const dnsTool = "tofu-dns";
export const smtpPostTool = "tofu-smtp-post";

export function toolDir(opts: Opts, tool: string): string {
  return onceTools.toolDir(opts, tool);
}

export function backendCredentialEnv(opts: Opts): Record<string, string> | undefined {
  return onceTools.backendCredentialEnv(opts);
}

export function appEnv(opts: Opts): string[] {
  return [
    `DOMAIN=https://${opts["vaultwarden-host"]}`,
    "DATA_FOLDER=/storage",
    "ROCKET_ADDRESS=127.0.0.1",
    "ROCKET_PORT=8080",
    `SIGNUPS_ALLOWED=${opts["vaultwarden-signups-allowed"]}`,
    `OWNER_EMAIL=${opts["vaultwarden-owner-email"]}`,
    `LITESTREAM_BUCKET=${opts["litestream-r2-bucket"]}`,
    `LITESTREAM_ENDPOINT=${opts["litestream-r2-endpoint"]}`,
    `LITESTREAM_REGION=${opts["litestream-r2-region"]}`,
    `LITESTREAM_PREFIX=${opts["litestream-r2-prefix"]}`,
    `LITESTREAM_RETENTION=${opts["litestream-retention"]}`,
    `LITESTREAM_SNAPSHOT_INTERVAL=${opts["litestream-snapshot-interval"]}`,
    `RESTORE_CHECK_ONCALENDAR=${opts["litestream-restore-check-oncalendar"]}`,
    `LITESTREAM_ACCESS_KEY_ID=${parLookup("litestream-r2-access-key-id")}`,
    `LITESTREAM_SECRET_ACCESS_KEY=${parLookup("litestream-r2-secret-access-key")}`,
    `VAULTWARDEN_BOOTSTRAP_ADMIN_TOKEN=${parLookup("vaultwarden-admin-token")}`,
  ];
}

export function withOnceShape(opts: Opts): Opts {
  const app: Record<string, unknown> = {
    host: opts["vaultwarden-host"],
    image: opts["vaultwarden-image"],
    env: appEnv(opts),
  };
  if (opts["vaultwarden-repo"] != null) app.github = opts["vaultwarden-repo"];
  return { ...opts, once: { applications: [app] } };
}
