"""Execute a versioned, actual cross-validator AAS mutation matrix.

External engines are called for EVERY case. Labels other than anchored
baseline/duplicate-idShort are observations, not invented ground truth.
"""
import copy
import hashlib
import json
import subprocess
from pathlib import Path

from aas_test_engines import file as aas_file

UPSTREAM = Path("/tmp/opendpp")
ROOT = Path("gate-b-evidence")
INPUT = UPSTREAM / "samples/battery-aas-environment.json"


def mutate(payload, name):
    x = copy.deepcopy(payload)
    elems = x["submodels"][0]["submodelElements"]
    if name == "baseline":
        return x
    if name == "duplicate_sibling_idshort":
        elems[1]["idShort"] = elems[0]["idShort"]
    elif name == "invalid_modeltype":
        elems[0]["modelType"] = "CompletelyUnknownAASModelType"
    elif name == "invalid_valuetype":
        elems[0]["valueType"] = "xs:invented"
    elif name == "missing_idshort":
        del elems[0]["idShort"]
    elif name == "reordered_siblings":
        elems[0], elems[1] = elems[1], elems[0]
    elif name == "empty_submodel_elements":
        x["submodels"][0]["submodelElements"] = []
    else:
        raise ValueError(name)
    return x


def run_matrix():
    cases = ["baseline", "duplicate_sibling_idshort", "invalid_modeltype",
             "invalid_valuetype", "missing_idshort", "reordered_siblings",
             "empty_submodel_elements"]
    result = {"schema": "aas-benchmark-matrix-v1",
              "dataset_provenance": "OpenDPP sample at pinned upstream SHA; deterministic mutations",
              "oracle": "aas_test_engines==1.0.3",
              "opendpp_commit": "20211ecc2b63eb7664c571a8d629aeeed364491e",
              "overall": "NOT_COMPLETED", "cases": []}
    original = json.loads(INPUT.read_bytes())
    ROOT.mkdir(exist_ok=True)
    for name in cases:
        value = mutate(original, name)
        data = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
        f = ROOT / ("matrix-" + name + ".json")
        f.write_bytes(data)
        execution = subprocess.run(
            ["node", "validate/validate.mjs", "aas", str(f.resolve())],
            cwd=UPSTREAM, capture_output=True, timeout=90)
        official = aas_file.check_json_data(value)
        accepted = bool(official.ok())
        result["cases"].append({
            "id": name, "sha256": hashlib.sha256(data).hexdigest(),
            "opendpp_exit": execution.returncode,
            "opendpp_accepts": execution.returncode == 0,
            "aas_test_engines_accepts": accepted,
            "difference": (execution.returncode == 0) != accepted,
            "stdout_sha256": hashlib.sha256(execution.stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(execution.stderr).hexdigest(),
        })
    lookup = {x["id"]: x for x in result["cases"]}
    anchors_ok = (lookup["baseline"]["opendpp_accepts"]
                  and lookup["baseline"]["aas_test_engines_accepts"]
                  and not lookup["duplicate_sibling_idshort"]["aas_test_engines_accepts"])
    result["summary"] = {
        "executed": len(result["cases"]),
        "agreed": sum(not x["difference"] for x in result["cases"]),
        "coverage_differences": sum(x["difference"] for x in result["cases"]),
        "anchor_expectations_met": anchors_ok,
    }
    result["overall"] = "OBSERVED" if anchors_ok and all(x["opendpp_exit"] in (0, 1) for x in result["cases"]) else "NOT_COMPLETED"
    (ROOT / "aas-benchmark-matrix.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"overall": result["overall"], "summary": result["summary"], "cases": result["cases"]}, indent=2))
    return 0 if result["overall"] == "OBSERVED" else 2


if __name__ == "__main__":
    raise SystemExit(run_matrix())
