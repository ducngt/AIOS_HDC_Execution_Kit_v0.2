"""Canonical Meta-Model integrity validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CanonicalIssue:
    code: str
    message: str


def validate_reference_integrity(
    objects: list[dict[str, Any]],
) -> tuple[CanonicalIssue, ...]:
    """Validate canonical object identifiers and typed references."""

    issues: list[CanonicalIssue] = []
    index: dict[str, str] = {}

    for obj in objects:
        identity = obj.get("identity", {})
        object_id = identity.get("object_id")
        object_type = identity.get("object_type")

        if not object_id or not object_type:
            issues.append(
                CanonicalIssue(
                    "CANONICAL_IDENTITY_MISSING",
                    "Canonical object requires object_id and object_type.",
                )
            )
            continue

        if object_id in index:
            issues.append(
                CanonicalIssue(
                    "CANONICAL_ID_DUPLICATE",
                    f"Duplicate canonical object_id: {object_id}",
                )
            )
            continue

        index[object_id] = object_type

    for obj in objects:
        identity = obj.get("identity", {})
        source_id = identity.get("object_id", "<unknown>")

        for ref in obj.get("references", []):
            target_id = ref.get("target_id")
            target_type = ref.get("target_type")

            if target_id not in index:
                issues.append(
                    CanonicalIssue(
                        "CANONICAL_REFERENCE_MISSING",
                        f"{source_id} references missing target "
                        f"{target_id}.",
                    )
                )
                continue

            actual_type = index[target_id]

            if actual_type != target_type:
                issues.append(
                    CanonicalIssue(
                        "CANONICAL_REFERENCE_TYPE_MISMATCH",
                        f"{source_id} references {target_id} as "
                        f"{target_type}, but target type is "
                        f"{actual_type}.",
                    )
                )

    return tuple(issues)
