"""Runnable integration: consume the existing OpenDPP + IDTA evidence chain.

This is a production-facing entrypoint over the existing Gate B modules, not
another mock validator. It executes the independently maintained AAS engine
through aas_oracle_adapter and publishes a comparison only after every leg
and evidence prerequisite succeeds.
"""
import argparse
import json
from pathlib import Path
from aas_oracle_adapter import evaluate
from cross_validator_comparison import compare

def run(bundle: Path):
    bundle = Path(bundle)
    outcome = {"schema": "dpp-evidence-integration-v1", "overall": "NOT_COMPLETED",
               "inputs": ["primary-baseline.json", "primary-mutant.json"],
               "oracle": "aas_test_engines", "comparison": None}
    try:
        if not bundle.is_dir() or bundle.is_symlink():
            raise ValueError("unsafe or missing evidence bundle")
        oracle = evaluate(bundle)
        (bundle / "aas-oracle-observation.json").write_text(json.dumps(oracle, indent=2) + "\n")
        if oracle["overall"] != "OBSERVED":
            raise RuntimeError("external AAS validator failed: " + oracle.get("error", "unknown"))
        comparison = compare(bundle)
        (bundle / "cross-validator-comparison.json").write_text(json.dumps(comparison, indent=2) + "\n")
        if comparison["overall"] != "OBSERVED":
            raise RuntimeError("evidence comparison failed: " + comparison.get("error", "unknown"))
        outcome["comparison"] = comparison
        outcome["overall"] = "OBSERVED"
    except (OSError, ValueError, RuntimeError, TypeError) as exc:
        outcome["error"] = str(exc)
    if bundle.is_dir() and not bundle.is_symlink():
        (bundle / "integration-result.json").write_text(json.dumps(outcome, indent=2) + "\n")
    return outcome

def main():
    p = argparse.ArgumentParser(description="Run the real AAS oracle and evidence comparison on an existing Gate B bundle")
    p.add_argument("--bundle", type=Path, default=Path("gate-b-evidence"))
    args = p.parse_args()
    result = run(args.bundle)
    print(json.dumps(result, indent=2))
    return 0 if result["overall"] == "OBSERVED" else 2

if __name__ == "__main__":
    raise SystemExit(main())
