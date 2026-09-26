import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from hdc.cli import EXIT_ERROR, EXIT_INVALID, EXIT_OK, main


class CliTests(unittest.TestCase):

    def run_cli(self, argv):
        stdout = io.StringIO()
        stderr = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            with contextlib.redirect_stderr(stderr):
                code = main(argv)

        return code, stdout.getvalue(), stderr.getvalue()

    def test_version(self):
        code, stdout, stderr = self.run_cli(["version"])

        self.assertEqual(code, EXIT_OK)
        self.assertIn("aios-hdc", stdout)
        self.assertEqual(stderr, "")

    def test_validate_current_t00(self):
        code, stdout, stderr = self.run_cli([
            "validate",
            "task",
            "tasks/T00/task.json",
        ])

        self.assertEqual(code, EXIT_OK)
        self.assertIn("PASS:", stdout)
        self.assertEqual(stderr, "")

    def test_validate_invalid_contract_returns_one(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"

            path.write_text(
                json.dumps({
                    "task_id": "INVALID",
                    "title": "Bad",
                    "version": "0.2.0",
                    "status": "implementing",
                    "objective": "Negative test",
                    "human_gate_required": True,
                    "implementation_allowed_before_gate": False,
                }),
                encoding="utf-8",
            )

            code, stdout, stderr = self.run_cli([
                "validate",
                "task",
                str(path),
            ])

        self.assertEqual(code, EXIT_INVALID)
        self.assertEqual(stdout, "")
        self.assertIn("FAIL:", stderr)

    def test_validate_missing_file_returns_two(self):
        code, stdout, stderr = self.run_cli([
            "validate",
            "task",
            "does-not-exist.json",
        ])

        self.assertEqual(code, EXIT_ERROR)
        self.assertEqual(stdout, "")
        self.assertIn("ERROR:", stderr)

    def test_guard_current_t00(self):
        code, stdout, stderr = self.run_cli([
            "guard",
            "--task",
            "tasks/T00/task.json",
            "--change",
            "change-packages/CP-T00.json",
            "--evidence",
            "engineering-evidence/EE-T00.json",
            "--acceptance",
            "acceptance-packages/AP-T00.json",
            "--root",
            ".",
        ])

        self.assertEqual(code, EXIT_OK)
        self.assertIn("PASS:", stdout)
        self.assertEqual(stderr, "")

    def test_guard_missing_task_returns_two(self):
        code, stdout, stderr = self.run_cli([
            "guard",
            "--task",
            "does-not-exist.json",
        ])

        self.assertEqual(code, EXIT_ERROR)
        self.assertEqual(stdout, "")
        self.assertIn("ERROR:", stderr)


if __name__ == "__main__":
    unittest.main()
