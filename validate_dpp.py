"""Run the pinned OpenDPP CLI and official IDTA AAS Test Engines on a user's JSON file.

Usage: python3 validate_dpp.py path/to/aas.json --output evidence-output
Requires a pinned OpenDPP checkout (default /tmp/opendpp) and aas_test_engines==1.0.3.
Unlike Gate B, this does not need a pre-generated synthetic baseline/mutant bundle.
"""
import argparse
import base64
import hashlib
import json
import os
import subprocess
from importlib.metadata import version as installed_version
from pathlib import Path

PIN = "20211ecc2b63eb7664c571a8d629aeeed364491e"
ORACLE_VERSION = "1.0.3"
MAX_BYTES = 8 * 1024 * 1024

def sha(data):
    return hashlib.sha256(data).hexdigest()

def run(source: Path, output: Path, upstream: Path):
    result = {"schema": "dpp-file-validation-v1", "overall": "NOT_COMPLETED",
              "validators": {}, "interpretation": "Validator scope disagreement is not proof of an upstream defect."}
    try:
        source, output, upstream = Path(source), Path(output), Path(upstream)
        if source.is_symlink() or not source.is_file() or source.stat().st_size > MAX_BYTES:
            raise ValueError("missing, unsafe or oversized input")
        payload = source.read_bytes()
        if len(payload) > MAX_BYTES:
            raise ValueError("input too large")
        document = json.loads(payload)
        if installed_version("aas_test_engines") != ORACLE_VERSION:
            raise ValueError("AAS engine installed version differs from pin")
        from aas_test_engines import file as aas_file
        head = subprocess.run(["git", "-C", str(upstream), "rev-parse", "HEAD"],
                              capture_output=True, text=True, timeout=10, check=True).stdout.strip()
        if head != PIN:
            raise ValueError("OpenDPP checkout commit does not match pin")
        cli = upstream / "validate" / "validate.mjs"
        if not cli.is_file() or cli.is_symlink():
            raise ValueError("OpenDPP validator entrypoint missing")
        # Invoke the actual external OpenDPP validator, not a simulated parser.
        proc = subprocess.run(["node", "validate/validate.mjs", "aas", str(source.resolve())],
                              cwd=upstream, capture_output=True, timeout=120)
        if proc.returncode not in (0, 1):
            raise RuntimeError("OpenDPP execution failed with unsupported exit code: " + str(proc.returncode))
        result["validators"]["opendpp"] = {
            "commit": PIN, "entrypoint_sha256": sha(cli.read_bytes()),
            "exit_code": proc.returncode, "accepted": proc.returncode == 0,
            "stdout_sha256": sha(proc.stdout), "stderr_sha256": sha(proc.stderr),
            "stdout_base64": base64.b64encode(proc.stdout).decode(),
            "stderr_base64": base64.b64encode(proc.stderr).decode()}
        verdict = aas_file.check_json_data(document).ok()
        if type(verdict) is not bool:
            raise TypeError("AAS oracle returned non-boolean verdict")
        result["validators"]["aas_test_engines"] = {
            "distribution_version": ORACLE_VERSION, "accepted": verdict}
        result["input"] = {"name": source.name, "sha256": sha(payload), "bytes": len(payload)}
        result["comparison"] = ("AGREEMENT" if verdict == (proc.returncode == 0) else "COVERAGE_DIFFERENCE")
        result["overall"] = "OBSERVED"
    except Exception as exc:
        result["error"] = repr(exc)
    if output.is_symlink():
        raise ValueError("output directory must not be a symlink")
    output.mkdir(parents=True, exist_ok=True)
    target = output / "validation-result.json"
    if target.is_symlink():
        raise ValueError("output file must not be a symlink")
    target.write_text(json.dumps(result, indent=2) + "\n")
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument("input", type=Path)
    p.add_argument("--output", type=Path, default=Path("dpp-validation-output"))
    p.add_argument("--opendpp", type=Path, default=Path(os.environ.get("OPENDPP_CHECKOUT", "/tmp/opendpp")))
    args = p.parse_args()
    result = run(args.input, args.output, args.opendpp)
    print(json.dumps({"overall": result["overall"], "comparison": result.get("comparison"),
                      "output": str(args.output / "validation-result.json"),
                      "error": result.get("error")}, indent=2))
    return 0 if result["overall"] == "OBSERVED" else 2

if __name__ == "__main__":
    raise SystemExit(main())
