"""Tests for the optional [documentation_bundle] release-archive contract."""

from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import unittest
import warnings
import zipfile
from pathlib import Path
from types import MappingProxyType

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import release_documentation as DOCS
from test_install import INSTALL, InstallValuesTests

PLUGIN_ROOT = SCRIPTS.parents[1]
GOLDEN = Path(__file__).with_name("golden_publish_artifacts_no_bundle.toml")

BUNDLE = {
    "source_directory": "docs/bundle",
    "package_directory": "share/docs",
    "required_files": ["README.md", "guides/start.md"],
}
BINARIES = [{"name": "example"}]


def manifest(declared: bool = True) -> dict:
    return {"documentation_bundle": dict(BUNDLE)} if declared else {}


def write_tree(root: Path, files: list[str]) -> None:
    for name in files:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name, encoding="utf-8")


def make_tar(path: Path, names: list[str]) -> None:
    with tarfile.open(path, "w:gz") as archive:
        for name in names:
            data = name.encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))


def make_zip(path: Path, names: list[str]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for name in names:
            archive.writestr(name, name)


def render_text(values: dict) -> str:
    """Render publish-artifacts.toml; a missing renderer is a failure, not a skip."""
    import sc_compose  # noqa: F401  (ImportError fails the test: the renderer is required)

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "input.json"
        path.write_text(json.dumps(values), encoding="utf-8")
        loaded = INSTALL.load_install_values(path)
        output = Path(directory) / "publish-artifacts.toml"
        previous = Path.cwd()
        os.chdir(PLUGIN_ROOT)
        try:
            INSTALL.render_template(Path("release/publish-artifacts.toml.j2"), loaded, output)
        finally:
            os.chdir(previous)
        return output.read_text(encoding="utf-8")


def run_script(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "release_artifacts.py"), *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )


class BundleContractTests(unittest.TestCase):
    def test_absent_bundle_is_a_no_op(self) -> None:
        self.assertIsNone(DOCS.documentation_bundle({}))
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory) / "stage"
            stage.mkdir()
            DOCS.validate_documentation_bundle({}, Path(directory) / "missing")
            DOCS.stage_documentation_bundle({}, stage)
            self.assertEqual(list(stage.iterdir()), [])
            archive = Path(directory) / "pkg.tar.gz"
            make_tar(archive, ["pkg/bin/example"])
            DOCS.validate_release_archive({}, BINARIES, archive)
        config = {"a": 1}
        self.assertIs(DOCS.package_config_with_bundle({}, config), config)

    def test_declared_bundle_validates_shape(self) -> None:
        self.assertEqual(DOCS.documentation_bundle(manifest()), BUNDLE)
        for key in BUNDLE:
            broken = {"documentation_bundle": {k: v for k, v in BUNDLE.items() if k != key}}
            with self.assertRaises(SystemExit):
                DOCS.documentation_bundle(broken)
        for bad in ("/abs", "../up", "a\\b", ""):
            with self.assertRaises(SystemExit):
                DOCS.documentation_bundle(
                    {"documentation_bundle": {**BUNDLE, "source_directory": bad}}
                )
        with self.assertRaises(SystemExit):
            DOCS.documentation_bundle({"documentation_bundle": {**BUNDLE, "required_files": []}})
        with self.assertRaises(SystemExit):
            DOCS.documentation_bundle(
                {"documentation_bundle": {**BUNDLE, "required_files": ["a", "a"]}}
            )

    def test_package_config_carries_declared_bundle(self) -> None:
        config = DOCS.package_config_with_bundle(manifest(), {"a": 1})
        self.assertEqual(config["documentation_bundle"], BUNDLE)

    def test_validate_reports_missing_and_unexpected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            write_tree(source, BUNDLE["required_files"])
            DOCS.validate_documentation_bundle(manifest(), source)
            (source / "extra.md").write_text("x", encoding="utf-8")
            with self.assertRaises(SystemExit) as raised:
                DOCS.validate_documentation_bundle(manifest(), source)
            self.assertIn("unexpected=['extra.md']", str(raised.exception))
            (source / "extra.md").unlink()
            (source / "README.md").unlink()
            with self.assertRaises(SystemExit) as raised:
                DOCS.validate_documentation_bundle(manifest(), source)
            self.assertIn("missing=['README.md']", str(raised.exception))

    def test_stage_copies_bundle_under_package_directory(self) -> None:
        import os

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_tree(root / "docs/bundle", BUNDLE["required_files"])
            stage = root / "stage"
            stage.mkdir()
            previous = Path.cwd()
            os.chdir(root)
            try:
                DOCS.stage_documentation_bundle(manifest(), stage)
            finally:
                os.chdir(previous)
            staged = {
                p.relative_to(stage / "share/docs").as_posix()
                for p in (stage / "share/docs").rglob("*")
                if p.is_file()
            }
        self.assertEqual(staged, set(BUNDLE["required_files"]))

    def test_archive_validation_tar_and_zip(self) -> None:
        bundle = [f"pkg/share/docs/{name}" for name in BUNDLE["required_files"]]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tar = root / "pkg.tar.gz"
            make_tar(tar, ["pkg/bin/example", *bundle])
            DOCS.validate_release_archive(manifest(), BINARIES, tar)
            zipped = root / "pkg.zip"
            make_zip(zipped, ["pkg/bin/example.exe", *bundle])
            DOCS.validate_release_archive(manifest(), BINARIES, zipped, windows=True)
            with self.assertRaises(SystemExit):
                DOCS.validate_release_archive(manifest(), BINARIES, zipped)

            missing_docs = root / "missing.tar.gz"
            make_tar(missing_docs, ["pkg/bin/example", bundle[0]])
            with self.assertRaises(SystemExit) as raised:
                DOCS.validate_release_archive(manifest(), BINARIES, missing_docs)
            self.assertIn("missing=['guides/start.md']", str(raised.exception))

            extra = root / "extra.zip"
            make_zip(extra, ["pkg/bin/example", *bundle, "pkg/share/docs/other.md"])
            with self.assertRaises(SystemExit) as raised:
                DOCS.validate_release_archive(manifest(), BINARIES, extra)
            self.assertIn("unexpected=['other.md']", str(raised.exception))

            no_binary = root / "nobin.tar.gz"
            make_tar(no_binary, bundle)
            with self.assertRaises(SystemExit):
                DOCS.validate_release_archive(manifest(), BINARIES, no_binary)


class InstallRenderTests(unittest.TestCase):
    def _render(self, values: dict) -> dict:
        return tomllib.loads(render_text(values))

    def test_render_omits_table_when_undeclared(self) -> None:
        rendered = self._render(InstallValuesTests.valid_values())
        self.assertNotIn("documentation_bundle", rendered)

    def test_render_round_trips_declared_bundle(self) -> None:
        values = InstallValuesTests.valid_values()
        values["documentation_bundle"] = dict(BUNDLE)
        rendered = self._render(values)
        self.assertEqual(rendered["documentation_bundle"], BUNDLE)

    def test_load_rejects_incomplete_bundle(self) -> None:
        values = InstallValuesTests.valid_values()
        values["documentation_bundle"] = {**BUNDLE, "required_files": []}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            path.write_text(json.dumps(values), encoding="utf-8")
            with self.assertRaises(argparse.ArgumentTypeError):
                INSTALL.load_install_values(path)


class PathHardeningTests(unittest.TestCase):
    def declared(self, **overrides: object) -> dict:
        return {"documentation_bundle": {**BUNDLE, **overrides}}

    def test_rejects_unnormalized_and_dangerous_paths(self) -> None:
        for key in ("source_directory", "package_directory"):
            for bad in (".", "./a", "a/", "a//b", "a/./b", "a/../b", "C:x", "/abs", "a\\b"):
                with self.subTest(key=key, value=bad), self.assertRaises(SystemExit):
                    DOCS.documentation_bundle(self.declared(**{key: bad}))
        for bad in ("./a.md", "a//b.md", "dir/", "C:x.md", "../x.md"):
            with self.subTest(entry=bad), self.assertRaises(SystemExit):
                DOCS.documentation_bundle(self.declared(required_files=[bad]))

    def test_rejects_package_directory_over_binaries_or_bundled_paths(self) -> None:
        for bad in ("bin", "bin/docs"):
            with self.subTest(value=bad), self.assertRaises(SystemExit):
                DOCS.documentation_bundle(self.declared(package_directory=bad))
        bundled = {
            "release_binaries": [
                {"name": "x", "bundled_paths": [{"source": "s", "destination": "share/doc/x"}]}
            ]
        }
        for bad in ("share", "share/doc", "share/doc/x", "share/doc/x/deeper"):
            with self.subTest(value=bad), self.assertRaises(SystemExit):
                DOCS.documentation_bundle({**bundled, **self.declared(package_directory=bad)})
        DOCS.documentation_bundle({**bundled, **self.declared(package_directory="share/docs")})

    def test_non_table_bundle_is_rejected(self) -> None:
        with self.assertRaises(SystemExit):
            DOCS.documentation_bundle({"documentation_bundle": "docs"})

    def test_stage_refuses_an_existing_destination(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_tree(root / "docs/bundle", BUNDLE["required_files"])
            stage = root / "stage"
            (stage / "share/docs").mkdir(parents=True)
            (stage / "share/docs/keep.txt").write_text("keep", encoding="utf-8")
            previous = Path.cwd()
            os.chdir(root)
            try:
                with self.assertRaises(SystemExit):
                    DOCS.stage_documentation_bundle(manifest(), stage)
            finally:
                os.chdir(previous)
            self.assertTrue((stage / "share/docs/keep.txt").is_file())

    def test_source_validation_rejects_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "src"
            write_tree(source, BUNDLE["required_files"])
            outside = root / "outside.md"
            outside.write_text("x", encoding="utf-8")
            (source / "README.md").unlink()
            (source / "README.md").symlink_to(outside)
            with self.assertRaises(SystemExit) as raised:
                DOCS.validate_documentation_bundle(manifest(), source)
            self.assertIn("symlinks", str(raised.exception))
            (source / "README.md").unlink()
            (source / "README.md").write_text("ok", encoding="utf-8")
            (source / "linked").symlink_to(root, target_is_directory=True)
            with self.assertRaises(SystemExit):
                DOCS.validate_documentation_bundle(manifest(), source)


class ArchiveHardeningTests(unittest.TestCase):
    GOOD = ("pkg/bin/example", *[f"pkg/share/docs/{n}" for n in BUNDLE["required_files"]])

    def check_tar(self, builder) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "pkg.tar.gz"
            with tarfile.open(archive, "w:gz") as output:
                builder(output)
            with self.assertRaises(SystemExit):
                DOCS.validate_release_archive(manifest(), BINARIES, archive)

    def add_all(self, output: tarfile.TarFile, skip: str | None = None) -> None:
        for name in self.GOOD:
            if name == skip:
                continue
            info = tarfile.TarInfo(name)
            info.size = 1
            output.addfile(info, io.BytesIO(b"x"))

    def test_tar_symlink_replacing_required_file(self) -> None:
        def build(output: tarfile.TarFile) -> None:
            self.add_all(output, skip="pkg/share/docs/README.md")
            link = tarfile.TarInfo("pkg/share/docs/README.md")
            link.type = tarfile.SYMTYPE
            link.linkname = "/etc/passwd"
            output.addfile(link)

        self.check_tar(build)

    def test_tar_hardlink_and_extra_symlink(self) -> None:
        def hardlink(output: tarfile.TarFile) -> None:
            self.add_all(output)
            link = tarfile.TarInfo("pkg/share/docs/extra.md")
            link.type = tarfile.LNKTYPE
            link.linkname = "pkg/bin/example"
            output.addfile(link)

        self.check_tar(hardlink)

    def test_tar_unsafe_and_duplicate_names(self) -> None:
        def traversal(output: tarfile.TarFile) -> None:
            self.add_all(output)
            info = tarfile.TarInfo("pkg/share/docs/../../evil")
            info.size = 1
            output.addfile(info, io.BytesIO(b"x"))

        def backslash(output: tarfile.TarFile) -> None:
            self.add_all(output)
            info = tarfile.TarInfo("pkg/share/docs\\evil.md")
            info.size = 1
            output.addfile(info, io.BytesIO(b"x"))

        def duplicate(output: tarfile.TarFile) -> None:
            self.add_all(output)
            info = tarfile.TarInfo(self.GOOD[1])
            info.size = 1
            output.addfile(info, io.BytesIO(b"x"))

        for builder in (traversal, backslash, duplicate):
            with self.subTest(builder=builder.__name__):
                self.check_tar(builder)

    def test_zip_symlink_and_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            linked = root / "linked.zip"
            with zipfile.ZipFile(linked, "w") as output:
                for name in self.GOOD[:-1]:
                    output.writestr(name, "x")
                info = zipfile.ZipInfo(self.GOOD[-1])
                info.external_attr = (0o120777) << 16
                output.writestr(info, "/etc/passwd")
            with self.assertRaises(SystemExit):
                DOCS.validate_release_archive(manifest(), BINARIES, linked)
            duplicated = root / "dup.zip"
            with zipfile.ZipFile(duplicated, "w") as output, warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                for name in [*self.GOOD, self.GOOD[1]]:
                    output.writestr(name, "x")
            with self.assertRaises(SystemExit):
                DOCS.validate_release_archive(manifest(), BINARIES, duplicated)


class InstallValidationTests(unittest.TestCase):
    def load(self, bundle: dict) -> None:
        values = InstallValuesTests.valid_values()
        values["documentation_bundle"] = bundle
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            path.write_text(json.dumps(values), encoding="utf-8")
            INSTALL.load_install_values(path)

    def test_install_mirrors_release_time_rules(self) -> None:
        self.load(dict(BUNDLE))
        bad_bundles = [
            {**BUNDLE, "source_directory": "."},
            {**BUNDLE, "package_directory": "../x"},
            {**BUNDLE, "package_directory": "bin"},
            {**BUNDLE, "package_directory": "docs/"},
            {**BUNDLE, "required_files": ["a.md", "a.md"]},
            {**BUNDLE, "required_files": ["./a.md"]},
        ]
        for bad in bad_bundles:
            with self.subTest(bundle=bad), self.assertRaises(argparse.ArgumentTypeError):
                self.load(bad)


class GoldenAndCliTests(unittest.TestCase):
    def test_absent_render_is_byte_identical_to_the_golden(self) -> None:
        rendered = render_text(InstallValuesTests.valid_values())
        self.assertEqual(rendered, GOLDEN.read_text(encoding="utf-8"))

    def declared_manifest(self, root: Path, targets: list[dict], layout: str | None = None) -> Path:
        values = InstallValuesTests.valid_values()
        if layout is not None:
            values["project"]["archive_layout"] = layout
        values["release_targets"] = targets
        values["documentation_bundle"] = {
            "source_directory": "bundle-src",
            "package_directory": "share/docs",
            "required_files": BUNDLE["required_files"],
        }
        (root / "release").mkdir()
        manifest_path = root / "release" / "publish-artifacts.toml"
        manifest_path.write_text(render_text(values), encoding="utf-8")
        return manifest_path

    def test_cli_round_trip_for_tar_gz_and_zip_through_the_workflow_packager(self) -> None:
        self.round_trip(None)

    def test_cli_round_trip_explicit_kit_layout(self) -> None:
        self.round_trip("kit")

    def test_cli_round_trip_flat_layout(self) -> None:
        self.round_trip("flat")

    def round_trip(self, layout: str | None) -> None:
        flat = layout == "flat"
        targets = [
            {"target": "x86_64-unknown-linux-gnu", "os": "ubuntu-latest", "archive": "tar.gz"},
            {"target": "x86_64-pc-windows-msvc", "os": "windows-latest", "archive": "zip"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = self.declared_manifest(root, targets, layout)
            shutil.copytree(
                SCRIPTS, root / ".github/scripts", ignore=shutil.ignore_patterns("tests", "__pycache__")
            )
            write_tree(root / "bundle-src", BUNDLE["required_files"])
            (root / "docs").mkdir()
            (root / "docs/note.md").write_text("n", encoding="utf-8")

            ok = run_script(
                "validate-documentation-bundle", "--manifest", str(manifest_path),
                "--documentation-directory", str(root / "bundle-src"),
            )
            self.assertEqual(ok.returncode, 0, ok.stderr)
            (root / "bundle-src/extra.md").write_text("x", encoding="utf-8")
            bad = run_script(
                "validate-documentation-bundle", "--manifest", str(manifest_path),
                "--documentation-directory", str(root / "bundle-src"),
            )
            self.assertNotEqual(bad.returncode, 0)
            (root / "bundle-src/extra.md").unlink()

            for target in targets:
                name = target["target"]
                release_dir = root / "target" / name / "release"
                release_dir.mkdir(parents=True)
                binary = "example.exe" if "windows" in name else "example"
                (release_dir / binary).write_text("bin", encoding="utf-8")
                script = packager_python().replace(
                    'target_name = "${{ matrix.target }}"', f"target_name = {name!r}"
                ).replace('version = "${{ needs.gate-and-tag.outputs.release_version }}"', 'version = "1.0.0"')
                env_file = root / f"env-{name}"
                result = subprocess.run(
                    [sys.executable, "-c", script], cwd=root, text=True, capture_output=True,
                    env={**os.environ, "RELEASE_ARTIFACT_MANIFEST": str(manifest_path),
                         "GITHUB_ENV": str(env_file)},
                    check=False, timeout=120,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                archive = root / env_file.read_text(encoding="utf-8").split("=", 1)[1].strip()
                self.assertTrue(archive.name.endswith(target["archive"]))
                if archive.suffix == ".zip":
                    with zipfile.ZipFile(archive) as opened_zip:
                        names = opened_zip.namelist()
                else:
                    with tarfile.open(archive) as opened_tar:
                        names = opened_tar.getnames()
                root_name = archive.name.removesuffix("." + target["archive"])
                binary_name = "example.exe" if "windows" in name else "example"
                if flat:
                    self.assertIn("share/docs/README.md", names)
                    self.assertIn(binary_name, names)
                    self.assertFalse(any(n.startswith(root_name) for n in names))
                else:
                    self.assertIn(f"{root_name}/share/docs/README.md", names)
                    self.assertIn(f"{root_name}/bin/{binary_name}", names)
                checked = run_script(
                    "validate-release-archive", "--manifest", str(manifest_path),
                    "--archive", str(archive), *(["--windows"] if archive.suffix == ".zip" else []),
                )
                self.assertEqual(checked.returncode, 0, checked.stderr)

            config = run_script(
                "release-package-config", "--manifest", str(manifest_path),
                "--target", "x86_64-unknown-linux-gnu",
            )
            payload = json.loads(config.stdout)
            self.assertEqual(payload["documentation_bundle"]["package_directory"], "share/docs")
            self.assertEqual(payload["project"].get("archive_layout"), layout)
            absent_text = render_text(InstallValuesTests.valid_values())
            absent = root / "release" / "absent.toml"
            absent.write_text(absent_text, encoding="utf-8")
            config = run_script(
                "release-package-config", "--manifest", str(absent), "--target", "x86_64-unknown-linux-gnu"
            )
            self.assertEqual(config.returncode, 0, config.stderr)
            self.assertNotIn("documentation_bundle", json.loads(config.stdout))
            stage = root / "empty-stage"
            stage.mkdir()
            staged = run_script("stage-documentation-bundle", "--manifest", str(absent), "--stage-directory", str(stage))
            self.assertEqual(staged.returncode, 0, staged.stderr)
            self.assertEqual(list(stage.iterdir()), [])


class FlatLayoutTests(unittest.TestCase):
    FLAT = MappingProxyType(
        {"project": {"archive_layout": "flat"}, "release_binaries": [{"name": "example"}]}
    )

    def flat_manifest(self) -> dict:
        return {**manifest(), **self.FLAT}

    def test_layout_values(self) -> None:
        self.assertEqual(DOCS.archive_layout({}), "kit")
        self.assertEqual(DOCS.archive_layout(self.FLAT), "flat")
        with self.assertRaises(SystemExit):
            DOCS.archive_layout({"project": {"archive_layout": "nested"}})

    def test_flat_archives_validate_for_tar_and_zip(self) -> None:
        members = ["example", *[f"share/docs/{n}" for n in BUNDLE["required_files"]]]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tar = root / "pkg.tar.gz"
            make_tar(tar, members)
            DOCS.validate_release_archive(self.flat_manifest(), BINARIES, tar)
            dotted = root / "dotted.tar.gz"
            make_tar(dotted, [f"./{n}" for n in members])
            DOCS.validate_release_archive(self.flat_manifest(), BINARIES, dotted)
            zipped = root / "pkg.zip"
            make_zip(zipped, ["example.exe", *members[1:]])
            DOCS.validate_release_archive(self.flat_manifest(), BINARIES, zipped, windows=True)
            # A kit-layout archive is rejected under flat, and vice versa.
            nested = root / "nested.tar.gz"
            make_tar(nested, ["pkg/bin/example", *[f"pkg/share/docs/{n}" for n in BUNDLE["required_files"]]])
            with self.assertRaises(SystemExit):
                DOCS.validate_release_archive(self.flat_manifest(), BINARIES, nested)
            with self.assertRaises(SystemExit):
                DOCS.validate_release_archive(manifest(), BINARIES, tar)

    def test_flat_archive_rejects_missing_binary_and_wrong_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            no_binary = root / "nobin.tar.gz"
            make_tar(no_binary, [f"share/docs/{n}" for n in BUNDLE["required_files"]])
            with self.assertRaises(SystemExit):
                DOCS.validate_release_archive(self.flat_manifest(), BINARIES, no_binary)
            extra = root / "extra.tar.gz"
            make_tar(extra, ["example", "share/docs/stray.md",
                             *[f"share/docs/{n}" for n in BUNDLE["required_files"]]])
            with self.assertRaises(SystemExit):
                DOCS.validate_release_archive(self.flat_manifest(), BINARIES, extra)

    def test_flat_package_directory_cannot_collide_with_a_binary(self) -> None:
        for directory in ("example", "example/docs", "example.exe"):
            candidate = {
                **self.FLAT,
                "documentation_bundle": {**BUNDLE, "package_directory": directory},
            }
            with self.subTest(directory=directory), self.assertRaises(SystemExit):
                DOCS.documentation_bundle(candidate)
        flat_bin = {**self.FLAT, "documentation_bundle": {**BUNDLE, "package_directory": "bin"}}
        self.assertIsNotNone(DOCS.documentation_bundle(flat_bin))

    def test_install_validates_and_renders_the_layout(self) -> None:
        values = InstallValuesTests.valid_values()
        values["project"]["archive_layout"] = "nested"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            path.write_text(json.dumps(values), encoding="utf-8")
            with self.assertRaises(argparse.ArgumentTypeError):
                INSTALL.load_install_values(path)
        values["project"]["archive_layout"] = "flat"
        self.assertEqual(tomllib.loads(render_text(values))["project"]["archive_layout"], "flat")
        del values["project"]["archive_layout"]
        self.assertNotIn("archive_layout", tomllib.loads(render_text(values))["project"])


def packager_python() -> str:
    workflow = (PLUGIN_ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    step = workflow.split("      - name: Package manifest-declared release archive\n", 1)[1].split(
        "      - name: Upload artifact\n", 1
    )[0]
    script = step.split("          python3 - <<'PY'\n", 1)[1].split("          PY\n", 1)[0]
    return "\n".join(line[10:] if line else "" for line in script.splitlines())


def documentation_blocks(path: str) -> list[str]:
    text = (PLUGIN_ROOT / ".github/workflows" / path).read_text(encoding="utf-8")
    blocks = []
    for chunk in text.split('if config.get("documentation_bundle"):')[1:]:
        block = chunk.split("          with Path(os.environ", 1)[0] if "validate-release-archive" in chunk else chunk
        blocks.append(" ".join(block.split("archive = Path", 1)[0].split()).replace("sys.executable", '"python3"'))
    return blocks


class WorkflowParityTests(unittest.TestCase):
    def test_release_and_prerelease_bundle_blocks_match(self) -> None:
        release = documentation_blocks("release.yml")
        prerelease = documentation_blocks("prerelease-archive.yml")
        self.assertEqual(len(release), 2)
        self.assertEqual(len(prerelease), 2)
        self.assertEqual(release[0], prerelease[0])
        self.assertIn("stage-documentation-bundle", release[0])
        self.assertIn("validate-release-archive", release[1])
        self.assertIn("validate-release-archive", prerelease[1])

    def test_homebrew_binary_paths_follow_the_archive_layout(self) -> None:
        text = (PLUGIN_ROOT / ".github/workflows/homebrew-publish.yml").read_text(encoding="utf-8")
        self.assertIn('binary if project.get("archive_layout", "kit") == "flat" else f"bin/{binary}"', text)

    def test_release_and_prerelease_packagers_share_the_layout_logic(self) -> None:
        for name in ("release.yml", "prerelease-archive.yml"):
            text = (PLUGIN_ROOT / ".github/workflows" / name).read_text(encoding="utf-8")
            self.assertIn('flat = project.get("archive_layout", "kit") == "flat"', text, name)
            self.assertIn("binary_directory = stage if flat else stage / \"bin\"", text, name)
            self.assertIn("output.add(item, arcname=item.name)", text, name)
            self.assertIn("item.relative_to(stage if flat else stage.parent)", text, name)


if __name__ == "__main__":
    unittest.main()
