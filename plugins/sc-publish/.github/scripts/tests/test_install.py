"""Unit tests for the repository-neutral publish-kit installer."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


INSTALLER = Path(__file__).resolve().parents[3] / "install.py"
SPEC = importlib.util.spec_from_file_location("sc_publish_install", INSTALLER)
assert SPEC is not None and SPEC.loader is not None
INSTALL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALL)


class InstallValuesTests(unittest.TestCase):
    def test_help_explains_the_explicit_install_workflow(self) -> None:
        result = subprocess.run(
            [sys.executable, "-S", str(INSTALLER), "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--write-example INSTALL.json", result.stdout)
        self.assertIn("workflow:", result.stdout)
        self.assertIn("caller-owned JSON input", result.stdout)

    def test_write_example_creates_a_complete_reviewable_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            destination = root / "install.json"
            result = subprocess.run(
                [
                    sys.executable,
                    "-S",
                    str(INSTALLER),
                    "--write-example",
                    str(destination),
                    str(root),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            contract = json.loads(destination.read_text(encoding="utf-8"))
        self.assertEqual(set(contract["channels"]), set(INSTALL.CHANNEL_NAMES))
        self.assertEqual(contract["artifacts"], {"crates": [], "wheels": [], "binaries": []})
        self.assertIn("wrote reviewable install input", result.stdout)

    def test_example_json_enables_only_supported_channels(self) -> None:
        with (
            patch.object(INSTALL, "discover_crates", return_value=["example-core"]),
            patch.object(INSTALL, "discover_wheels", return_value=[]),
            patch.object(INSTALL, "discover_binaries", return_value=[]),
        ):
            values = INSTALL.example_values(Path("consumer"))
        self.assertTrue(values["channels"]["crates_io"]["enabled"])
        self.assertFalse(values["channels"]["pypi"]["enabled"])
        self.assertFalse(values["channels"]["homebrew"]["enabled"])
        self.assertFalse(values["channels"]["winget"]["enabled"])

    def test_load_install_values_requires_explicit_artifacts_and_channels(self) -> None:
        values = {
            "release": {"version_source": "Cargo.toml", "tag_prefix": "v"},
            "artifacts": {
                "crates": [
                    {"name": "example-core", "publish_order": 1},
                    {"name": "example-cli", "publish_order": 2},
                ],
                "wheels": [{"package": "example-python", "python_package": "example_python"}],
                "binaries": ["example"],
            },
            "channels": {
                "github_release": {"enabled": True},
                "crates_io": {"enabled": True},
                "pypi": {"enabled": False, "workflow": "pypi-publish.yml"},
                "homebrew": {"enabled": False},
                "scoop": {"enabled": False},
                "winget": {"enabled": False},
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            path.write_text(json.dumps(values), encoding="utf-8")
            loaded = INSTALL.load_install_values(path)
        self.assertEqual(
            loaded["artifacts"]["crates"],
            [
                {"name": "example-core", "publish_order": 1},
                {"name": "example-cli", "publish_order": 2},
            ],
        )
        self.assertEqual(
            loaded["artifacts"]["wheels"],
            [{"package": "example-python", "python_package": "example_python"}],
        )
        self.assertEqual(loaded["artifacts"]["binaries"], ["example"])
        self.assertTrue(loaded["channels"]["crates_io"]["enabled"])
        self.assertFalse(loaded["channels"]["scoop"]["enabled"])

    def test_load_install_values_rejects_missing_channel_activation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            path.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(Exception, "release must be an object"):
                INSTALL.load_install_values(path)


if __name__ == "__main__":
    unittest.main()
