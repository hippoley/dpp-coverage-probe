"""Create a bounded, evidence-grounded cross-validator comparison.

A difference is COVERAGE_DIFFERENCE, never automatically an upstream bug.
"""
import argparse
import json
from pathlib import Path


def compare(root):
    result = {"schema": "aas-cross-validator-comparison-v1", "overall": "NOT_COMPLETED",
              "cases": [], "interpretation": "Different declared scopes; disagreement is not proof of a defect."}
    try:
        open_report = json.loads((root / "report.json").read_text())
        oracle = json.loads((root / "aas-oracle-observation.json").read_text())
        if open_report.get("overall") != "REPLAY_OUTCOME_MATCH" or oracle.get("overall") != "OBSERVED":
            raise ValueError("evidence prerequisite missing")
        import hashlib
        for kind in ("baseline", "mutant"):
            expected_name = "primary-" + kind + ".json"
            reference = open_report["primary"]["source_sha256" if kind == "baseline" else "mutant_sha256"]
            match = [row for row in oracle["checks"] if row.get("input") == expected_name]
            if len(match) != 1 or match[0].get("input_sha256") != reference:
                raise ValueError("oracle input does not match upstream " + kind)
            exit_code = open_report["primary"]["legs"][kind]["exit_code"]
            if exit_code not in (0, 1) or type(match[0].get("accepted")) is not bool:
                raise ValueError("invalid validator outcome " + kind)
            structural = (exit_code == 0)
            aas = match[0]["accepted"]
            result["cases"].append({"case": kind, "sha256": reference,
                                    "opendpp_structural_accepts": structural,
                                    "aas_test_engines_accepts": aas,
                                    "comparison": "AGREEMENT" if structural == aas else "COVERAGE_DIFFERENCE"})
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
