import { ansibleWithSpec } from "red/ansible";
import { PRESERVE_JINJA_DELIMITERS } from "red/scaffold";
import cfg from "../resources/tools/ansible-local/ansible.cfg" with { type: "text" };
import inventory from "../resources/tools/ansible-local/inventory.ini" with { type: "text" };
import main from "../resources/tools/ansible-local/main.yml" with { type: "text" };
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


export function ansibleLocalStep(opts: Opts): Promise<Opts> {
  const dir = toolDir(opts, 'ansible-local');
  const data = {...opts, ...(opts['once/compute-params'] as Opts ?? {})};
  const specs = Object.entries({'ansible.cfg':cfg,'inventory.ini':inventory,'main.yml':main}).map(([name,content]) => ({
    template:{name:'tools/ansible-local/'+name,content},target:dir+'/'+name,data,opts:PRESERVE_JINJA_DELIMITERS,
  }));
  return ansibleWithSpec(opts, {dir,inventory:'inventory.ini',playbooks:{create:'main.yml',delete:'main.yml'},extraVars:{
    host_alias:data.profile,ssh_hosts:[{name:data.profile,ip:data.ip,user:data.user,identity_file:data['ssh-private-key-path']}],
    block_state:opts['red/event']==='delete'?'absent':'present',
  }},specs);
}
