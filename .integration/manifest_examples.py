#!/usr/bin/env python3
"""Render and install a complete generic publish manifest contract."""

from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

import sc_compose


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPOSITORY_ROOT / "plugins" / "sc-publish"
ARTIFACT_TEMPLATE = PACKAGE_ROOT / "release" / "publish-artifacts.toml.j2"
INSTALLER = PACKAGE_ROOT / "install.py"


def complete_values() -> dict[str, object]:
    """Return one generic complete contract, including both Python build paths."""
    return {
        "schema_version": 1,
        "project": {
            "name": "example",
            "archive_prefix": "example",
            "description": "Example release package",
            "homepage": "https://example.test/example",
            "license": "MIT",
            "readme_dependency_crate": "example-core",
            "renderer_archive_path": "bin/example",
        },
        "release_targets": [
            {"target": "x86_64-unknown-linux-gnu", "os": "ubuntu-latest", "archive": "tar.gz"},
            {"target": "aarch64-apple-darwin", "os": "macos-latest", "archive": "tar.gz"},
            {"target": "x86_64-apple-darwin", "os": "macos-latest", "archive": "tar.gz"},
            {"target": "x86_64-pc-windows-msvc", "os": "windows-latest", "archive": "zip"},
        ],
        "crates": [
            {
                "artifact": "example-core",
                "package": "example-core",
                "cargo_toml": "crates/example-core/Cargo.toml",
                "required": True,
                "publish": True,
                "publish_order": 1,
                "preflight_check": "locked",
                "wait_after_publish_seconds": 0,
                "verify_install": False,
            },
            {
                "artifact": "example-python",
                "package": "example-python",
                "cargo_toml": "crates/example-python/Cargo.toml",
                "required": True,
                "publish": False,
                "publish_order": 0,
                "preflight_check": "locked",
                "wait_after_publish_seconds": 0,
                "verify_install": True,
            },
        ],
        "release_binaries": [
            {
                "name": "example",
                "bundled_paths": [
                    {
                        "source": "docs",
                        "destination": "share/doc/example",
                        "homebrew_destination_components": ["pkgshare"],
                    }
                ],
            },
            {"name": "example-daemon"},
        ],
        "installed_docs": {
            "source_root": "docs",
            "install_root": "share/doc/example",
            "entrypoint": "share/doc/example/README.md",
        },
        "python_packages": [
            {
                "artifact": "example-wheel",
                "package": "example",
                "manifest": "python/pyproject.toml",
                "module": "example",
                "publish": "pypi",
            }
        ],
        "python_distributions": [
            {
                "name": "example",
                "source": "python",
                "cargo_manifest": "crates/example-python/Cargo.toml",
                "module_path": "python/example",
                "sdist": True,
                "wheels": ["ubuntu-latest", "macos-latest", "windows-latest"],
            },
            {
                "name": "example-plugin",
                "source": "plugin",
                "build_system": "setuptools",
                "module_path": "plugin/src/example_plugin",
                "sdist": True,
                "wheels": ["ubuntu-latest"],
            },
        ],
        "channels": {
            "pypi": {
                "workflow": "pypi-publish.yml",
                "dispatch_inputs": {"target": "production"},
                "credential_rehearsal_inputs": {"target": "testpypi"},
                "test_repository": "testpypi",
                "production_repository": "pypi",
            },
            "homebrew": {
                "workflow": "homebrew-publish.yml",
                "dispatch_inputs": {},
                "tap_repository": "example/homebrew-tap",
                "renderer_target": "x86_64-unknown-linux-gnu",
                "formulas": [
                    {
                        "path": "Formula/example.rb",
                        "template": "release/homebrew/formula.rb.j2",
                        "class": "Example",
                        "binaries": ["example", "example-daemon"],
                        "test_binary": "example-daemon",
                        "test_command": "--help",
                        "test_output": "Example release package",
                        "release_track": "stable",
                    }
                ],
                "assets": [
                    {"key": "macos_arm", "target": "aarch64-apple-darwin"},
                    {"key": "macos_intel", "target": "x86_64-apple-darwin"},
                    {"key": "linux", "target": "x86_64-unknown-linux-gnu"},
                ],
            },
            "winget": {
                "workflow": "winget-publish.yml",
                "dispatch_inputs": {},
                "identifier": "example.example",
                "installer_target": "x86_64-pc-windows-msvc",
            },
            "scoop": {
                "workflow": "scoop-publish.yml",
                "dispatch_inputs": {},
                "bucket_repository": "example/scoop-bucket",
                "manifest_path": "bucket/example.json",
                "manifest_template": "release/scoop/manifest.json.j2",
                "installer_target": "x86_64-pc-windows-msvc",
                "binary": "bin/example.exe",
                "renderer_target": "x86_64-unknown-linux-gnu",
            },
        },
    }


def render(values: dict[str, object]) -> dict[str, object]:
    """Render the full manifest through the pinned Python binding contract."""
    spec = importlib.util.spec_from_file_location("sc_publish_install", INSTALLER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    request = sc_compose.ComposeRequest(
        root=PACKAGE_ROOT,
        mode=sc_compose.ComposeMode.file(str(ARTIFACT_TEMPLATE.relative_to(PACKAGE_ROOT))),
        vars_input=module.template_values(values),
        policy=sc_compose.ComposePolicy(strict_undeclared_variables=True),
    )
    return tomllib.loads(sc_compose.compose_file(request).rendered_text)


def verify_complete_contract() -> None:
    """Assert rendering preserves every required manifest section."""
    values = complete_values()
    assert render(values) == values

    with tempfile.TemporaryDirectory() as directory:
        temporary = Path(directory)
        consumer = temporary / "consumer"
        consumer.mkdir()
        input_path = temporary / "install.json"
        input_path.write_text(json.dumps(values), encoding="utf-8")
        command = [sys.executable, str(INSTALLER), "--input", str(input_path), str(consumer)]
        subprocess.run(command, check=True)
        with (consumer / "release" / "publish-artifacts.toml").open("rb") as source:
            assert tomllib.load(source) == values
        rerun = subprocess.run([*command, "--dry-run"], text=True, capture_output=True, check=False)
        assert rerun.returncode == 0, rerun.stdout + rerun.stderr


if __name__ == "__main__":
    verify_complete_contract()
    print("complete publish manifest contract passed; installer rerun is clean")
