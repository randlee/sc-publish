#!/usr/bin/env python3
"""Render representative publish-artifact manifests outside the CI suite.

Run manually from the repository root:

    python3 .integration/manifest_examples.py

The fixtures intentionally contain JSON text rather than reading either
consumer's manifest.  They are durable examples of the installation input
contract for the two current consumers.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPOSITORY_ROOT / "plugins" / "sc-publish"
ARTIFACT_TEMPLATE = PACKAGE_ROOT / "release" / "publish-artifacts.toml.j2"
INSTALLER = PACKAGE_ROOT / "install.py"


SC_COMPOSE_JSON = r"""
{
  "release": {"version_source": "Cargo.toml", "tag_prefix": "v"},
  "artifacts": {
    "crates": [
      {"name": "sc-sha", "publish_order": 1},
      {"name": "sc-composer", "publish_order": 2},
      {"name": "sc-compose", "publish_order": 3}
    ],
    "wheels": [
      {"package": "sc-sha", "python_package": "sc_sha"},
      {"package": "sc-compose", "python_package": "sc_compose"}
    ],
    "binaries": ["sc-compose"]
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


ATM_CORE_JSON = r"""
{
  "release": {"version_source": "Cargo.toml", "tag_prefix": "v"},
  "artifacts": {
    "crates": [
      {"name": "atm-error", "publish_order": 1},
      {"name": "atm-storage", "publish_order": 2},
      {"name": "agent-team-mail-core", "publish_order": 3},
      {"name": "atm-storage-rusqlite", "publish_order": 4},
      {"name": "atm-http-runtime", "publish_order": 5},
      {"name": "atm-daemon-client", "publish_order": 6},
      {"name": "atm-runtime", "publish_order": 7},
      {"name": "atm-template-sc-compose", "publish_order": 8},
      {"name": "atm-daemon-bootstrap", "publish_order": 9},
      {"name": "atm-daemon", "publish_order": 10},
      {"name": "atm-graft", "publish_order": 11},
      {"name": "agent-team-mail", "publish_order": 12}
    ],
    "wheels": [
      {"package": "atm-graft", "python_package": "atm_graft"},
      {"package": "atm-query", "python_package": "atm_query"},
      {"package": "hermes-atm", "python_package": "hermes_atm"}
    ],
    "binaries": ["atm", "atm-daemon"]
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


def render(values: dict[str, object]) -> dict[str, object]:
    """Render the artifact template and return its semantic TOML value."""
    with tempfile.TemporaryDirectory() as directory:
        temporary = Path(directory)
        input_path = temporary / "manifest-input.json"
        output_path = temporary / "publish-artifacts.toml"
        input_path.write_text(json.dumps(values), encoding="utf-8")
        subprocess.run(
            [
                "sc-compose",
                "render",
                "--root",
                str(PACKAGE_ROOT),
                "--file",
                str(ARTIFACT_TEMPLATE),
                "--var-file",
                str(input_path),
                "--strict",
                "--check-render",
                "--output",
                str(output_path),
            ],
            check=True,
        )
        with output_path.open("rb") as output:
            return tomllib.load(output)


def verify_example(name: str, json_text: str) -> None:
    """Assert that a fixed JSON example renders without semantic drift."""
    values = json.loads(json_text)
    rendered = render(values)
    assert rendered["release"] == values["release"], name
    assert rendered["artifacts"]["crates"] == values["artifacts"]["crates"], name
    assert rendered["artifacts"]["wheels"] == values["artifacts"]["wheels"], name
    assert [entry["name"] for entry in rendered["release_binaries"]] == values[
        "artifacts"
    ]["binaries"], name
    for channel_name, channel in values["channels"].items():
        assert rendered["channels"][channel_name] == channel, name


def verify_installer_is_idempotent(name: str, json_text: str) -> None:
    """Install an example into an empty consumer and require a clean rerun."""
    values = json.loads(json_text)
    artifacts = values["artifacts"]
    arguments = [
        sys.executable,
        str(INSTALLER),
        "--crates",
        json.dumps([crate["name"] for crate in artifacts["crates"]]),
        "--wheels",
        json.dumps([wheel["package"] for wheel in artifacts["wheels"]]),
        "--binaries",
        json.dumps(artifacts["binaries"]),
    ]
    with tempfile.TemporaryDirectory() as directory:
        consumer = Path(directory) / name
        consumer.mkdir()
        subprocess.run([*arguments, str(consumer)], check=True)
        clean_rerun = subprocess.run(
            [*arguments, "--dry-run", str(consumer)],
            text=True,
            capture_output=True,
            check=False,
        )
    assert clean_rerun.returncode == 0, clean_rerun.stdout + clean_rerun.stderr


def main() -> None:
    verify_example("sc-compose", SC_COMPOSE_JSON)
    verify_example("atm-core", ATM_CORE_JSON)
    verify_installer_is_idempotent("sc-compose", SC_COMPOSE_JSON)
    verify_installer_is_idempotent("atm-core", ATM_CORE_JSON)
    print("manifest examples passed: sc-compose, atm-core; installer reruns are clean")


if __name__ == "__main__":
    main()
