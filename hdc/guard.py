"""Governance enforcement for AIOS Human-Directed Coding."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hdc.validator import ContractValidationError, validate_document


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class GuardIssue:
    code: str
    message: str

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


@dataclass(frozen=True)
class GuardResult:
    valid: bool
    issues: tuple[GuardIssue, ...]

    def require_valid(self) -> None:
        if not self.valid:
            raise GuardViolation(
                "\n".join(str(issue) for issue in self.issues)
            )


class GuardViolation(RuntimeError):
    """Raised when HDC governance invariants are violated."""


def _read_json(path: str | Path) -> dict[str, Any]:
    path = Path(path)

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise GuardViolation(f"Artifact not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise GuardViolation(
            f"Invalid JSON in {path}: "
            f"line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc


def _schema_issues(
    document: dict[str, Any],
    contract_type: str,
    artifact_name: str,
) -> list[GuardIssue]:
    try:
        result = validate_document(document, contract_type)
    except ContractValidationError as exc:
        return [
            GuardIssue(
                "SCHEMA_ENGINE_ERROR",
                f"{artifact_name}: {exc}",
            )
        ]

    return [
        GuardIssue(
            "SCHEMA_INVALID",
            f"{artifact_name}: {issue}",
        )
        for issue in result.issues
    ]


def evaluate_governance(
    *,
    task: dict[str, Any],
    change: dict[str, Any] | None = None,
    evidence: dict[str, Any] | None = None,
    acceptance: dict[str, Any] | None = None,
    root: str | Path = ROOT,
) -> GuardResult:
    root = Path(root)
    issues: list[GuardIssue] = []

    issues.extend(_schema_issues(task, "task", "task"))

    if change is not None:
        issues.extend(_schema_issues(change, "change", "change"))

    if evidence is not None:
        issues.extend(
            _schema_issues(evidence, "evidence", "evidence")
        )

    if acceptance is not None:
        issues.extend(
            _schema_issues(
                acceptance,
                "acceptance",
                "acceptance",
            )
        )

    # Stop relational checks when an artifact is structurally invalid.
    if issues:
        return GuardResult(False, tuple(issues))

    task_id = task["task_id"]

    gate = task.get("human_gate")
    gate_required = task["human_gate_required"]
    before_gate = task["implementation_allowed_before_gate"]

    if gate_required and not before_gate:
        if not gate or gate.get("decision") != "approved":
            issues.append(
                GuardIssue(
                    "HUMAN_GATE_REQUIRED",
                    f"{task_id} requires approved Human Gate "
                    "before implementation.",
                )
            )

    if gate and gate.get("record"):
        record = root / gate["record"]

        if not record.is_file():
            issues.append(
                GuardIssue(
                    "DECISION_RECORD_MISSING",
                    f"Human Gate decision record does not exist: "
                    f"{gate['record']}",
                )
            )

    if change is not None:
        if change["task_id"] != task_id:
            issues.append(
                GuardIssue(
                    "TASK_LINK_MISMATCH",
                    "Change Package task_id does not match task.",
                )
            )

    if evidence is not None:
        if change is None:
            issues.append(
                GuardIssue(
                    "CHANGE_REQUIRED",
                    "Engineering Evidence requires a Change Package.",
                )
            )
        else:
            if evidence["task_id"] != task_id:
                issues.append(
                    GuardIssue(
                        "EVIDENCE_TASK_MISMATCH",
                        "Engineering Evidence task_id does not "
                        "match task.",
                    )
                )

            if evidence["change_id"] != change["change_id"]:
                issues.append(
                    GuardIssue(
                        "EVIDENCE_CHANGE_MISMATCH",
                        "Engineering Evidence change_id does not "
                        "match Change Package.",
                    )
                )

    if acceptance is not None:
        if change is None:
            issues.append(
                GuardIssue(
                    "ACCEPTANCE_CHANGE_REQUIRED",
                    "Acceptance Package requires a Change Package.",
                )
            )

        if evidence is None:
            issues.append(
                GuardIssue(
                    "ACCEPTANCE_EVIDENCE_REQUIRED",
                    "Acceptance Package requires Engineering Evidence.",
                )
            )

        if acceptance["task_id"] != task_id:
            issues.append(
                GuardIssue(
                    "ACCEPTANCE_TASK_MISMATCH",
                    "Acceptance Package task_id does not match task.",
                )
            )

        if change is not None:
            if acceptance["change_id"] != change["change_id"]:
                issues.append(
                    GuardIssue(
                        "ACCEPTANCE_CHANGE_MISMATCH",
                        "Acceptance Package change_id does not "
                        "match Change Package.",
                    )
                )

        if evidence is not None:
            if acceptance["evidence_id"] != evidence["evidence_id"]:
                issues.append(
                    GuardIssue(
                        "ACCEPTANCE_EVIDENCE_MISMATCH",
                        "Acceptance Package evidence_id does not "
                        "match Engineering Evidence.",
                    )
                )

        decision_record = root / acceptance["decision_record"]

        if not decision_record.is_file():
            issues.append(
                GuardIssue(
                    "ACCEPTANCE_RECORD_MISSING",
                    "Human acceptance decision record does not exist: "
                    f"{acceptance['decision_record']}",
                )
            )

    return GuardResult(
        valid=not issues,
        issues=tuple(issues),
    )


def evaluate_files(
    *,
    task_path: str | Path,
    change_path: str | Path | None = None,
    evidence_path: str | Path | None = None,
    acceptance_path: str | Path | None = None,
    root: str | Path = ROOT,
) -> GuardResult:
    return evaluate_governance(
        task=_read_json(task_path),
        change=_read_json(change_path) if change_path else None,
        evidence=_read_json(evidence_path) if evidence_path else None,
        acceptance=(
            _read_json(acceptance_path)
            if acceptance_path
            else None
        ),
        root=root,
    )
