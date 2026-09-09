from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[3] / ".claude" / "skills" / "prerelease" / "scripts" / "prerelease.py"


def write_manifest(root: Path) -> None:
    (root / "release").mkdir()
    (root / "release" / "publish-artifacts.toml").write_text(
        "[prerelease]\n"
        'tag_prefix = "prerelease/v"\n'
        'tag_script = ".just/prerelease_tag.py"\n'
        'install_root = "~/.fixture-builds"\n'
        'binaries = ["fixture"]\n'
        'selector_dir = { darwin = "/tmp", linux = "/tmp", windows = "C:\\\\tmp" }\n'
        'post_install = "true"\n'
        'verify = "echo 1.5.11"\n', encoding="utf-8"
    )


class PrereleaseTests(unittest.TestCase):
    def test_publish_dry_run_never_needs_network_or_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_manifest(root)
            result = subprocess.run([sys.executable, str(SCRIPT), "--publish", "1.5.11", "--dry-run"], cwd=root, text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("would run", result.stdout)

    def test_publish_refuses_without_written_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_manifest(root)
            result = subprocess.run([sys.executable, str(SCRIPT), "--publish", "1.5.11"], cwd=root, text=True, capture_output=True, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("authorization", result.stderr)
