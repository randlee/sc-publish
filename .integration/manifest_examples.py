#!/usr/bin/env python3
"""Render generic publish-artifact examples outside the CI unit-test suite.

Run through the pinned sc-compose wheel provisioned by ``bootstrap_sc_compose.py``.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

import sc_compose


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPOSITORY_ROOT / "plugins" / "sc-publish"
ARTIFACT_TEMPLATE = PACKAGE_ROOT / "release" / "publish-artifacts.toml.j2"
CHANNEL_TEMPLATE = PACKAGE_ROOT / "release" / "publish-channel-contracts.toml.j2"
INSTALLER = PACKAGE_ROOT / "install.py"


SINGLE_CLI_JSON = r"""
{
  "release": {"version_source": "Cargo.toml", "tag_prefix": "v"},
  "artifacts": {
    "crates": [{
      "artifact": "example-cli",
      "package": "example-cli",
      "cargo_toml": "Cargo.toml",
      "required": true,
      "publish": true,
      "publish_order": 1,
      "preflight_check": "full",
      "wait_after_publish_seconds": 0,
      "verify_install": false
    }],
    "wheels": [],
    "binaries": ["example"]
  },
  "channels": {
    "github_release": {"enabled": true},
    "crates_io": {"enabled": true},
    "pypi": {"enabled": false, "workflow": "pypi-publish.yml"},
    "homebrew": {"enabled": false},
    "scoop": {"enabled": false},
    "winget": {"enabled": false}
  }
}
"""


MULTI_ARTIFACT_JSON = r"""
{
  "release": {"version_source": "workspace.package.version", "tag_prefix": "release-"},
  "artifacts": {
    "crates": [
      {
        "artifact": "example-core",
        "package": "example-core",
        "cargo_toml": "crates/example-core/Cargo.toml",
        "required": true,
        "publish": true,
        "publish_order": 1,
        "preflight_check": "full",
        "wait_after_publish_seconds": 0,
        "verify_install": false
      },
      {
        "artifact": "example-service",
        "package": "example-service",
        "cargo_toml": "crates/example-service/Cargo.toml",
        "required": true,
        "publish": true,
        "publish_order": 2,
        "preflight_check": "full",
        "wait_after_publish_seconds": 30,
        "verify_install": false
      }
    ],
    "wheels": [{"package": "example-sdk", "python_package": "example_sdk"}],
    "binaries": ["example", "example-daemon"]
  },
  "channels": {
    "github_release": {"enabled": true},
    "crates_io": {"enabled": true},
    "pypi": {"enabled": true, "workflow": "pypi-publish.yml"},
    "homebrew": {"enabled": true},
    "scoop": {"enabled": true},
    "winget": {"enabled": true}
  }
}
"""


def render(template: Path, values: dict[str, object]) -> dict[str, object]:
    """Render one release template and return its semantic TOML value."""
    request = sc_compose.ComposeRequest(
        root=PACKAGE_ROOT,
        mode=sc_compose.ComposeMode.file(str(template.relative_to(PACKAGE_ROOT))),
        vars_input=values,
        policy=sc_compose.ComposePolicy(strict_undeclared_variables=True),
    )
    return tomllib.loads(sc_compose.compose_file(request).rendered_text)


def verify_example(name: str, json_text: str) -> None:
    """Assert that fixed, generic input renders without semantic drift."""
    values = json.loads(json_text)
    rendered = render(ARTIFACT_TEMPLATE, values)
    assert rendered["release"] == values["release"], name
    assert rendered.get("crates", []) == values["artifacts"]["crates"], name
    assert rendered.get("artifacts", {}).get("wheels", []) == values["artifacts"]["wheels"], name
    assert [entry["name"] for entry in rendered.get("release_binaries", [])] == values[
        "artifacts"
    ]["binaries"], name
    for channel_name, channel in values["channels"].items():
        assert rendered["channels"][channel_name] == channel, name
    rendered_contracts = render(CHANNEL_TEMPLATE, values)
    with CHANNEL_TEMPLATE.open("rb") as source:
        assert rendered_contracts == tomllib.load(source), name


def verify_installer_is_idempotent(name: str, json_text: str) -> None:
    """Require explicit input, install it, then require a clean dry-run rerun."""
    with tempfile.TemporaryDirectory() as directory:
        temporary = Path(directory)
        consumer = temporary / name
        consumer.mkdir()
        input_path = temporary / "install.json"
        input_path.write_text(json_text, encoding="utf-8")
        arguments = [
            sys.executable,
            str(INSTALLER),
            "--input",
            str(input_path),
            str(consumer),
        ]
        subprocess.run(arguments, check=True)
        for source in INSTALLER.parent.rglob("*"):
            if not source.is_file() or "__pycache__" in source.parts:
                continue
            installed = consumer / source.relative_to(INSTALLER.parent)
            assert installed.read_bytes() == source.read_bytes(), installed
        with (consumer / "release" / "publish-artifacts.toml").open("rb") as output:
            rendered_artifacts = tomllib.load(output)
        assert rendered_artifacts["release"] == json.loads(json_text)["release"], name
        with (consumer / "release" / "publish-channel-contracts.toml").open("rb") as output:
            installed_contracts = tomllib.load(output)
        with CHANNEL_TEMPLATE.open("rb") as source:
            assert installed_contracts == tomllib.load(source), name
        clean_rerun = subprocess.run(
            [*arguments, "--dry-run"],
            text=True,
            capture_output=True,
            check=False,
        )
    assert clean_rerun.returncode == 0, clean_rerun.stdout + clean_rerun.stderr


def main() -> None:
    verify_example("single-cli", SINGLE_CLI_JSON)
    verify_example("multi-artifact", MULTI_ARTIFACT_JSON)
    verify_installer_is_idempotent("single-cli", SINGLE_CLI_JSON)
    verify_installer_is_idempotent("multi-artifact", MULTI_ARTIFACT_JSON)
    print("generic manifest examples passed; installer reruns are clean")


if __name__ == "__main__":
    main()
