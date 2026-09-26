import copy
import tempfile
import unittest
from pathlib import Path

from hdc.guard import GuardViolation, evaluate_governance


TASK = {
    "task_id": "T00",
    "title": "HDC Guard",
    "version": "0.2.0",
    "status": "implementing",
    "objective": "Establish HDC governance baseline.",
    "human_gate_required": True,
    "implementation_allowed_before_gate": False,
    "required_outputs": ["guard"],
    "human_gate": {
        "decision": "approved",
        "record": "governance/decisions/T00_HUMAN_GATE.md",
    },
}

CHANGE = {
    "change_id": "CP-T00-001",
    "task_id": "T00",
    "base_ref": "origin/main",
    "branch": "change/t00-hdc-guard",
    "changed_files": ["hdc/guard.py"],
    "rationale": "Implement HDC Guard.",
}

EVIDENCE = {
    "evidence_id": "EE-T00-001",
    "task_id": "T00",
    "change_id": "CP-T00-001",
    "test_results": {"status": "pass"},
    "verification_results": {"status": "pass"},
    "replay_results": {"status": "pass"},
}

ACCEPTANCE = {
    "acceptance_id": "AP-T00-001",
    "task_id": "T00",
    "change_id": "CP-T00-001",
    "evidence_id": "EE-T00-001",
    "decision_record": "governance/decisions/T00_ACCEPTANCE.md",
    "decision": "accepted",
}


class GuardTests(unittest.TestCase):

    def make_root(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)

        decision_dir = root / "governance" / "decisions"
        decision_dir.mkdir(parents=True)

        (decision_dir / "T00_HUMAN_GATE.md").write_text(
            "APPROVED\n",
            encoding="utf-8",
        )

        (decision_dir / "T00_ACCEPTANCE.md").write_text(
            "ACCEPTED\n",
            encoding="utf-8",
        )

        return temp, root

    def test_valid_linked_chain_passes(self):
        temp, root = self.make_root()

        try:
            result = evaluate_governance(
                task=TASK,
                change=CHANGE,
                evidence=EVIDENCE,
                acceptance=ACCEPTANCE,
                root=root,
            )
            self.assertTrue(result.valid)
            self.assertEqual(result.issues, ())
        finally:
            temp.cleanup()

    def test_missing_human_gate_blocks_implementation(self):
        temp, root = self.make_root()

        try:
            task = copy.deepcopy(TASK)
            task.pop("human_gate")

            result = evaluate_governance(
                task=task,
                change=CHANGE,
                root=root,
            )

            self.assertFalse(result.valid)
            self.assertIn(
                "HUMAN_GATE_REQUIRED",
                {issue.code for issue in result.issues},
            )
        finally:
            temp.cleanup()

    def test_missing_gate_decision_record_fails(self):
        temp, root = self.make_root()

        try:
            (root / TASK["human_gate"]["record"]).unlink()

            result = evaluate_governance(
                task=TASK,
                change=CHANGE,
                root=root,
            )

            self.assertFalse(result.valid)
            self.assertIn(
                "DECISION_RECORD_MISSING",
                {issue.code for issue in result.issues},
            )
        finally:
            temp.cleanup()

    def test_change_task_mismatch_fails(self):
        temp, root = self.make_root()

        try:
            change = copy.deepcopy(CHANGE)
            change["task_id"] = "T01"

            result = evaluate_governance(
                task=TASK,
                change=change,
                root=root,
            )

            self.assertIn(
                "TASK_LINK_MISMATCH",
                {issue.code for issue in result.issues},
            )
        finally:
            temp.cleanup()

    def test_evidence_requires_change(self):
        temp, root = self.make_root()

        try:
            result = evaluate_governance(
                task=TASK,
                evidence=EVIDENCE,
                root=root,
            )

            self.assertIn(
                "CHANGE_REQUIRED",
                {issue.code for issue in result.issues},
            )
        finally:
            temp.cleanup()

    def test_evidence_change_mismatch_fails(self):
        temp, root = self.make_root()

        try:
            evidence = copy.deepcopy(EVIDENCE)
            evidence["change_id"] = "CP-T00-999"

            result = evaluate_governance(
                task=TASK,
                change=CHANGE,
                evidence=evidence,
                root=root,
            )

            self.assertIn(
                "EVIDENCE_CHANGE_MISMATCH",
                {issue.code for issue in result.issues},
            )
        finally:
            temp.cleanup()

    def test_acceptance_requires_evidence(self):
        temp, root = self.make_root()

        try:
            result = evaluate_governance(
                task=TASK,
                change=CHANGE,
                acceptance=ACCEPTANCE,
                root=root,
            )

            self.assertIn(
                "ACCEPTANCE_EVIDENCE_REQUIRED",
                {issue.code for issue in result.issues},
            )
        finally:
            temp.cleanup()

    def test_acceptance_evidence_mismatch_fails(self):
        temp, root = self.make_root()

        try:
            acceptance = copy.deepcopy(ACCEPTANCE)
            acceptance["evidence_id"] = "EE-T00-999"

            result = evaluate_governance(
                task=TASK,
                change=CHANGE,
                evidence=EVIDENCE,
                acceptance=acceptance,
                root=root,
            )

            self.assertIn(
                "ACCEPTANCE_EVIDENCE_MISMATCH",
                {issue.code for issue in result.issues},
            )
        finally:
            temp.cleanup()

    def test_acceptance_requires_decision_record(self):
        temp, root = self.make_root()

        try:
            (root / ACCEPTANCE["decision_record"]).unlink()

            result = evaluate_governance(
                task=TASK,
                change=CHANGE,
                evidence=EVIDENCE,
                acceptance=ACCEPTANCE,
                root=root,
            )

            self.assertIn(
                "ACCEPTANCE_RECORD_MISSING",
                {issue.code for issue in result.issues},
            )
        finally:
            temp.cleanup()

    def test_schema_failure_precedes_relational_checks(self):
        temp, root = self.make_root()

        try:
            change = copy.deepcopy(CHANGE)
            change["change_id"] = "INVALID"

            result = evaluate_governance(
                task=TASK,
                change=change,
                root=root,
            )

            self.assertFalse(result.valid)
            self.assertEqual(
                {issue.code for issue in result.issues},
                {"SCHEMA_INVALID"},
            )
        finally:
            temp.cleanup()

    def test_require_valid_raises(self):
        temp, root = self.make_root()

        try:
            result = evaluate_governance(
                task=TASK,
                evidence=EVIDENCE,
                root=root,
            )

            with self.assertRaises(GuardViolation):
                result.require_valid()
        finally:
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()
