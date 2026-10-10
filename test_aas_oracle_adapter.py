"""Failure-injection tests for the real external-module adapter boundary."""
import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from aas_oracle_adapter import evaluate, VERSION

class OracleBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for kind in ("baseline", "mutant"):
            (self.root / ("primary-" + kind + ".json")).write_text('{"modelType":"Submodel"}')
    def test_mismatched_installed_distribution_fails_closed(self):
        with patch("aas_oracle_adapter.installed_version", return_value="0.0.0"):
            result = evaluate(self.root)
        self.assertEqual(result["overall"], "NOT_COMPLETED")
        self.assertIn("version mismatch", result["error"])
    def test_missing_external_module_fails_closed(self):
        with patch("aas_oracle_adapter.installed_version", side_effect=RuntimeError("not installed")):
            result = evaluate(self.root)
        self.assertEqual(result["overall"], "NOT_COMPLETED")
    def test_strict_boolean_oracle_contract(self):
        fake_file = types.ModuleType("aas_test_engines.file")
        fake_file.check_json_data = lambda parsed: types.SimpleNamespace(ok=lambda: "true")
        fake_package = types.ModuleType("aas_test_engines")
        fake_package.file = fake_file
        with patch("aas_oracle_adapter.installed_version", return_value=VERSION):
            with patch.dict("sys.modules", {"aas_test_engines": fake_package, "aas_test_engines.file": fake_file}):
                result = evaluate(self.root)
        self.assertEqual(result["overall"], "NOT_COMPLETED")
        self.assertIn("did not return bool", result["error"])
    def test_external_api_is_actually_called(self):
        seen = []
        fake_file = types.ModuleType("aas_test_engines.file")
        def check(payload):
            seen.append(payload)
            return types.SimpleNamespace(ok=lambda: True)
        fake_file.check_json_data = check
        fake_package = types.ModuleType("aas_test_engines")
        fake_package.file = fake_file
        with patch("aas_oracle_adapter.installed_version", return_value=VERSION):
            with patch.dict("sys.modules", {"aas_test_engines": fake_package, "aas_test_engines.file": fake_file}):
                result = evaluate(self.root)
        self.assertEqual(result["overall"], "OBSERVED")
        self.assertEqual(len(seen), 2)
        self.assertEqual(len(result["checks"]), 2)

if __name__ == "__main__":
    unittest.main()
