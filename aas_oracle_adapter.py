"""Independent AAS metamodel oracle adapter.

Calls the official IDTA AAS Test Engines Python module, without duplicating
its model constraints. The result is a separate standards-check observation,
not a claim about OpenDPP's documented JSON Schema scope.
"""
import argparse
import hashlib
import json
from pathlib import Path

TOOL = "aas_test_engines"
VERSION = "1.0.3"
INPUTS = ("primary-baseline.json", "primary-mutant.json")


def evaluate(bundle: Path):
    result = {"schema": "aas-independent-oracle-v1", "tool": TOOL, "version_pin": VERSION,
              "overall": "NOT_COMPLETED", "checks": [], "scope": "IDTA AAS metamodel and constraints, subject to selected Test Engines version"}
    try:
        from aas_test_engines import file as aas_file
        for filename in INPUTS:
            path = bundle / filename
            if path.is_symlink() or not path.is_file():
                raise ValueError("input missing or symlink: " + filename)
            data = path.read_bytes()
            parsed = json.loads(data)
            actual = aas_file.check_json_data(parsed)
            accepted = bool(actual.ok())
            result["checks"].append({
                "input": filename, "input_sha256": hashlib.sha256(data).hexdigest(),
                "accepted": accepted, "oracle": TOOL, "version_pin": VERSION,
            })
        result["overall"] = "OBSERVED"
        result["comparison_note"] = "Compare accepted results with the OpenDPP CLI; divergent scopes do not imply upstream bugs."
    except Exception as exc:
        result["error"] = repr(exc)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", type=Path, default=Path("gate-b-evidence"))
    args = ap.parse_args()
    outcome = evaluate(args.bundle)
    args.bundle.mkdir(parents=True, exist_ok=True)
    (args.bundle / "aas-oracle-observation.json").write_text(json.dumps(outcome, indent=2) + "\n")
    print(json.dumps(outcome, indent=2))
    return 0 if outcome["overall"] == "OBSERVED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
