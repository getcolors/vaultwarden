import {test,expect} from "bun:test";
import {wireFn} from "../src/workflow.ts";
for(const event of ["create","build"])test(`SSH alias precedes remote convergence on ${event}`,()=>{
 const opts={"red/event":event};
 expect(wireFn("vaultwarden/smtp-post",opts)?.slice(1)).toEqual(["vaultwarden/ansible-local"]);
 expect(wireFn("vaultwarden/ansible-local",opts)?.slice(1)).toEqual(["vaultwarden/ansible-remote"]);
});
