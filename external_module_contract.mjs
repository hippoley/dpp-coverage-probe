/** Invoke the pinned Apache-2.0 OpenDPP validation API, not a reimplementation. */
import {readFileSync, mkdirSync, writeFileSync} from "node:fs";
import {resolve} from "node:path";
import {pathToFileURL} from "node:url";

const PIN = "20211ecc2b63eb7664c571a8d629aeeed364491e";
const LABELS = ["primary", "replay"];
const TYPES = ["baseline", "mutant"];
const result = {schema:"external-module-contract-v1", upstream_commit:PIN, module:"OpenDPP validateInterop (AJV 8)", overall:"NOT_COMPLETED", checks:[], scope:"AAS JSON Schema structural conformance only"};
try {
  const report = JSON.parse(readFileSync("gate-b-evidence/report.json","utf8"));
  for (const [idx,label] of LABELS.entries()) {
    const dir = idx===0 ? "/tmp/opendpp" : "/tmp/opendpp-replay";
    const {execFileSync} = await import("node:child_process");
    const head = execFileSync("git",["-C",dir,"rev-parse","HEAD"],{encoding:"utf8"}).trim();
    if (head !== PIN || report[label]?.commit !== PIN) throw Error(label+": upstream pin mismatch");
    const mod = await import(pathToFileURL(resolve(dir,"validate/validate.mjs")).href);
    if (typeof mod.validateInterop !== "function") throw Error(label+": no validateInterop function");
    for (const kind of TYPES) {
      const filename = `gate-b-evidence/${label}-${kind}.json`;
      const payload = JSON.parse(readFileSync(filename,"utf8"));
      const observed = mod.validateInterop("aas",payload);
      if (typeof observed.valid !== "boolean") throw Error(label+": invalid API return contract");
      const cliExit = report[label]?.legs?.[kind]?.exit_code;
      const agreement = observed.valid === (cliExit === 0) && (cliExit===0 || cliExit===1);
      result.checks.push({label,kind,api_valid:observed.valid,cli_exit_code:cliExit,agreement,
                          api_error_count:Array.isArray(observed.errors)? observed.errors.length : null});
    }
  }
  result.overall = result.checks.length===4 && result.checks.every(x=>x.agreement) ? "PASS":"NOT_COMPLETED";
} catch(err) {
  result.error=String(err);
}
mkdirSync("gate-b-evidence",{recursive:true});
writeFileSync("gate-b-evidence/external-module-contract.json",JSON.stringify(result,null,2)+"\n");
console.log(JSON.stringify({overall:result.overall,checks:result.checks,error:result.error},null,2));
if(result.overall!=="PASS")process.exitCode=2;
