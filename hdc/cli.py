"""Command-line interface for AIOS HDC."""

from __future__ import annotations

import argparse
import sys
from importlib.metadata import PackageNotFoundError, version

from hdc.guard import GuardViolation, evaluate_files
from hdc.validator import ContractValidationError, validate_file


EXIT_OK = 0
EXIT_INVALID = 1
EXIT_ERROR = 2


def package_version() -> str:
    try:
        return version("aios-hdc")
    except PackageNotFoundError:
        return "0.2.0"


def cmd_version(_args: argparse.Namespace) -> int:
    print(f"aios-hdc {package_version()}")
    return EXIT_OK


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        result = validate_file(args.file, args.type)
    except ContractValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_ERROR

    if result.valid:
        print(
            f"PASS: {args.file} conforms to "
            f"{args.type} contract"
        )
        return EXIT_OK

    print(
        f"FAIL: {args.file} violates "
        f"{args.type} contract",
        file=sys.stderr,
    )

    for issue in result.issues:
        print(f"- {issue}", file=sys.stderr)

    return EXIT_INVALID


def cmd_guard(args: argparse.Namespace) -> int:
    try:
        result = evaluate_files(
            task_path=args.task,
            change_path=args.change,
            evidence_path=args.evidence,
            acceptance_path=args.acceptance,
            root=args.root,
        )
    except GuardViolation as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_ERROR

    if result.valid:
        print("PASS: HDC governance invariants satisfied")
        return EXIT_OK

    print("FAIL: HDC governance violation", file=sys.stderr)

    for issue in result.issues:
        print(f"- {issue}", file=sys.stderr)

    return EXIT_INVALID


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hdc",
        description=(
            "AIOS Human-Directed Coding validation "
            "and governance CLI"
        ),
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    version_parser = subparsers.add_parser(
        "version",
        help="Show HDC version",
    )
    version_parser.set_defaults(func=cmd_version)

    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate an HDC contract document",
    )
    validate_parser.add_argument(
        "type",
        choices=[
            "task",
            "change",
            "evidence",
            "acceptance",
            "canonical-identity",
            "canonical-reference",
            "canonical-lifecycle",
            "canonical-object",
            "canonical-meta-model",
        ],
    )
    validate_parser.add_argument("file")
    validate_parser.set_defaults(func=cmd_validate)

    guard_parser = subparsers.add_parser(
        "guard",
        help="Evaluate HDC governance invariants",
    )
    guard_parser.add_argument(
        "--task",
        required=True,
        help="Task contract JSON",
    )
    guard_parser.add_argument(
        "--change",
        help="Change Package JSON",
    )
    guard_parser.add_argument(
        "--evidence",
        help="Engineering Evidence JSON",
    )
    guard_parser.add_argument(
        "--acceptance",
        help="Acceptance Package JSON",
    )
    guard_parser.add_argument(
        "--root",
        default=".",
        help="Repository root",
    )
    guard_parser.set_defaults(func=cmd_guard)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
