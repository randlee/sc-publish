"""Unit tests for the repository-neutral publish-kit installer."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


INSTALLER = Path(__file__).resolve().parents[3] / "install.py"
SPEC = importlib.util.spec_from_file_location("sc_publish_install", INSTALLER)
assert SPEC is not None and SPEC.loader is not None
INSTALL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALL)


class InstallValuesTests(unittest.TestCase):
    def test_json_list_requires_a_string_array(self) -> None:
        self.assertEqual(INSTALL.json_list('["core", "cli"]', "--crates"), ["core", "cli"])
        with self.assertRaisesRegex(Exception, "JSON array of strings"):
            INSTALL.json_list('{"name": "core"}', "--crates")

    def test_install_values_preserve_requested_artifacts(self) -> None:
        values = INSTALL.install_values(
            Path("/consumer"),
            ["example-core", "example-cli"],
            ["example-python"],
            ["example"],
        )
        self.assertEqual(
            values["artifacts"]["crates"],
            [
                {"name": "example-core", "publish_order": 1},
                {"name": "example-cli", "publish_order": 2},
            ],
        )
        self.assertEqual(
            values["artifacts"]["wheels"],
            [{"package": "example-python", "python_package": "example_python"}],
        )
        self.assertEqual(values["artifacts"]["binaries"], ["example"])
        self.assertTrue(values["channels"]["crates_io"]["enabled"])
        self.assertTrue(values["channels"]["scoop"]["enabled"])


if __name__ == "__main__":
    unittest.main()
