"""Independent adversarial tests for evidence-bound AAS oracle comparison."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from cross_validator_comparison import compare

class CrossValidatorEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.hashes = {}
        for kind in ("baseline", "mutant"):
            payload = ('{"id":"'+kind+'"}').encode()
            (self.root / ("primary-"+kind+".json")).write_bytes(payload)
            self.hashes[kind] = hashlib.sha256(payload).hexdigest()
        self.report = {"overall":"REPLAY_OUTCOME_MATCH",
                       "primary":{"source_sha256":self.hashes["baseline"],
                                  "mutant_sha256":self.hashes["mutant"],
                                  "legs":{"baseline":{"exit_code":0},"mutant":{"exit_code":0}}}}
        self.oracle = {"overall":"OBSERVED","tool":"aas_test_engines","version_pin":"1.0.3",
                       "checks":[{"input":"primary-"+kind+".json",
                                  "input_sha256":self.hashes[kind],
                                  "accepted":kind=="baseline"} for kind in ("baseline","mutant")]}
        self.save()
    def save(self):
        (self.root/"report.json").write_text(json.dumps(self.report))
        (self.root/"aas-oracle-observation.json").write_text(json.dumps(self.oracle))
    def test_real_bytes_agree_and_difference_is_not_bug(self):
        result=compare(self.root)
        self.assertEqual(result["overall"],"OBSERVED")
        self.assertEqual(result["cases"][1]["comparison"],"COVERAGE_DIFFERENCE")
    def test_tampered_file_fails_closed(self):
        (self.root/"primary-mutant.json").write_text('{"tampered":true}')
        self.assertEqual(compare(self.root)["overall"],"NOT_COMPLETED")
    def test_no_partial_results_on_second_input_failure(self):
        (self.root/"primary-mutant.json").write_text('{"changed":true}')
        result = compare(self.root)
        self.assertEqual(result["overall"], "NOT_COMPLETED")
        self.assertEqual(result["cases"], [])

    def test_symlink_fails_closed(self):
        p=self.root/"primary-baseline.json"
        p.unlink()
        p.symlink_to(self.root/"primary-mutant.json")
        self.assertEqual(compare(self.root)["overall"],"NOT_COMPLETED")
    def test_duplicate_oracle_row_fails_closed(self):
        self.oracle["checks"].append(dict(self.oracle["checks"][0]))
        self.save()
        self.assertEqual(compare(self.root)["overall"],"NOT_COMPLETED")
    def test_unpinned_oracle_fails_closed(self):
        self.oracle["version_pin"]="unverified"
        self.save()
        self.assertEqual(compare(self.root)["overall"],"NOT_COMPLETED")
    def test_duplicate_json_keys_fails_closed(self):
        (self.root/"aas-oracle-observation.json").write_text('{"overall":"OBSERVED","overall":"OBSERVED"}')
        self.assertEqual(compare(self.root)["overall"], "NOT_COMPLETED")

    def test_symlink_report_fails_closed(self):
        p = self.root/"report.json"
        p.unlink()
        p.symlink_to(self.root/"aas-oracle-observation.json")
        self.assertEqual(compare(self.root)["overall"], "NOT_COMPLETED")

    def test_oversized_oracle_evidence_fails_closed(self):
        (self.root/"aas-oracle-observation.json").write_bytes(b" " * (2*1024*1024+1))
        self.assertEqual(compare(self.root)["overall"], "NOT_COMPLETED")

    def test_wrong_tool_fails_closed(self):
        self.oracle["tool"]="fake_oracle"
        self.save()
        self.assertEqual(compare(self.root)["overall"],"NOT_COMPLETED")
    def test_oracle_boolean_must_be_real_boolean(self):
        self.oracle["checks"][0]["accepted"]="true"
        self.save()
        self.assertEqual(compare(self.root)["overall"],"NOT_COMPLETED")

if __name__=="__main__":
    unittest.main()
