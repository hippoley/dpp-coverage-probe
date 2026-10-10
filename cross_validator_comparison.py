"""Create a bounded, evidence-grounded cross-validator comparison.

A difference is COVERAGE_DIFFERENCE, never automatically an upstream bug.
"""
import argparse
import json
import hashlib
import re
from pathlib import Path


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def compare(root):
    result = {"schema": "aas-cross-validator-comparison-v1", "overall": "NOT_COMPLETED",
              "cases": [], "interpretation": "Different declared scopes; disagreement is not proof of a defect."}
    try:
        reports = []
        for filename in ("report.json", "aas-oracle-observation.json"):
            path = root / filename
            if path.is_symlink() or not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
                raise ValueError("unsafe, missing or oversized evidence: " + filename)
            reports.append(json.loads(path.read_bytes(), object_pairs_hook=unique_object))
        open_report, oracle = reports
        if open_report.get("overall") != "REPLAY_OUTCOME_MATCH" or oracle.get("overall") != "OBSERVED":
            raise ValueError("evidence prerequisite missing")
        checks = oracle.get("checks")
        if not isinstance(checks, list) or len(checks) != 2:
            raise ValueError("oracle must report exactly two checks")
        if oracle.get("tool") != "aas_test_engines" or oracle.get("version_pin") != "1.0.3":
            raise ValueError("unexpected oracle implementation or version")
        verified_cases = []
        for kind in ("baseline", "mutant"):
            expected_name = "primary-" + kind + ".json"
            reference = open_report["primary"]["source_sha256" if kind == "baseline" else "mutant_sha256"]
            match = [row for row in oracle["checks"] if row.get("input") == expected_name]
            if len(match) != 1 or match[0].get("input_sha256") != reference:
                raise ValueError("oracle input does not match upstream " + kind)
            path = root / expected_name
            if path.is_symlink() or not path.is_file():
                raise ValueError("primary input missing or symlink: " + kind)
            actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            if not re.fullmatch(r"[0-9a-f]{64}", reference) or actual_hash != reference:
                raise ValueError("on-disk primary input hash mismatch: " + kind)
            exit_code = open_report["primary"]["legs"][kind]["exit_code"]
            if type(exit_code) is not int or exit_code not in (0, 1) or type(match[0].get("accepted")) is not bool:
                raise ValueError("invalid validator outcome " + kind)
            structural = (exit_code == 0)
            aas = match[0]["accepted"]
            verified_cases.append({"case": kind, "sha256": reference,
                                    "opendpp_structural_accepts": structural,
                                    "aas_test_engines_accepts": aas,
                                    "comparison": "AGREEMENT" if structural == aas else "COVERAGE_DIFFERENCE"})
        result["cases"] = verified_cases
        result["overall"] = "OBSERVED"
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        result["error"] = str(exc)
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--bundle", type=Path, default=Path("gate-b-evidence"))
    args = p.parse_args()
    result = compare(args.bundle)
    args.bundle.mkdir(exist_ok=True, parents=True)
    (args.bundle / "cross-validator-comparison.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["overall"] == "OBSERVED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
