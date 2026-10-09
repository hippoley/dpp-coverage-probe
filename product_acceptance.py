"""Independent, fail-closed evaluator of a real Gate B observation bundle.

This module does not invoke the validator and cannot establish AAS semantic
conformance. It checks that the upstream observation and replay evidence agree.
"""
import argparse
import base64
import binascii
import hashlib
import json
from pathlib import Path

PIN = "20211ecc2b63eb7664c571a8d629aeeed364491e"
MAX_REPORT_BYTES = 2 * 1024 * 1024


def digest(value):
    return hashlib.sha256(value).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def assess(root):
    findings = []
    report_path = root / "report.json"
    if report_path.is_symlink() or not report_path.is_file() or report_path.stat().st_size > MAX_REPORT_BYTES:
        return {"overall": "NOT_COMPLETED", "findings": ["report missing, unsafe, or oversized"]}
    try:
        report = json.loads(report_path.read_bytes(), object_pairs_hook=unique_object)
        if report.get("overall") != "REPLAY_OUTCOME_MATCH":
            findings.append("bootstrap did not report matching real outcomes")
        if report.get("schema") != "gate-b-real-observation-v1":
            findings.append("unsupported evidence schema")
        reference = None
        for label in ("primary", "replay"):
            obs = report[label]
            if obs["commit"] != PIN:
                findings.append(label + ": upstream commit differs")
            for kind in ("baseline", "mutant"):
                filename = label + "-" + kind + ".json"
                path = root / filename
                if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_REPORT_BYTES:
                    findings.append(label + ": input missing or unsafe " + kind)
                    continue
                blob = path.read_bytes()
                expected = obs["source_sha256" if kind == "baseline" else "mutant_sha256"]
                if digest(blob) != expected:
                    findings.append(label + ": input digest mismatch " + kind)
                leg = obs["legs"][kind]
                if leg.get("executed") is not True or leg.get("exit_code") not in (0, 1):
                    findings.append(label + ": missing or unsupported process outcome " + kind)
                command = leg.get("command")
                if not isinstance(command, list) or command[:3] != ["node", "validate/validate.mjs", "aas"] or len(command) != 4 or not command[3].endswith("/gate-b-evidence/" + filename):
                    findings.append(label + ": command is not bound to its evidence file " + kind)
                for stream in ("stdout", "stderr"):
                    raw = base64.b64decode(leg[stream + "_base64"], validate=True)
                    if digest(raw) != leg[stream + "_raw_sha256"]:
                        findings.append(label + ": corrupted " + stream + " " + kind)
            if reference is None:
                reference = obs
            else:
                for field in ("commit", "source_sha256", "mutant_sha256", "validator_sha256"):
                    if obs[field] != reference[field]:
                        findings.append("replay differs on " + field)
                for kind in ("baseline", "mutant"):
                    if obs["legs"][kind]["exit_code"] != reference["legs"][kind]["exit_code"]:
                        findings.append("replay process outcome differs on " + kind)
        if report.get("observed_exit_codes") != {kind: report["primary"]["legs"][kind]["exit_code"] for kind in ("baseline", "mutant")}:
            findings.append("recorded exit code summary inconsistent")
    except (KeyError, TypeError, ValueError, OSError, UnicodeError, binascii.Error) as exc:
        findings.append("invalid evidence structure: " + str(exc))
    return {
        "schema": "gate-b-independent-acceptance-v1",
        "overall": "PASS" if not findings else "NOT_COMPLETED",
        "findings": findings,
        "scope": "Evidence integrity and independent checkout outcome agreement, not AAS semantic conformance",
        "upstream_commit": PIN,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, default=Path("gate-b-evidence"))
    args = parser.parse_args()
    result = assess(args.bundle)
    args.bundle.mkdir(parents=True, exist_ok=True)
    (args.bundle / "independent-acceptance.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["overall"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
