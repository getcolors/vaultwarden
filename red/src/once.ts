// Resolution of ONCE's github module, which its package.json does not export.
//
// ONCE's index surfaces `startStep`, the `tools` namespace and the rest of its
// public API, but the deploy-key/GitHub-environment step lives in
// red/src/github.ts, reachable only by path: the exports map admits bare
// specifiers for "." alone. So the module is resolved from the package entry —
// the same resolved-file technique the clickstack package uses for ONCE's ssh
// module — and typed here with exactly the surface this package consumes.

import { dirname, join } from "node:path";
import type { Opts } from "red/workflow";

export interface OnceGithub {
  githubStep(opts: Opts): Promise<Opts>;
  generateKeys(opts: Opts): Promise<[Array<{privateFile: string}>, string | undefined]>;
  placeholderKeys(opts: Opts): unknown[];
}

const onceEntry = Bun.resolveSync("package-once-red", import.meta.dir);
export const onceGithub = (await import(join(dirname(onceEntry), "github.ts"))) as OnceGithub;
