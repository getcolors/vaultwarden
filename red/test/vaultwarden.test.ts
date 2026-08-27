import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import type { Opts } from "red/workflow";
import * as tools from "../src/tools.ts";
import * as validate from "../src/validate.ts";
import * as workflow from "../src/workflow.ts";

const fixtureFile = join(import.meta.dir, "../../test/fixtures/colors.yml");

function fixture(overrides: Opts = {}): Opts {
  const parsed = Bun.YAML.parse(readFileSync(fixtureFile, "utf8")) as Opts;
  return { ...parsed, ...overrides };
}

function without(opts: Opts, key: string): Opts {
  const { [key]: _dropped, ...rest } = opts;
  return rest;
}

const matching = (opts: Opts, fragment: string) =>
  validate.stateErrors(opts).filter((e) => e.includes(fragment));

// --- validate ----------------------------------------------------------------

describe("validate", () => {
  test("fixture is valid", () => {
    expect(validate.stateErrors(fixture())).toEqual([]);
  });

  test("reports all invalid fields", () => {
    const errors = validate.stateErrors(fixture({
      "vaultwarden-host": "bad",
      "vaultwarden-repo": "bad",
      "vaultwarden-owner-email": "bad",
      "vaultwarden-signups-allowed": true,
      "vaultwarden-admin-enabled": true,
      "litestream-retention": "forever",
    }));
    expect(errors.length).toBeGreaterThanOrEqual(6);
    for (const fragment of ["host", "repo", "email", "signups", "admin", "retention"]) {
      expect(errors.some((e) => e.includes(fragment))).toBe(true);
    }
  });

  test("image must be pinned", () => {
    expect(matching(fixture({ "vaultwarden-image": "ghcr.io/getcolors/vaultwarden" }),
      "explicit tag").length).toBeGreaterThan(0);
  });

  test("repository is optional only for the official image", () => {
    expect(validate.stateErrors(without(fixture(), "vaultwarden-repo"))).toEqual([]);
    expect(matching(without(fixture({ "vaultwarden-image": "ghcr.io/acme/vaultwarden:1.0.0" }), "vaultwarden-repo"),
      "repo is required").length).toBeGreaterThan(0);
    expect(matching(fixture({ "vaultwarden-repo": "acme/vaultwarden" }), "repo")).toEqual([]);
  });

  test("restore-check schedule must match the image", () => {
    expect(matching(fixture({ "litestream-restore-check-oncalendar": "daily" }),
      "one weekly").length).toBeGreaterThan(0);
  });

  test("profile overlay is refused", () => {
    expect(validate.profilePar).toBe("COLORS_PAR_PROFILE");
    expect(validate.envErrors({ COLORS_PAR_PROFILE: "other" }).length).toBeGreaterThan(0);
    expect(validate.envErrors({})).toEqual([]);
  });

  test("package secrets are named", () => {
    const errors = validate.secretErrors(fixture()).join("\n");
    for (const par of ["COLORS_PAR_LITESTREAM_R2_ACCESS_KEY_ID",
      "COLORS_PAR_LITESTREAM_R2_SECRET_ACCESS_KEY",
      "COLORS_PAR_VAULTWARDEN_ADMIN_TOKEN"]) {
      expect(errors).toContain(par);
    }
  });
});

// --- tools -------------------------------------------------------------------

describe("tools", () => {
  test("adapter builds one once application", () => {
    const opts = tools.withOnceShape(fixture());
    const app = (opts.once as { applications: Record<string, unknown>[] }).applications[0]!;
    const env = (app.env as string[]).join("\n");
    expect(app.host).toBe("vault.example.com");
    expect(app.image).toBe("ghcr.io/getcolors/vaultwarden:1.0.0");
    expect(app.github).toBe("getcolors/vaultwarden");
    expect(env).toContain("DOMAIN=https://vault.example.com");
    expect(env).toContain("SIGNUPS_ALLOWED=false");
    expect(env).toContain("COLORS_PAR_LITESTREAM_R2_ACCESS_KEY_ID");
    expect(env).toContain("COLORS_PAR_VAULTWARDEN_ADMIN_TOKEN");
    expect(env).not.toContain("secret-value");
  });

  test("adapter omits github for the public image", () => {
    const opts = tools.withOnceShape(without(fixture(), "vaultwarden-repo"));
    const app = (opts.once as { applications: Record<string, unknown>[] }).applications[0]!;
    expect(app.image).toBe("ghcr.io/getcolors/vaultwarden:1.0.0");
    expect("github" in app).toBe(false);
  });

  test("once storage path is fixed", () => {
    expect(tools.appEnv(fixture())).toContain("DATA_FOLDER=/storage");
  });
});

// --- workflow ----------------------------------------------------------------

const packageSecrets = {
  COLORS_PAR_LITESTREAM_R2_ACCESS_KEY_ID: "x",
  COLORS_PAR_LITESTREAM_R2_SECRET_ACCESS_KEY: "x",
  COLORS_PAR_VAULTWARDEN_ADMIN_TOKEN: "x",
};

describe("workflow", () => {
  test("build and dry-run need no credentials", async () => {
    expect((await workflow.startStep(fixture({ "red/event": "build" }), {}))["red/exit"]).toBe(0);
    expect((await workflow.startStep(
      fixture({ "red/event": "create", "red/dry-run": true }), {}))["red/exit"]).toBe(0);
  });

  test("real create demands package and provider credentials", async () => {
    const bare = await workflow.startStep(fixture({ "red/event": "create" }), {});
    expect(bare["red/exit"]).toBe(2);
    expect(String(bare["red/err"])).toContain("COLORS_PAR_VAULTWARDEN_ADMIN_TOKEN");
    const withPackage = await workflow.startStep(fixture({ "red/event": "create" }), packageSecrets);
    expect(withPackage["red/exit"]).toBe(2);
    expect(String(withPackage["red/err"])).toContain("COLORS_PAR_NO_INFRA_SMTP_PASSWORD");
  });

  test("official image needs no github credential", async () => {
    const env = { ...packageSecrets, COLORS_PAR_NO_INFRA_SMTP_PASSWORD: "x" };
    const opts = without(fixture({ "red/event": "create" }), "vaultwarden-repo");
    const result = await workflow.startStep(opts, env);
    expect(result["red/exit"]).toBe(0);
    expect(String(result["red/err"] ?? "")).not.toContain("COLORS_PAR_GITHUB_TOKEN");
  });

  test("delete is protected", async () => {
    const result = await workflow.startStep(fixture({ "red/event": "delete" }), {});
    expect(result["red/exit"]).toBe(2);
    expect(String(result["red/err"])).toContain("COMPUTE_PREVENT_DESTROY");
  });

  test("graph reuses once stages and reverses on delete", () => {
    expect(workflow.wireFn("vaultwarden/start", { "red/event": "create" })!.slice(1))
      .toEqual(["vaultwarden/compute", "vaultwarden/smtp"]);
    expect(workflow.wireFn("vaultwarden/start", fixture({ "red/event": "delete" }))!.slice(1))
      .toEqual(["vaultwarden/github"]);
    expect(workflow.wireFn("vaultwarden/dns", { "red/event": "delete" })!.slice(1))
      .toEqual(["vaultwarden/smtp", "vaultwarden/compute"]);
  });

  test("official image omits github from the graph", () => {
    const opts = without(fixture(), "vaultwarden-repo");
    expect(workflow.wireFn("vaultwarden/ansible-remote", { ...opts, "red/event": "create" })!.slice(1))
      .toEqual([]);
    expect(workflow.wireFn("vaultwarden/start", { ...opts, "red/event": "delete" })!.slice(1))
      .toEqual(["vaultwarden/ansible-cleanup"]);
  });
});
