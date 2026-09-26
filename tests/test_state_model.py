import copy
import json
import unittest
from pathlib import Path

from hdc.guard import evaluate_governance


ROOT = Path(__file__).resolve().parents[1]


def current_task():
    return json.loads(
        (ROOT / "tasks/T00/task.json").read_text(encoding="utf-8")
    )


class StateModelTests(unittest.TestCase):

    def test_current_t00_is_evidenced(self):
        task = current_task()

        self.assertEqual(task["status"], "evidenced")
        self.assertEqual(
            task["human_gate"]["decision"],
            "approved",
        )

    def test_human_gate_approval_does_not_imply_acceptance(self):
        task = current_task()

        result = evaluate_governance(
            task=task,
            root=ROOT,
        )

        self.assertTrue(result.valid)
        self.assertEqual(task["status"], "evidenced")
        self.assertNotEqual(task["status"], "accepted")

    def test_rejected_human_gate_blocks_implementation(self):
        task = copy.deepcopy(current_task())
        task["human_gate"]["decision"] = "rejected"

        result = evaluate_governance(
            task=task,
            root=ROOT,
        )

        self.assertFalse(result.valid)
        self.assertIn(
            "HUMAN_GATE_REQUIRED",
            {issue.code for issue in result.issues},
        )

    def test_accepted_lifecycle_requires_human_acceptance(self):
        task = copy.deepcopy(current_task())
        task["status"] = "accepted"

        result = evaluate_governance(
            task=task,
            root=ROOT,
        )

        self.assertFalse(result.valid)
        self.assertIn(
            "ACCEPTANCE_REQUIRED_FOR_ACCEPTED_STATE",
            {issue.code for issue in result.issues},
        )


if __name__ == "__main__":
    unittest.main()

class AcceptanceDecisionSemanticsTests(unittest.TestCase):

    def test_pending_human_gate_is_schema_valid_but_not_authorized(self):
        task = current_task()
        task = copy.deepcopy(task)
        task["human_gate"]["decision"] = "pending"

        result = evaluate_governance(
            task=task,
            root=ROOT,
        )

        self.assertFalse(result.valid)
        self.assertIn(
            "HUMAN_GATE_REQUIRED",
            {issue.code for issue in result.issues},
        )

    def test_rejected_acceptance_cannot_produce_accepted_lifecycle(self):
        task = copy.deepcopy(current_task())
        task["status"] = "accepted"

        acceptance = {
            "acceptance_id": "AP-T00-TEST",
            "task_id": "T00",
            "change_id": "CP-T00-TEST",
            "evidence_id": "EE-T00-TEST",
            "decision_record":
                "governance/decisions/T00_HUMAN_GATE.md",
            "decision": "rejected"
        }

        change = {
            "change_id": "CP-T00-TEST",
            "task_id": "T00",
            "base_ref": "origin/main",
            "branch": "change/t00-hdc-guard",
            "changed_files": ["hdc/guard.py"],
            "rationale": "State model regression test"
        }

        evidence = {
            "evidence_id": "EE-T00-TEST",
            "task_id": "T00",
            "change_id": "CP-T00-TEST",
            "test_results": {"status": "pass"},
            "verification_results": {"status": "pass"},
            "replay_results": {"status": "pass"}
        }

        result = evaluate_governance(
            task=task,
            change=change,
            evidence=evidence,
            acceptance=acceptance,
            root=ROOT,
        )

        self.assertFalse(result.valid)
        self.assertIn(
            "ACCEPTANCE_DECISION_MISMATCH",
            {issue.code for issue in result.issues},
        )
