// The graph, the port of io.github.getcolors.vaultwarden.workflow.
//
// Package-owned validation runs first; everything after it — the workflow
// start behaviour, all four OpenTofu stages, both Ansible stages and the
// optional GitHub credential publication — is ONCE's, reused unmodified.

import { readPars } from "red/cli";
import * as dryRun from "red/dry-run";
import { preflight } from "red/lifecycle";
import * as progress from "red/progress";
import * as tofu from "red/tofu";
import { adviceAdd, failed, workflow, type Opts, type WireDecl } from "red/workflow";
import { startStep as onceStartStep, tools as onceTools } from "package-once-red";
import { onceGithub } from "./once.ts";
import * as tools from "./tools.ts";
import * as validate from "./validate.ts";

export const defaults: Opts = {
  "compute-prevent-destroy": true,
  "provider-compute": "digitalocean",
  "provider-dns": "cloudflare",
  "provider-smtp": "resend",
  "provider-backend": "local",
  workdir: ".colors",
};

export async function startStep(
  original: Opts,
  env: Record<string, string | undefined> = process.env,
): Promise<Opts> {
  const checked = await preflight(original, {
    defaults,
    overlay: readPars,
    validators: [
      (_opts, environment) => validate.envErrors(environment),
      (opts) => validate.stateErrors(opts),
      (opts, _environment, { event, real }) =>
        real && event === "create" ? validate.secretErrors(opts) : [],
    ],
  }, env);
  if (failed(checked)) return checked;
  return onceStartStep(tools.withOnceShape(checked), env);
}

export async function ansibleCleanupStep(opts: Opts): Promise<Opts> {
  return onceTools.ansibleRemoteStep(await onceTools.ansibleLocalStep(opts));
}

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
      "vaultwarden/dns": [onceTools.tofuDnsStep, "vaultwarden/smtp", "vaultwarden/compute"],
      "vaultwarden/smtp": [onceTools.tofuSmtpStep],
      "vaultwarden/compute": [onceTools.tofuComputeStep],
    };
    return graph[step];
  }
  const graph: Record<string, WireDecl> = {
    "vaultwarden/start": [startStep, "vaultwarden/compute", "vaultwarden/smtp"],
    "vaultwarden/compute": [onceTools.tofuComputeStep, "vaultwarden/dns"],
    "vaultwarden/smtp": [onceTools.tofuSmtpStep, "vaultwarden/dns"],
    "vaultwarden/dns": [onceTools.tofuDnsStep, "vaultwarden/smtp-post"],
    "vaultwarden/smtp-post": [onceTools.tofuSmtpPostStep,
      "vaultwarden/ansible-local", "vaultwarden/ansible-remote"],
    "vaultwarden/ansible-local": [onceTools.ansibleLocalStep],
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
  let wf = workflow({ start: "vaultwarden/start", wireFn });
  wf = adviceAdd(wf, "vaultwarden/compute", "before", "vaultwarden.workflow/backend",
    backendAdvice(tools.computeTool));
  wf = adviceAdd(wf, "vaultwarden/smtp", "before", "vaultwarden.workflow/backend",
    backendAdvice(tools.smtpTool));
  wf = adviceAdd(wf, "vaultwarden/dns", "before", "vaultwarden.workflow/backend",
    backendAdvice(tools.dnsTool));
  wf = adviceAdd(wf, "vaultwarden/smtp-post", "before", "vaultwarden.workflow/backend",
    backendAdvice(tools.smtpPostTool));
  return dryRun.advise(progress.advise(wf), sideEffectingSteps);
}

export const vaultwardenWorkflow = create();
