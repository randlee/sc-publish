#!/usr/bin/env python3
"""Install the optional go-native-module peer package into a consumer repository."""

from __future__ import annotations

import argparse
import difflib
import json
import shutil
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Any

from go_native_module import ContractError, validate_binding_source

if TYPE_CHECKING:
    from sc_compose import ComposeRequest


PACKAGE_ROOT = Path(__file__).resolve().parent
MANIFEST = PACKAGE_ROOT / "manifest.toml"
TEMPLATE = PACKAGE_ROOT / "release" / "go-native-module.toml.j2"
INPUT_FIELDS = {"schema_version", "package_version", "source", "cargo_package", "artifact_prefix"}
ASSETS = {
    Path("go_native_module.py"): Path(".github/scripts/go_native_module.py"),
    Path("tests/test_go_native_module.py"): Path(".github/scripts/tests/test_go_native_module.py"),
}


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise argparse.ArgumentTypeError(f"{label} must be an object")
    return value


def _string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise argparse.ArgumentTypeError(f"{label} must be a non-empty string")
    return value


def _safe_relative(value: str, label: str) -> str:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise argparse.ArgumentTypeError(f"{label} must be a repository-relative safe path")
    return path.as_posix()


def package_version() -> str:
    try:
        with MANIFEST.open("rb") as source:
            manifest = tomllib.load(source)
        return _string(manifest.get("version"), "package manifest version")
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise argparse.ArgumentTypeError(f"cannot read package manifest: {error}") from error


def load_input(path: Path) -> dict[str, object]:
    try:
        data = _mapping(json.loads(path.read_text(encoding="utf-8")), "install input")
    except OSError as error:
        raise argparse.ArgumentTypeError(f"cannot read --input {path}: {error}") from error
    except json.JSONDecodeError as error:
        raise argparse.ArgumentTypeError(f"--input must contain JSON: {error}") from error
    if set(data) != INPUT_FIELDS or data.get("schema_version") != 1:
        raise argparse.ArgumentTypeError("install input must contain exactly the v1 schema fields")
    expected = _string(data.get("package_version"), "package_version")
    actual = package_version()
    if expected != actual:
        raise argparse.ArgumentTypeError(
            f"package_version mismatch: input={expected!r}, installed package={actual!r}"
        )
    return {
        "schema_version": 1,
        "package_version": expected,
        "source": _safe_relative(_string(data.get("source"), "source"), "source"),
        "cargo_package": _string(data.get("cargo_package"), "cargo_package"),
        "artifact_prefix": _string(data.get("artifact_prefix"), "artifact_prefix"),
    }


def _template_values(values: dict[str, object]) -> dict[str, object]:
    """Serialize scalar TOML values for the pinned sc-compose renderer."""
    return {
        "schema_version": str(values["schema_version"]),
        "source": json.dumps(values["source"]),
        "cargo_package": json.dumps(values["cargo_package"]),
        "artifact_prefix": json.dumps(values["artifact_prefix"]),
    }


def render_config(values: dict[str, object], output: Path) -> None:
    """Render with the same pinned sc-compose Python-binding contract as core."""
    try:
        import sc_compose
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "sc-compose Python bindings are required to install; run "
            "plugins/sc-publish/.github/scripts/bootstrap_sc_compose.py first"
        ) from error
    request: ComposeRequest = sc_compose.ComposeRequest(
        root=PACKAGE_ROOT,
        mode=sc_compose.ComposeMode.file(str(TEMPLATE.relative_to(PACKAGE_ROOT))),
        vars_input=_template_values(values),
        policy=sc_compose.ComposePolicy(strict_undeclared_variables=True),
    )
    rendered = sc_compose.compose_file(request).rendered_text
    tomllib.loads(rendered)
    output.write_text(rendered, encoding="utf-8")


def _print_diff(destination: Path, source: Path, relative: Path) -> None:
    before = destination.read_text(encoding="utf-8").splitlines(keepends=True) if destination.exists() else []
    after = source.read_text(encoding="utf-8").splitlines(keepends=True)
    sys.stdout.writelines(
        difflib.unified_diff(before, after, fromfile=f"consumer/{relative}", tofile=f"package/{relative}")
    )


def install(consumer: Path, values: dict[str, object], *, dry_run: bool = False) -> bool:
    """Install assets and rendered config; return whether the consumer would change."""
    consumer = consumer.resolve()
    if not consumer.is_dir():
        raise RuntimeError(f"consumer repository does not exist: {consumer}")
    source = (consumer / str(values["source"])).resolve()
    try:
        source.relative_to(consumer)
    except ValueError as error:
        raise RuntimeError("source escapes consumer repository") from error
    if not source.is_dir():
        raise RuntimeError(f"source does not exist: {values['source']}")
    try:
        validate_binding_source(
            consumer,
            str(values["source"]),
            str(values["cargo_package"]),
            str(values["artifact_prefix"]),
        )
    except ContractError as error:
        raise RuntimeError(str(error)) from error
    with tempfile.TemporaryDirectory() as directory:
        rendered = Path(directory) / "go-native-module.toml"
        render_config(values, rendered)
        files = {**ASSETS, Path("release/go-native-module.toml.j2"): Path("release/go-native-module.toml")}
        changed = False
        for package_relative, consumer_relative in files.items():
            source_file = rendered if package_relative == Path("release/go-native-module.toml.j2") else PACKAGE_ROOT / package_relative
            destination = consumer / consumer_relative
            if destination.exists() and destination.read_bytes() == source_file.read_bytes():
                continue
            changed = True
            if dry_run:
                _print_diff(destination, source_file, consumer_relative)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_file, destination)
            print(f"installed {consumer_relative}")
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="v1 consumer install JSON")
    parser.add_argument("--dry-run", action="store_true", help="show drift without changing files")
    parser.add_argument("consumer_repository", nargs="?", default=Path.cwd(), type=Path)
    args = parser.parse_args(argv)
    try:
        values = load_input(args.input)
        changed = install(args.consumer_repository, values, dry_run=args.dry_run)
    except (argparse.ArgumentTypeError, RuntimeError, OSError) as error:
        parser.error(str(error))
    if args.dry_run:
        if changed:
            return 1
        print("go-native-module assets are in sync.")
    else:
        print(f"go-native-module {package_version()} installed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
