#!/usr/bin/env python3
"""Create and verify the fail-closed preflight receipt consumed by Release."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
REQUIRED_FIELDS = {
    "schema_version",
    "outcome",
    "source_commit",
    "manifest_sha256",
    "toolchain_sha256",
    "validation_sha256",
    "validation",
}


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise SystemExit(f"required receipt input is not a file: {path}")
    return sha256_bytes(path.read_bytes())


def toolchain_digest(paths: list[Path]) -> str:
    if not paths:
        raise SystemExit("at least one --toolchain-file is required")
    entries: dict[str, str] = {}
    for path in paths:
        key = path.as_posix()
        if key in entries:
            raise SystemExit(f"duplicate toolchain input: {key}")
        entries[key] = sha256_file(path)
    return sha256_bytes(canonical_json(entries))


def load_validation(path: Path) -> dict[str, str]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"invalid validation record {path}: {error}") from error
    if not isinstance(value, dict) or not value:
        raise SystemExit("validation record must be a non-empty object")
    if not all(isinstance(name, str) and isinstance(status, str) for name, status in value.items()):
        raise SystemExit("validation record keys and statuses must be strings")
    return value


def expected_receipt(
    *, source_commit: str, manifest: Path, toolchain_files: list[Path], validation: dict[str, str]
) -> dict[str, Any]:
    if len(source_commit) != 40 or any(char not in "0123456789abcdef" for char in source_commit):
        raise SystemExit("source commit must be a lowercase 40-character Git SHA")
    outcome = "passed" if all(status == "success" for status in validation.values()) else "escalation_required"
    return {
        "schema_version": SCHEMA_VERSION,
        "outcome": outcome,
        "source_commit": source_commit,
        "manifest_sha256": sha256_file(manifest),
        "toolchain_sha256": toolchain_digest(toolchain_files),
        "validation_sha256": sha256_bytes(canonical_json(validation)),
        "validation": validation,
    }


def cmd_record(args: argparse.Namespace) -> int:
    validation = load_validation(Path(args.validation_file))
    receipt = expected_receipt(
        source_commit=args.source_commit,
        manifest=Path(args.manifest),
        toolchain_files=[Path(path) for path in args.toolchain_file],
        validation=validation,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"outcome": receipt["outcome"], "receipt": str(output)}, separators=(",", ":")))
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    path = Path(args.receipt)
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"invalid release receipt {path}: {error}") from error
    if not isinstance(receipt, dict) or set(receipt) != REQUIRED_FIELDS:
        raise SystemExit("release receipt has an invalid schema")
    validation = receipt["validation"]
    if not isinstance(validation, dict) or not validation or not all(
        isinstance(name, str) and isinstance(status, str) for name, status in validation.items()
    ):
        raise SystemExit("release receipt has invalid validation results")
    expected = expected_receipt(
        source_commit=args.source_commit,
        manifest=Path(args.manifest),
        toolchain_files=[Path(item) for item in args.toolchain_file],
        validation=validation,
    )
    mismatches = [
        field for field in ("schema_version", "source_commit", "manifest_sha256", "toolchain_sha256", "validation_sha256")
        if receipt[field] != expected[field]
    ]
    if receipt["outcome"] != "passed":
        mismatches.append("outcome")
    if any(status != "success" for status in validation.values()):
        mismatches.append("validation")
    if mismatches:
        raise SystemExit("release receipt rejected; fresh preflight required: " + ", ".join(mismatches))
    print(json.dumps({"outcome": "passed", "source_commit": args.source_commit}, separators=(",", ":")))
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    subcommands = result.add_subparsers(dest="command", required=True)
    for name, handler in (("record", cmd_record), ("verify", cmd_verify)):
        command = subcommands.add_parser(name)
        command.add_argument("--source-commit", required=True)
        command.add_argument("--manifest", required=True)
        command.add_argument("--toolchain-file", action="append", default=[])
        if name == "record":
            command.add_argument("--validation-file", required=True)
            command.add_argument("--output", required=True)
        else:
            command.add_argument("--receipt", required=True)
        command.set_defaults(func=handler)
    return result


if __name__ == "__main__":
    args = parser().parse_args()
    raise SystemExit(args.func(args))
