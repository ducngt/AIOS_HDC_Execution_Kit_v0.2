import json
import tempfile
import unittest
from pathlib import Path

from hdc.validator import (
    ContractValidationError,
    ValidationResult,
    load_schema,
    require_valid_file,
    validate_document,
    validate_file,
)


class ValidatorTests(unittest.TestCase):

    def test_loads_all_contract_schemas(self):
        for contract_type in (
            "task",
            "change",
            "evidence",
            "acceptance",
        ):
            schema = load_schema(contract_type)
            self.assertEqual(schema["type"], "object")

    def test_current_t00_contract_is_valid(self):
        result = validate_file(
            "tasks/T00/task.json",
            "task",
        )

        self.assertTrue(result.valid)
        self.assertEqual(result.issues, ())

    def test_invalid_task_returns_structured_issue(self):
        result = validate_document(
            {
                "task_id": "INVALID",
                "title": "Bad task",
                "version": "0.2.0",
                "status": "approved",
                "objective": "Negative test.",
                "human_gate_required": True,
                "implementation_allowed_before_gate": False,
            },
            "task",
        )

        self.assertFalse(result.valid)
        self.assertGreaterEqual(len(result.issues), 1)
        self.assertEqual(result.issues[0].path, "task_id")

    def test_unknown_contract_type_fails(self):
        with self.assertRaises(ContractValidationError):
            validate_document({}, "unknown")

    def test_missing_file_fails_actionably(self):
        with self.assertRaisesRegex(
            ContractValidationError,
            "JSON file not found",
        ):
            validate_file(
                "tests/fixtures/does-not-exist.json",
                "task",
            )

    def test_malformed_json_fails_actionably(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "broken.json"
            path.write_text("{broken", encoding="utf-8")

            with self.assertRaisesRegex(
                ContractValidationError,
                "Invalid JSON",
            ):
                validate_file(path, "task")

    def test_require_valid_file_passes_valid_contract(self):
        require_valid_file(
            "tasks/T00/task.json",
            "task",
        )

    def test_require_valid_file_raises_for_invalid_contract(self):
        document = {
            "task_id": "BAD",
            "title": "Bad task",
            "version": "0.2.0",
            "status": "approved",
            "objective": "Negative test.",
            "human_gate_required": True,
            "implementation_allowed_before_gate": False,
        }

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "task.json"
            path.write_text(
                json.dumps(document),
                encoding="utf-8",
            )

            with self.assertRaises(ContractValidationError):
                require_valid_file(path, "task")

    def test_validation_result_require_valid(self):
        result = ValidationResult(
            valid=False,
            issues=(),
        )

        with self.assertRaises(ContractValidationError):
            result.require_valid()


if __name__ == "__main__":
    unittest.main()
