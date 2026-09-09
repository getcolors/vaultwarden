import { dirname } from "node:path";
import * as machine from "./machine.ts";
import { readPars, parName } from "red/cli";
import * as dryRun from "red/dry-run";
import { preflight } from "red/lifecycle";
import * as progress from "red/progress";
import * as tofu from "red/tofu";
import { adviceAdd, failed, workflow, type Opts, type WireDecl } from "red/workflow";
import { tools as onceTools } from "package-once-red";
import { onceGithub } from "./once.ts";
import * as tools from "./tools.ts";
import * as validate from "./validate.ts";

export const defaults: Opts = {
  "compute-prevent-destroy": true,
  "provider-compute": "digitalocean",
  "provider-dns": "cloudflare",
  "provider-smtp": "resend",
  "provider-backend": "r2",
  workdir: ".colors",
};

async function stateOutput(opts: Opts, tool: string): Promise<Record<string, unknown> | undefined> {
  try {
    const result = await tofu.outputs(tools.toolDir(opts, tool), tools.backendCredentialEnv(opts));
    return result.params as Record<string, unknown> | undefined;
  } catch {
    return undefined;
  }
}

async function adoptExistingState(opts: Opts): Promise<Opts> {
  const loaded = await machine.load(opts);
  if (loaded['red/exit']||loaded['colors-compute/already-destroyed']) return loaded;
  const smtp = await stateOutput(opts,'tofu-smtp');
  return {...loaded,...(smtp??{}),...(smtp?{'once/smtp-params':smtp}:{})};
}

// Attach the keys ansible-remote installs and the github step publishes.
//
// Generating them is a create-time side effect, so a build or a dry-run takes
// fixed placeholders instead: a fresh key rendered into the artifact would make
// the build nondeterministic and break byte parity between the colours.
async function withDeployKeys(opts: Opts, real: boolean): Promise<Opts> {
  if (real && opts["red/event"] === "create") {
    const [keys, err] = await onceGithub.generateKeys(opts);
    if (err) return { ...opts, "red/exit": 1, "red/err": err };
    return {
      ...opts,
      "red/exit": 0,
      "once/deploy-keys": keys,
      ...(keys.length ? { "once/key-dir": dirname(String(keys[0]!.privateFile)) } : {}),
    };
  }
  return { ...opts, "red/exit": 0, "once/deploy-keys": onceGithub.placeholderKeys(opts) };
}

export async function startStep(original: Opts, env: Record<string, string | undefined> = process.env): Promise<Opts> {
  return preflight(original, {
    defaults, overlay: readPars,
    validators: [
      (_o,e) => validate.envErrors(e),
      (o) => [...validate.stateErrors(o), ...validate.integrationErrors(o)],
      (o,_e,c) => c.real && ['create','delete'].includes(String(c.event)) ? validate.credentialErrors(o) : [],
      (o,_e,c) => c.real && c.event === 'create' ? validate.secretErrors(o) : [],
      (o,_e,c) => c.real && c.event === 'delete' && o['compute-prevent-destroy'] ? [`compute destruction is protected; set ${parName('compute-prevent-destroy')}=false to delete`] : [],
    ],
    afterValidate: async (opts,_env,ctx) => {
      opts = tools.withOnceShape(opts);
      return ctx.real && ctx.event === 'delete' ? adoptExistingState(opts) : withDeployKeys(opts,ctx.real);
    },
  },env);
}

export async function ansibleCleanupStep(opts: Opts): Promise<Opts> {
  return onceTools.ansibleRemoteStep(await tools.ansibleLocalStep(opts));
}

export function nextFn(step:string, successors:string[]|null, opts:Opts):[string,Opts][] {return failed(opts)||(step==='vaultwarden/start'&&opts['red/event']==='delete'&&opts['colors-compute/already-destroyed'])?[]:(successors??[]).map(s=>[s,opts]);}
export function wireFn(step: string, runOpts: Opts): WireDecl | undefined {
  const github = runOpts["vaultwarden-repo"] != null;
  if (runOpts["red/event"] === "delete") {
    const graph: Record<string, WireDecl> = {
      "vaultwarden/start": github
        ? [startStep, "vaultwarden/github"]
        : [startStep, "vaultwarden/ansible-cleanup"],
      "vaultwarden/github": [onceGithub.githubStep, "vaultwarden/ansible-cleanup"],
      "vaultwarden/ansible-cleanup": [ansibleCleanupStep, "vaultwarden/smtp-post"],
      "vaultwarden/smtp-post": [onceTools.tofuSmtpPostStep, "vaultwarden/dns"],
      "vaultwarden/dns": [onceTools.tofuDnsStep, "vaultwarden/smtp"],
      "vaultwarden/smtp": [onceTools.tofuSmtpStep, "vaultwarden/compute"],
      "vaultwarden/compute": [machine.step],
    };
    return graph[step];
  }
  const graph: Record<string, WireDecl> = {
    "vaultwarden/start": [startStep, "vaultwarden/compute"],
    "vaultwarden/compute": [machine.step, "vaultwarden/smtp"],
    "vaultwarden/smtp": [onceTools.tofuSmtpStep, "vaultwarden/dns"],
    "vaultwarden/dns": [onceTools.tofuDnsStep, "vaultwarden/smtp-post"],
    "vaultwarden/smtp-post": [onceTools.tofuSmtpPostStep,
      "vaultwarden/ansible-local"],
    "vaultwarden/ansible-local": [tools.ansibleLocalStep, "vaultwarden/ansible-remote"],
    "vaultwarden/ansible-remote": github
      ? [onceTools.ansibleRemoteStep, "vaultwarden/github"]
      : [onceTools.ansibleRemoteStep],
    "vaultwarden/github": [onceGithub.githubStep],
  };
  return graph[step];
}

export function backendAdvice(tool: string) {
  return tofu.conventionalBackendAdvice({
    dir: (opts) => tools.toolDir(opts, tool),
    key: (opts) => `${opts.profile ?? "vaultwarden"}/${tool}.tfstate`,
  });
}

export const sideEffectingSteps = [
  "vaultwarden/compute", "vaultwarden/smtp", "vaultwarden/dns",
  "vaultwarden/smtp-post", "vaultwarden/ansible-local",
  "vaultwarden/ansible-remote", "vaultwarden/ansible-cleanup",
  "vaultwarden/github",
];

function create() {
  let wf = workflow({ start: "vaultwarden/start", wireFn, nextFn });
  wf = adviceAdd(wf, "vaultwarden/smtp", "before", "vaultwarden.workflow/backend",
    backendAdvice(tools.smtpTool));
  wf = adviceAdd(wf, "vaultwarden/dns", "before", "vaultwarden.workflow/backend",
    backendAdvice(tools.dnsTool));
  wf = adviceAdd(wf, "vaultwarden/smtp-post", "before", "vaultwarden.workflow/backend",
    backendAdvice(tools.smtpPostTool));
  return dryRun.advise(progress.advise(wf), sideEffectingSteps);
}

export const vaultwardenWorkflow = create();
