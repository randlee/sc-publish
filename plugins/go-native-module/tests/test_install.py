"""Tests for the strict v1 go-native-module installer contract."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SPEC = importlib.util.spec_from_file_location("go_native_install", ROOT / "install.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def write_source(root: Path) -> None:
    source = root / "bindings" / "sc-sha-go"
    (source / "go" / "sc_sha_go").mkdir(parents=True)
    (source / "native").mkdir()
    (source / "go.mod").write_text("module github.com/example/sc-sha-go\n", encoding="utf-8")
    (source / "README.md").write_text("# fixture\n", encoding="utf-8")
    (source / "Cargo.toml").write_text(
        '[package]\nname = "sc-sha-go"\nversion.workspace = true\n', encoding="utf-8"
    )
    (source / "go" / "sc_sha_go" / "source.go").write_text("package sc_sha_go\n", encoding="utf-8")
    (source / "native" / "targets.toml").write_text(
        "schema_version = 1\n\n[contract]\ngenerated_package = \"go/sc_sha_go\"\nnative_library = \"libsc_sha_go.a\"\n\n"
        "[[targets]]\nrust_target = \"x86_64-unknown-linux-gnu\"\ngoos = \"linux\"\ngoarch = \"amd64\"\nlibrary = \"libsc_sha_go.a\"\n",
        encoding="utf-8",
    )


def values(**changes: object) -> dict[str, object]:
    result: dict[str, object] = {
        "schema_version": 1,
        "package_version": "0.1.0",
        "source": "bindings/sc-sha-go",
        "cargo_package": "sc-sha-go",
        "artifact_prefix": "sc-sha-go",
    }
    result.update(changes)
    return result


class InstallerTests(unittest.TestCase):
    def write_input(self, directory: Path, payload: object) -> Path:
        path = directory / "install.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_valid_install_renders_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            consumer = Path(directory) / "consumer"
            consumer.mkdir()
            write_source(consumer)
            install_values = MODULE.load_input(self.write_input(Path(directory), values()))
            self.assertTrue(MODULE.install(consumer, install_values))
            config = consumer / "release" / "go-native-module.toml"
            self.assertIn('source = "bindings/sc-sha-go"', config.read_text(encoding="utf-8"))
            copied = consumer / ".github" / "scripts" / "go_native_module.py"
            self.assertEqual(copied.read_bytes(), (ROOT / "go_native_module.py").read_bytes())
            before = {path: path.read_bytes() for path in (config, copied)}
            self.assertFalse(MODULE.install(consumer, install_values))
            self.assertEqual(before, {path: path.read_bytes() for path in before})

    def test_dry_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            consumer = root / "consumer"
            consumer.mkdir()
            write_source(consumer)
            input_path = self.write_input(root, values())
            install_values = MODULE.load_input(input_path)
            self.assertTrue(MODULE.install(consumer, install_values, dry_run=True))
            self.assertFalse((consumer / "release" / "go-native-module.toml").exists())
            result = subprocess.run(
                [sys.executable, str(ROOT / "install.py"), "--dry-run", "--input", str(input_path), str(consumer)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("go-native-module.toml", result.stdout)
            self.assertFalse((consumer / "release" / "go-native-module.toml").exists())

    def test_installed_consumer_executes_copied_helper(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            consumer = root / "consumer"
            consumer.mkdir()
            write_source(consumer)
            release = consumer / "release"
            release.mkdir()
            (release / "publish-artifacts.toml").write_text(
                "[[release_targets]]\n"
                'target = "x86_64-unknown-linux-gnu"\n'
                'os = "ubuntu-latest"\n'
                'archive = "tar.gz"\n',
                encoding="utf-8",
            )
            install_values = MODULE.load_input(self.write_input(root, values()))
            MODULE.install(consumer, install_values)
            copied = consumer / ".github" / "scripts" / "go_native_module.py"
            result = subprocess.run(
                [
                    sys.executable,
                    str(copied),
                    "target-matrix",
                    "--manifest",
                    str(release / "publish-artifacts.toml"),
                    "--config",
                    str(release / "go-native-module.toml"),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["include"][0]["target"], "x86_64-unknown-linux-gnu")

    def test_rejects_malformed_schema_wrong_version_and_unsafe_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for payload, expected in (
                ([], "must be an object"),
                ({"schema_version": 2}, "exactly the v1"),
                (values(package_version="9.9.9"), "package_version mismatch"),
                (values(source="../escape"), "safe path"),
            ):
                with self.subTest(payload=payload):
                    with self.assertRaisesRegex(Exception, expected):
                        MODULE.load_input(self.write_input(root, payload))

    def test_rejects_unparseable_json_without_consumer_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            consumer = root / "consumer"
            consumer.mkdir()
            input_path = root / "broken.json"
            input_path.write_text('{"schema_version":', encoding="utf-8")
            with self.assertRaisesRegex(Exception, "--input must contain JSON"):
                MODULE.load_input(input_path)
            result = subprocess.run(
                [sys.executable, str(ROOT / "install.py"), "--input", str(input_path), str(consumer)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertIn("--input must contain JSON", result.stderr)
            self.assertFalse((consumer / ".github").exists())
            self.assertFalse((consumer / "release").exists())

    def test_install_rejects_invalid_binding_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            consumer = root / "consumer"
            consumer.mkdir()
            install_values = MODULE.load_input(self.write_input(root, values()))
            with self.assertRaisesRegex(RuntimeError, "source does not exist"):
                MODULE.install(consumer, install_values)


if __name__ == "__main__":
    unittest.main()
