import copy
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "validate_master.py"
SPEC = importlib.util.spec_from_file_location("validate_master", MODULE_PATH)
validate_master = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(validate_master)


class ValidateMasterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.example = validate_master.load_json(ROOT / "assets" / "cv_master.example.json")

    def test_example_passes_strict_provenance(self):
        validator = validate_master.Validator(strict_provenance=True)
        validator.validate(copy.deepcopy(self.example))
        self.assertEqual(validator.errors, [])
        self.assertEqual(validator.warnings, [])

    def test_unknown_skill_evidence_is_rejected(self):
        data = copy.deepcopy(self.example)
        data["skills"]["Languages"][0]["evidence"] = ["ach-does-not-exist"]
        validator = validate_master.Validator(strict_provenance=True)
        validator.validate(data)
        self.assertTrue(any("unknown achievement ID" in error for error in validator.errors))

    def test_legacy_skill_is_rejected_in_strict_mode(self):
        data = copy.deepcopy(self.example)
        data["skills"]["Languages"].append("Legacy Skill")
        validator = validate_master.Validator(strict_provenance=True)
        validator.validate(data)
        self.assertTrue(any("legacy skill string" in error for error in validator.errors))

    def test_example_fit_matrix_and_claim_ledger_pass(self):
        validator = validate_master.Validator(strict_provenance=True)
        validator.validate(copy.deepcopy(self.example))
        validator.validate_fit_matrix(
            validate_master.load_json(ROOT / "assets" / "fit_matrix.example.json")
        )
        validator.validate_claim_ledger(
            validate_master.load_json(ROOT / "assets" / "claim_ledger.example.json")
        )
        self.assertEqual(validator.errors, [])

    def test_gap_with_master_evidence_is_rejected(self):
        matrix = validate_master.load_json(ROOT / "assets" / "fit_matrix.example.json")
        matrix["requirements"][1]["master_refs"] = ["ach-api-latency"]
        validator = validate_master.Validator(strict_provenance=True)
        validator.validate(copy.deepcopy(self.example))
        validator.validate_fit_matrix(matrix)
        self.assertTrue(any("gap requirements cannot cite" in error for error in validator.errors))


if __name__ == "__main__":
    unittest.main()
