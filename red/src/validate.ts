import { credential_requirements } from "colors-compute-red";
import { providers } from "package-once-red";
import * as machine from "./machine.ts";
// Desired-state validation, the port of io.github.getcolors.vaultwarden.validate.

import { parName } from "red/cli";
import { placeholder } from "red/providers";
import type { Opts } from "red/workflow";

export const ownRequired = [
  "vaultwarden-host", "vaultwarden-image",
  "vaultwarden-owner-email", "vaultwarden-signups-allowed",
  "vaultwarden-admin-enabled",
  "litestream-r2-bucket", "litestream-r2-endpoint", "litestream-r2-region",
  "litestream-r2-prefix", "litestream-retention", "litestream-snapshot-interval",
  "litestream-restore-check-oncalendar",
];

export const ownSecrets = [
  "litestream-r2-access-key-id", "litestream-r2-secret-access-key",
  "vaultwarden-admin-token",
];

export const profilePar = parName("profile");
const hostRe = /^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+$/;
const repoRe = /^[A-Za-z0-9._-]+\/[A-Za-z0-9._-]+$/;
const officialImageRe = /^ghcr\.io\/getcolors\/vaultwarden(?::[^@\s]+|@sha256:[0-9a-fA-F]{64})$/;
const emailRe = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const durationRe = /^[1-9][0-9]*(?:ms|s|m|h)$/;

export function envErrors(env: Record<string, string | undefined>): string[] {
  return String(env[profilePar] ?? "").length
    ? [`${profilePar} is set. This package takes profile from colors.yml only.`]
    : [];
}

export function stateErrors(opts: Opts): string[] {
  const errors: string[] = [];
  for (const key of ["profile", "workdir", ...ownRequired]) {
    if (placeholder(opts[key])) errors.push(`:${key} is required`);
  }
  if (!placeholder(opts["vaultwarden-host"]) && !hostRe.test(String(opts["vaultwarden-host"]))) {
    errors.push(":vaultwarden-host must be a fully qualified hostname");
  }
  if (placeholder(opts["vaultwarden-repo"]) && !officialImageRe.test(String(opts["vaultwarden-image"]))) {
    errors.push(":vaultwarden-repo is required unless :vaultwarden-image uses ghcr.io/getcolors/vaultwarden with an explicit tag or digest");
  }
  if (!placeholder(opts["vaultwarden-repo"]) && !repoRe.test(String(opts["vaultwarden-repo"]))) {
    errors.push(":vaultwarden-repo must be owner/name");
  }
  if (!placeholder(opts["vaultwarden-owner-email"]) && !emailRe.test(String(opts["vaultwarden-owner-email"]))) {
    errors.push(":vaultwarden-owner-email must be an email address");
  }
  if (!placeholder(opts["vaultwarden-image"]) && !/[:@]/.test(String(opts["vaultwarden-image"]))) {
    errors.push(":vaultwarden-image must carry an explicit tag or digest");
  }
  if (typeof opts["vaultwarden-signups-allowed"] !== "boolean") {
    errors.push(":vaultwarden-signups-allowed must be true or false");
  }
  if (opts["vaultwarden-signups-allowed"] !== false) {
    errors.push(":vaultwarden-signups-allowed must remain false; bootstrap uses an invitation");
  }
  if (opts["vaultwarden-admin-enabled"] !== false) {
    errors.push(":vaultwarden-admin-enabled must remain false in converged desired state");
  }
  for (const key of ["litestream-retention", "litestream-snapshot-interval"]) {
    if (!placeholder(opts[key]) && !durationRe.test(String(opts[key]))) {
      errors.push(`:${key} must be a positive duration such as 24h`);
    }
  }
  if (!placeholder(opts["litestream-restore-check-oncalendar"]) &&
      String(opts["litestream-restore-check-oncalendar"]) !== "Sun *-*-* 03:00:00") {
    errors.push(":litestream-restore-check-oncalendar must be Sun *-*-* 03:00:00; the image supports one weekly restore-check schedule");
  }
  return errors;
}

export function secretErrors(opts: Opts): string[] {
  return ownSecrets
    .filter((key) => placeholder(opts[key]))
    .map((key) => `required credential is not set: ${parName(key)}`);
}

export function integrationErrors(opts: Opts): string[] {
  const errors=machine.errors(opts);
  for(const slot of ['provider-smtp','provider-dns']){
    const entry=providers[slot]?.[String(opts[slot])];
    if(!entry)errors.push('unsupported '+slot);
    else for(const key of entry.required)if(placeholder(opts[key]))errors.push(':'+key+' is required');
  }
  return errors;
}
export function credentialErrors(opts: Opts): string[] {
  const variables=new Set(credential_requirements(opts));
  for(const slot of ['provider-smtp','provider-dns'])for(const key of providers[slot]?.[String(opts[slot])]?.secrets??[])variables.add(parName(key));
  if(opts['vaultwarden-repo']!=null)variables.add('COLORS_PAR_GITHUB_TOKEN');
  return [...variables].sort().filter(variable=>placeholder(opts[variable.slice(11).toLowerCase().replaceAll('_','-')])).map(variable=>'required credential is not set: '+variable);
}
