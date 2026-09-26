import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"


def load_schema(name):
    return json.loads((CONTRACTS / name).read_text())


class ContractSchemaTests(unittest.TestCase):
    def test_all_schemas_are_valid(self):
        for name in [
            "task-contract.schema.json",
            "change-package.schema.json",
            "engineering-evidence.schema.json",
            "acceptance-package.schema.json",
        ]:
            schema = load_schema(name)
            Draft202012Validator.check_schema(schema)

    def test_valid_task_contract(self):
        schema = load_schema("task-contract.schema.json")
        doc = {
            "task_id": "T00",
            "title": "HDC Guard",
            "version": "0.2.0",
            "status": "implementing",
            "objective": "Establish HDC governance baseline.",
            "human_gate_required": True,
            "implementation_allowed_before_gate": False,
            "required_outputs": ["validator", "guard"],
            "human_gate": {
                "decision": "approved",
                "record": "governance/decisions/T00_HUMAN_GATE.md"
            }
        }
        Draft202012Validator(schema).validate(doc)

    def test_invalid_task_id_fails(self):
        schema = load_schema("task-contract.schema.json")
        doc = {
            "task_id": "BAD",
            "title": "Invalid",
            "version": "0.2.0",
            "status": "implementing",
            "objective": "Invalid task.",
            "human_gate_required": True,
            "implementation_allowed_before_gate": False
        }
        with self.assertRaises(ValidationError):
            Draft202012Validator(schema).validate(doc)

    def test_valid_change_package(self):
        schema = load_schema("change-package.schema.json")
        doc = {
            "change_id": "CP-T00-001",
            "task_id": "T00",
            "base_ref": "origin/main",
            "branch": "change/t00-hdc-guard",
            "changed_files": ["hdc/guard.py"],
            "rationale": "Implement HDC Guard."
        }
        Draft202012Validator(schema).validate(doc)

    def test_change_package_requires_files(self):
        schema = load_schema("change-package.schema.json")
        doc = {
            "change_id": "CP-T00-001",
            "task_id": "T00",
            "base_ref": "origin/main",
            "branch": "change/t00-hdc-guard",
            "changed_files": [],
            "rationale": "Invalid empty change."
        }
        with self.assertRaises(ValidationError):
            Draft202012Validator(schema).validate(doc)

    def test_valid_engineering_evidence(self):
        schema = load_schema("engineering-evidence.schema.json")
        doc = {
            "evidence_id": "EE-T00-001",
            "task_id": "T00",
            "change_id": "CP-T00-001",
            "test_results": {"status": "pass"},
            "verification_results": {"status": "pass"},
            "replay_results": {"status": "pass"}
        }
        Draft202012Validator(schema).validate(doc)

    def test_valid_acceptance_package(self):
        schema = load_schema("acceptance-package.schema.json")
        doc = {
            "acceptance_id": "AP-T00-001",
            "task_id": "T00",
            "change_id": "CP-T00-001",
            "evidence_id": "EE-T00-001",
            "decision_record": "governance/decisions/T00_ACCEPTANCE.md",
            "decision": "accepted"
        }
        Draft202012Validator(schema).validate(doc)

    def test_invalid_acceptance_decision_fails(self):
        schema = load_schema("acceptance-package.schema.json")
        doc = {
            "acceptance_id": "AP-T00-001",
            "task_id": "T00",
            "change_id": "CP-T00-001",
            "evidence_id": "EE-T00-001",
            "decision_record": "governance/decisions/T00_ACCEPTANCE.md",
            "decision": "auto_accepted"
        }
        with self.assertRaises(ValidationError):
            Draft202012Validator(schema).validate(doc)


if __name__ == "__main__":
    unittest.main()
