import base64
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from product_acceptance import assess, PIN


def h(v):
    return hashlib.sha256(v).hexdigest()


def make_bundle(path):
    sample = b'{"submodels":[]}'
    mutant = b'{"submodels":[{"idShort":"x"}]}'
    observations = {}
    for label in ("primary", "replay"):
        legs = {}
        for kind, blob in (("baseline", sample), ("mutant", mutant)):
            filename = label + "-" + kind + ".json"
            (path / filename).write_bytes(blob)
            stdout = (label + " accepted " + kind).encode()
            legs[kind] = {
                "executed": True, "exit_code": 0,
                "command": ["node", "validate/validate.mjs", "aas", str((path / filename).resolve())],
                "stdout_base64": base64.b64encode(stdout).decode(),
                "stdout_raw_sha256": h(stdout),
                "stderr_base64": "", "stderr_raw_sha256": h(b"")
            }
        observations[label] = {"commit": PIN, "source_sha256": h(sample),
                               "mutant_sha256": h(mutant), "validator_sha256": h(b"validator"),
                               "legs": legs}
    data = {"schema": "gate-b-real-observation-v1", "overall": "REPLAY_OUTCOME_MATCH",
            "primary": observations["primary"], "replay": observations["replay"],
            "observed_exit_codes": {"baseline": 0, "mutant": 0}}
    (path / "report.json").write_text(json.dumps(data))
    return data


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "gate-b-evidence"
        self.root.mkdir()
        self.report = make_bundle(self.root)

    def save(self):
        (self.root / "report.json").write_text(json.dumps(self.report))

    def test_valid_real_format_evidence(self):
        self.assertEqual(assess(self.root)["overall"], "PASS")

    def test_tampered_input_rejected(self):
        (self.root / "primary-baseline.json").write_text("{}")
        self.assertEqual(assess(self.root)["overall"], "NOT_COMPLETED")

    def test_fake_replay_outcome_rejected(self):
        self.report["replay"]["legs"]["mutant"]["exit_code"] = 1
        self.save()
        self.assertEqual(assess(self.root)["overall"], "NOT_COMPLETED")

    def test_corrupt_stdout_rejected(self):
        self.report["primary"]["legs"]["baseline"]["stdout_base64"] = "YWJj"
        self.save()
        self.assertEqual(assess(self.root)["overall"], "NOT_COMPLETED")

    def test_unexecuted_rejected(self):
        self.report["primary"]["legs"]["baseline"]["executed"] = False
        self.save()
        self.assertEqual(assess(self.root)["overall"], "NOT_COMPLETED")

    def test_duplicate_json_keys_rejected(self):
        (self.root / "report.json").write_text('{"overall":"REPLAY_OUTCOME_MATCH","overall":"REPLAY_OUTCOME_MATCH"}')
        self.assertEqual(assess(self.root)["overall"], "NOT_COMPLETED")

    def test_symlink_rejected(self):
        p = self.root / "primary-mutant.json"
        p.unlink()
        p.symlink_to(self.root / "replay-mutant.json")
        self.assertEqual(assess(self.root)["overall"], "NOT_COMPLETED")


if __name__ == "__main__":
    unittest.main()
