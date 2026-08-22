import hashlib
import importlib.util
import platform
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("uniffi_install", ROOT / "install.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class InstallerTests(unittest.TestCase):
    def test_host_key_rejects_non_linux(self):
        with patch.object(MODULE.platform, "system", return_value="Darwin"):
            with self.assertRaisesRegex(RuntimeError, "Linux-only"):
                MODULE.host_key()

    def test_host_key_normalizes_linux_arm64(self):
        with patch.object(MODULE.platform, "system", return_value="Linux"), patch.object(
            MODULE.platform, "machine", return_value="aarch64"
        ):
            self.assertEqual(MODULE.host_key(), "linux-aarch64")

    def test_url_uses_pinned_release(self):
        manifest = {"repository": "owner/repo", "release_tag": "tag"}
        self.assertEqual(
            MODULE.artifact_url(manifest, {"asset": "tool"}),
            "https://github.com/owner/repo/releases/download/tag/tool",
        )

    def test_install_verifies_checksum_and_mode(self):
        payload = b"fake generator"
        checksum = hashlib.sha256(payload).hexdigest()
        manifest = {
            "repository": "owner/repo",
            "release_tag": "tag",
            "artifacts": {"linux-x86_64": {"asset": "tool", "checksum_asset": "tool.sha256"}},
        }
        with tempfile.TemporaryDirectory() as directory, patch.object(MODULE, "load_manifest", return_value=manifest), patch.object(
            MODULE, "host_key", return_value="linux-x86_64"
        ), patch.object(MODULE, "download", side_effect=lambda _url, path: path.write_bytes(payload)), patch.object(
            MODULE, "release_checksum", return_value=checksum
        ):
            result = MODULE.install(Path(directory))
            self.assertEqual(result.read_bytes(), payload)
            self.assertTrue(result.stat().st_mode & 0o111)

    def test_install_rejects_bad_checksum(self):
        manifest = {
            "repository": "owner/repo",
            "release_tag": "tag",
            "artifacts": {"linux-x86_64": {"asset": "tool", "checksum_asset": "tool.sha256"}},
        }
        with tempfile.TemporaryDirectory() as directory, patch.object(MODULE, "load_manifest", return_value=manifest), patch.object(
            MODULE, "host_key", return_value="linux-x86_64"
        ), patch.object(MODULE, "download", side_effect=lambda _url, path: path.write_bytes(b"payload")), patch.object(
            MODULE, "release_checksum", return_value="bad"
        ):
            with self.assertRaisesRegex(RuntimeError, "checksum mismatch"):
                MODULE.install(Path(directory))

    def test_dry_run_does_not_download(self):
        manifest = {
            "repository": "owner/repo",
            "release_tag": "tag",
            "artifacts": {"linux-x86_64": {"asset": "tool", "checksum_asset": "tool.sha256"}},
        }
        with tempfile.TemporaryDirectory() as directory, patch.object(MODULE, "load_manifest", return_value=manifest), patch.object(
            MODULE, "host_key", return_value="linux-x86_64"
        ), patch.object(MODULE, "download") as download:
            MODULE.install(Path(directory), dry_run=True)
            download.assert_not_called()


if __name__ == "__main__":
    unittest.main()
