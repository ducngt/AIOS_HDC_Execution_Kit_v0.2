import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from hdc.validator import load_schema, validate_document, validate_file


ROOT = Path(__file__).resolve().parents[1]


class CanonicalMetaModelTests(unittest.TestCase):

    def test_all_canonical_schemas_are_valid(self):
        for contract_type in (
            "canonical-identity",
            "canonical-reference",
            "canonical-lifecycle",
            "canonical-object",
            "canonical-meta-model",
        ):
            schema = load_schema(contract_type)
            Draft202012Validator.check_schema(schema)

    def test_valid_canonical_identity(self):
        result = validate_document(
            {
                "object_id": "IDENTITY-001",
                "object_type": "identity",
                "version": "1.0.0",
                "namespace": "aios.core",
                "status": "active",
            },
            "canonical-identity",
        )
        self.assertTrue(result.valid)

    def test_invalid_identity_version_fails(self):
        result = validate_document(
            {
                "object_id": "IDENTITY-001",
                "object_type": "identity",
                "version": "latest",
                "namespace": "aios.core",
            },
            "canonical-identity",
        )
        self.assertFalse(result.valid)

    def test_reference_requires_explicit_target_type(self):
        result = validate_document(
            {
                "target_id": "ROLE-LECTURER",
                "relation": "assigned_role",
            },
            "canonical-reference",
        )
        self.assertFalse(result.valid)

    def test_lifecycle_keeps_current_state_and_history_separate(self):
        result = validate_document(
            {
                "current_state": "active",
                "lifecycle_state": "activated",
                "history_ref": "HISTORY-001",
                "provenance_ref": "PROVENANCE-001",
            },
            "canonical-lifecycle",
        )
        self.assertTrue(result.valid)

    def test_valid_canonical_object(self):
        result = validate_document(
            {
                "identity": {
                    "object_id": "AUTH-GRANT-001",
                    "object_type": "authority_grant",
                    "version": "1.0.0",
                    "namespace": "aios.core",
                    "status": "active",
                },
                "references": [
                    {
                        "target_id": "ROLE-LECTURER",
                        "target_type": "role",
                        "relation": "granted_to",
                        "scope": "research",
                        "version_constraint": ">=1.0.0",
                    }
                ],
                "lifecycle": {
                    "current_state": "active",
                    "lifecycle_state": "activated",
                    "history_ref": "HISTORY-001",
                    "provenance_ref": "PROVENANCE-001",
                },
                "provenance": {
                    "source": "authority-registry"
                },
                "payload": {
                    "authority": "review_research"
                },
            },
            "canonical-object",
        )
        self.assertTrue(result.valid)

    def test_meta_model_manifest_is_valid(self):
        result = validate_file(
            ROOT / "manifests/canonical/meta-model.json",
            "canonical-meta-model",
        )
        self.assertTrue(result.valid)

    def test_required_concept_families_exist(self):
        data = json.loads(
            (ROOT / "manifests/canonical/meta-model.json").read_text()
        )
        names = {item["name"] for item in data["concept_families"]}

        required = {
            "Identity",
            "Organization",
            "Role",
            "Context",
            "Authority",
            "Delegation",
            "Policy",
            "Semantic",
            "Capability",
            "Contract",
            "Domain",
            "Work",
            "Decision",
            "Evidence",
            "Event",
            "Agent",
            "Change",
        }

        self.assertEqual(names, required)

    def test_required_invariants_exist(self):
        data = json.loads(
            (ROOT / "manifests/canonical/meta-model.json").read_text()
        )
        ids = {item["id"] for item in data["invariants"]}

        required = {
            "INV-IDENTITY-ROLE",
            "INV-ROLE-AUTHORITY",
            "INV-CAPABILITY-AUTHORITY",
            "INV-EVIDENCE-DECISION",
            "INV-AI-RECOMMENDATION-DECISION",
            "INV-DOMAIN-ORGANIZATION",
            "INV-CURRENT-STATE-HISTORY",
            "INV-REGISTRY-SOURCE-CODE",
        }

        self.assertEqual(ids, required)

    def test_missing_required_invariant_fails(self):
        data = json.loads(
            (ROOT / "manifests/canonical/meta-model.json").read_text()
        )
        broken = copy.deepcopy(data)
        broken["invariants"] = broken["invariants"][1:]

        result = validate_document(
            broken,
            "canonical-meta-model",
        )

        self.assertFalse(result.valid)

    def test_domain_is_structurally_distinct_from_organization(self):
        data = json.loads(
            (ROOT / "manifests/canonical/meta-model.json").read_text()
        )

        invariant = next(
            item for item in data["invariants"]
            if item["id"] == "INV-DOMAIN-ORGANIZATION"
        )

        self.assertEqual(invariant["left"], "Domain")
        self.assertEqual(invariant["relation"], "distinct_from")
        self.assertEqual(invariant["right"], "OrganizationUnit")


if __name__ == "__main__":
    unittest.main()


class CanonicalIntegrityTests(unittest.TestCase):

    def test_t01_human_gate_is_approved(self):
        task = json.loads(
            (ROOT / "tasks/T01/task.json").read_text()
        )

        self.assertEqual(
            task["human_gate"]["decision"],
            "approved",
        )

    def test_invalid_lifecycle_datetime_fails(self):
        result = validate_document(
            {
                "current_state": "active",
                "lifecycle_state": "activated",
                "effective_from": "not-a-date-time",
            },
            "canonical-lifecycle",
        )

        self.assertFalse(result.valid)

    def test_cross_object_reference_integrity_passes(self):
        from hdc.canonical import validate_reference_integrity

        role = {
            "identity": {
                "object_id": "ROLE-LECTURER",
                "object_type": "role",
            },
            "references": [],
        }

        authority = {
            "identity": {
                "object_id": "AUTH-GRANT-001",
                "object_type": "authority_grant",
            },
            "references": [
                {
                    "target_id": "ROLE-LECTURER",
                    "target_type": "role",
                    "relation": "granted_to",
                }
            ],
        }

        issues = validate_reference_integrity(
            [role, authority]
        )

        self.assertEqual(issues, ())

    def test_missing_reference_target_fails(self):
        from hdc.canonical import validate_reference_integrity

        authority = {
            "identity": {
                "object_id": "AUTH-GRANT-001",
                "object_type": "authority_grant",
            },
            "references": [
                {
                    "target_id": "ROLE-MISSING",
                    "target_type": "role",
                    "relation": "granted_to",
                }
            ],
        }

        issues = validate_reference_integrity(
            [authority]
        )

        self.assertIn(
            "CANONICAL_REFERENCE_MISSING",
            {issue.code for issue in issues},
        )

    def test_reference_target_type_mismatch_fails(self):
        from hdc.canonical import validate_reference_integrity

        role = {
            "identity": {
                "object_id": "ROLE-LECTURER",
                "object_type": "role",
            },
            "references": [],
        }

        authority = {
            "identity": {
                "object_id": "AUTH-GRANT-001",
                "object_type": "authority_grant",
            },
            "references": [
                {
                    "target_id": "ROLE-LECTURER",
                    "target_type": "identity",
                    "relation": "granted_to",
                }
            ],
        }

        issues = validate_reference_integrity(
            [role, authority]
        )

        self.assertIn(
            "CANONICAL_REFERENCE_TYPE_MISMATCH",
            {issue.code for issue in issues},
        )
