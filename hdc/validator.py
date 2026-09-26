"""Schema validation primitives for AIOS HDC."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_DIR = ROOT / "contracts"


SCHEMAS = {
    "task": "task-contract.schema.json",
    "change": "change-package.schema.json",
    "evidence": "engineering-evidence.schema.json",
    "acceptance": "acceptance-package.schema.json",
    "canonical-identity": "canonical-identity.schema.json",
    "canonical-reference": "canonical-reference.schema.json",
    "canonical-lifecycle": "canonical-lifecycle.schema.json",
    "canonical-object": "canonical-object.schema.json",
    "canonical-meta-model": "canonical-meta-model.schema.json",
}


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    message: str

    def __str__(self) -> str:
        location = self.path or "$"
        return f"{location}: {self.message}"


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    issues: tuple[ValidationIssue, ...]

    def require_valid(self) -> None:
        if not self.valid:
            details = "\n".join(str(issue) for issue in self.issues)
            raise ContractValidationError(details)


class ContractValidationError(ValueError):
    """Raised when a document violates an HDC contract."""


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ContractValidationError(
            f"JSON file not found: {path}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise ContractValidationError(
            f"Invalid JSON in {path}: "
            f"line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc


def _schema_path(contract_type: str) -> Path:
    try:
        filename = SCHEMAS[contract_type]
    except KeyError as exc:
        supported = ", ".join(sorted(SCHEMAS))
        raise ContractValidationError(
            f"Unknown contract type '{contract_type}'. "
            f"Supported types: {supported}"
        ) from exc

    return CONTRACTS_DIR / filename


def load_schema(contract_type: str) -> dict[str, Any]:
    schema = _read_json(_schema_path(contract_type))

    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise ContractValidationError(
            f"Invalid schema for '{contract_type}': {exc.message}"
        ) from exc

    return schema


def validate_document(
    document: Any,
    contract_type: str,
) -> ValidationResult:
    schema = load_schema(contract_type)
    validator = Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    )

    errors = sorted(
        validator.iter_errors(document),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )

    issues = tuple(
        ValidationIssue(
            path=".".join(str(part) for part in error.absolute_path),
            message=error.message,
        )
        for error in errors
    )

    return ValidationResult(
        valid=not issues,
        issues=issues,
    )


def validate_file(
    path: str | Path,
    contract_type: str,
) -> ValidationResult:
    document = _read_json(Path(path))
    return validate_document(document, contract_type)


def require_valid_file(
    path: str | Path,
    contract_type: str,
) -> None:
    validate_file(path, contract_type).require_valid()
