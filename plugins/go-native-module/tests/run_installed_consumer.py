#!/usr/bin/env python3
"""Install the package into a temporary consumer and run its copied test suite."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = PACKAGE_ROOT / "install.py"


def package_version() -> str:
    with (PACKAGE_ROOT / "manifest.toml").open("rb") as source:
        return tomllib.load(source)["version"]


def create_consumer_source(root: Path) -> None:
    """Create the minimal valid binding required by the strict installer."""
    source = root / "bindings" / "example-go"
    (source / "go" / "example").mkdir(parents=True)
    (source / "native").mkdir()
    (source / "go.mod").write_text("module example.test/example-go\n", encoding="utf-8")
    (source / "README.md").write_text("# example-go\n", encoding="utf-8")
    (source / "Cargo.toml").write_text(
        '[package]\nname = "example-go"\nversion.workspace = true\n', encoding="utf-8"
    )
    (source / "go" / "example" / "example.go").write_text("package example\n", encoding="utf-8")
    (source / "native" / "targets.toml").write_text(
        "schema_version = 1\n\n[contract]\ngenerated_package = \"go/example\"\nnative_library = \"libexample.a\"\n\n"
        "[[targets]]\nrust_target = \"x86_64-unknown-linux-gnu\"\ngoos = \"linux\"\ngoarch = \"amd64\"\nlibrary = \"libexample.a\"\n",
        encoding="utf-8",
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="go-native-module-installed-") as directory:
        consumer = Path(directory) / "consumer"
        consumer.mkdir()
        create_consumer_source(consumer)
        install_input = Path(directory) / "install.json"
        install_input.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "package_version": package_version(),
                    "source": "bindings/example-go",
                    "cargo_package": "example-go",
                    "artifact_prefix": "example-go",
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [sys.executable, str(INSTALLER), "--input", str(install_input), str(consumer)],
            check=True,
        )
        copied_test = consumer / ".github" / "scripts" / "tests" / "test_go_native_module.py"
        subprocess.run([sys.executable, str(copied_test)], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
