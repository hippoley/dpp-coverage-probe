"""Real upstream observation, not a claim of full AAS semantic conformance."""
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

PIN = "20211ecc2b63eb7664c571a8d629aeeed364491e"
SAMPLE = "samples/battery-aas-environment.json"
OUT = Path("gate-b-evidence")
OUT.mkdir(exist_ok=True)

def sha(b):
    return hashlib.sha256(b).hexdigest()

def process(repo, name, kind, path):
    cmd = ["node", "validate/validate.mjs", kind, str(path.resolve())]
    try:
        p = subprocess.run(cmd, cwd=repo, capture_output=True, timeout=120)
        return dict(command=cmd, executed=True, exit_code=p.returncode,
                    stdout_raw_sha256=sha(p.stdout), stderr_raw_sha256=sha(p.stderr),
                    stdout_base64=base64.b64encode(p.stdout).decode(),
                    stderr_base64=base64.b64encode(p.stderr).decode())
    except (OSError, subprocess.TimeoutExpired) as exc:
        return dict(command=cmd, executed=False, error=str(exc))

def observe(repo, label):
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    if head != PIN:
        raise ValueError("pinned SHA mismatch")
    dirty = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=repo, text=True).strip()
    if dirty:
        raise ValueError("upstream tracked files changed")
    validator = (repo / "validate/validate.mjs").read_bytes()
    original = (repo / SAMPLE).read_bytes()
    payload = json.loads(original)
    altered = copy.deepcopy(payload)
    changed = False
    for sub in altered.get("submodels", []):
        elems = sub.get("submodelElements", [])
        if len(elems) >= 2 and isinstance(elems[0], dict) and isinstance(elems[1], dict):
            a, b = elems[0].get("idShort"), elems[1].get("idShort")
            if isinstance(a, str) and a and a != b:
                elems[1]["idShort"] = a
                changed = True
                break
    if not changed:
        raise ValueError("no suitable sibling idShort mutation")
    mutant = (json.dumps(altered, indent=2, sort_keys=True) + "\n").encode()
    (OUT / (label + "-baseline.json")).write_bytes(original)
    (OUT / (label + "-mutant.json")).write_bytes(mutant)
    legs = {key: process(repo, label, "aas", OUT / (label + "-" + key + ".json"))
            for key in ("baseline", "mutant")}
    return dict(commit=head, source_sha256=sha(original),
                validator_sha256=sha(validator), mutant_sha256=sha(mutant), legs=legs)

def main():
    report = {"schema": "gate-b-real-observation-v1", "claim_scope": "OpenDPP AAS structural JSON Schema observations only; no AASd-022 conformance claim",
              "overall": "NOT_COMPLETED"}
    try:
        primary = observe(Path("/tmp/opendpp"), "primary")
        replay = observe(Path("/tmp/opendpp-replay"), "replay")
        report["primary"] = primary
        report["replay"] = replay
        shared = ["commit", "source_sha256", "validator_sha256", "mutant_sha256"]
        identical_inputs = all(primary[x] == replay[x] for x in shared)
        # Independent validator outcomes are compared, not byte-identical logs:
        # different input paths legitimately appear in stdout/stderr.
        outcomes_match = all(
            primary["legs"][k].get("executed") and replay["legs"][k].get("executed") and
            primary["legs"][k].get("exit_code") in (0, 1) and
            primary["legs"][k].get("exit_code") == replay["legs"][k].get("exit_code")
            for k in ("baseline", "mutant"))
        report["output_bytes_identical"] = all(
            primary["legs"][k].get(f + "_raw_sha256") == replay["legs"][k].get(f + "_raw_sha256")
            for k in ("baseline", "mutant") for f in ("stdout", "stderr"))
        report["replay_claim_scope"] = "Independent checkout agrees on validator acceptance/rejection; raw logs are preserved, but need not be byte-identical."
        report["overall"] = "REPLAY_OUTCOME_MATCH" if identical_inputs and outcomes_match else "NOT_COMPLETED"
        report["observed_exit_codes"] = {k: primary["legs"][k].get("exit_code") for k in ("baseline", "mutant")}
    except Exception as exc:
        report["blocker"] = repr(exc)
    finally:
        (OUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({"overall": report["overall"], "blocker": report.get("blocker"),
                          "observed_exit_codes": report.get("observed_exit_codes")}, indent=2))
    return 0 if report["overall"] == "REPLAY_OUTCOME_MATCH" else 2

if __name__ == "__main__":
    sys.exit(main())
