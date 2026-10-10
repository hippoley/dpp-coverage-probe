"""Batch validation over user-provided AAS JSON files, using the real validators."""
import argparse
import json
from pathlib import Path
from validate_dpp import run

def main():
    p = argparse.ArgumentParser(description="Batch-run external validators over a folder of AAS JSON files")
    p.add_argument("folder", type=Path)
    p.add_argument("--output", type=Path, default=Path("dpp-batch-output"))
    p.add_argument("--opendpp", type=Path, default=Path("/tmp/opendpp"))
    args = p.parse_args()
    if args.folder.is_symlink() or not args.folder.is_dir():
        p.error("folder must be an existing non-symlink directory")
    args.output.mkdir(parents=True, exist_ok=True)
    files = sorted(x for x in args.folder.glob("*.json") if x.is_file() and not x.is_symlink())
    summary = {"schema": "dpp-batch-validation-v1", "total": len(files), "observed": 0,
               "failed": 0, "items": []}
    for index, path in enumerate(files):
        outcome = run(path, args.output / ("case-%05d" % index), args.opendpp)
        ok = outcome["overall"] == "OBSERVED"
        summary["observed" if ok else "failed"] += 1
        summary["items"].append({"file": path.name, "overall": outcome["overall"],
                                 "comparison": outcome.get("comparison"),
                                 "result_path": "case-%05d/validation-result.json" % index})
    (args.output / "batch-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0 if summary["total"] > 0 and summary["failed"] == 0 else 2

if __name__ == "__main__":
    raise SystemExit(main())
