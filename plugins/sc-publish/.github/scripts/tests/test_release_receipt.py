"""Regression coverage for the fail-closed shared preflight receipt."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "release_receipt.py"
SOURCE_COMMIT = "a" * 40


def command(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )


def write_inputs(tmp_path: Path, validation: dict[str, str]) -> tuple[Path, Path, Path]:
    manifest = tmp_path / "publish-artifacts.toml"
    toolchain = tmp_path / "toolchain.yml"
    validation_file = tmp_path / "validation.json"
    manifest.write_text("schema_version = 1\n", encoding="utf-8")
    toolchain.write_text("tool: pinned\n", encoding="utf-8")
    validation_file.write_text(json.dumps(validation), encoding="utf-8")
    return manifest, toolchain, validation_file


def test_successful_receipt_verifies_only_for_matching_inputs(tmp_path: Path) -> None:
    manifest, toolchain, validation = write_inputs(tmp_path, {"workspace-tests": "success"})
    receipt = tmp_path / "receipt.json"

    recorded = command(
        tmp_path,
        "record",
        "--source-commit", SOURCE_COMMIT,
        "--manifest", str(manifest),
        "--toolchain-file", str(toolchain),
        "--validation-file", str(validation),
        "--output", str(receipt),
    )
    verified = command(
        tmp_path,
        "verify",
        "--source-commit", SOURCE_COMMIT,
        "--manifest", str(manifest),
        "--toolchain-file", str(toolchain),
        "--receipt", str(receipt),
    )

    assert recorded.returncode == 0, recorded.stderr
    assert verified.returncode == 0, verified.stderr
    assert json.loads(receipt.read_text(encoding="utf-8"))["outcome"] == "passed"


def test_receipt_fails_closed_for_changed_manifest_or_failed_validation(tmp_path: Path) -> None:
    manifest, toolchain, validation = write_inputs(tmp_path, {"workspace-tests": "failure"})
    receipt = tmp_path / "receipt.json"
    recorded = command(
        tmp_path,
        "record",
        "--source-commit", SOURCE_COMMIT,
        "--manifest", str(manifest),
        "--toolchain-file", str(toolchain),
        "--validation-file", str(validation),
        "--output", str(receipt),
    )
    manifest.write_text("schema_version = 2\n", encoding="utf-8")
    verified = command(
        tmp_path,
        "verify",
        "--source-commit", SOURCE_COMMIT,
        "--manifest", str(manifest),
        "--toolchain-file", str(toolchain),
        "--receipt", str(receipt),
    )

    assert recorded.returncode == 0, recorded.stderr
    assert json.loads(receipt.read_text(encoding="utf-8"))["outcome"] == "escalation_required"
    assert verified.returncode != 0
    assert "fresh preflight required" in verified.stderr
