#!/usr/bin/env python3
"""Install sc-publish assets and render repository-specific manifests."""

from __future__ import annotations

import argparse
import difflib
import json
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
TEMPLATES = {
    Path("release/publish-channel-contracts.toml.j2"): Path(
        "release/publish-channel-contracts.toml"
    ),
    Path("release/publish-artifacts.toml.j2"): Path("release/publish-artifacts.toml"),
}

DEFAULT_CHANNELS = {
    "github_release": {"enabled": True},
    "crates_io": {"enabled": True},
    "pypi": {"enabled": True, "workflow": "pypi-publish.yml"},
    "homebrew": {"enabled": True},
    "scoop": {"enabled": True},
    "winget": {"enabled": True},
}


def json_list(value: str, option: str) -> list[str]:
    """Parse a CLI JSON array of package names."""
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as error:
        raise argparse.ArgumentTypeError(f"{option} must be a JSON array: {error}") from error
    if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
        raise argparse.ArgumentTypeError(f"{option} must be a JSON array of strings")
    return parsed


def discover_crates(consumer: Path) -> list[str]:
    """Return publishable Cargo package names without reading release metadata."""
    if not (consumer / "Cargo.toml").is_file():
        return []
    result = subprocess.run(
        ["cargo", "metadata", "--no-deps", "--format-version", "1"],
        cwd=consumer,
        check=True,
        capture_output=True,
        text=True,
    )
    metadata = json.loads(result.stdout)
    return [
        package["name"]
        for package in metadata["packages"]
        if package.get("publish") != []
    ]


def discover_wheels(consumer: Path) -> list[str]:
    """Return Python project names without reading release metadata."""
    excluded = {".git", "target", ".venv", "venv"}
    wheels = []
    for manifest in sorted(consumer.rglob("pyproject.toml")):
        if any(part in excluded for part in manifest.parts):
            continue
        with manifest.open("rb") as file:
            project = tomllib.load(file).get("project", {})
        name = project.get("name")
        if isinstance(name, str):
            wheels.append(name)
    return wheels


def install_values(consumer: Path, crates: list[str], wheels: list[str], binaries: list[str]) -> dict[str, object]:
    """Build the JSON supplied to sc-compose from source discovery and CLI input."""
    return {
        "release": {"version_source": "Cargo.toml", "tag_prefix": "v"},
        "artifacts": {
            "crates": [
                {"name": name, "publish_order": position}
                for position, name in enumerate(crates, start=1)
            ],
            "wheels": [
                {"package": name, "python_package": name.replace("-", "_")}
                for name in wheels
            ],
            "binaries": binaries,
        },
        "channels": DEFAULT_CHANNELS,
    }


def package_files() -> list[Path]:
    """Return package files that are copied unchanged into a consumer."""
    return sorted(
        path
        for path in PACKAGE_ROOT.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
    )


def print_diff(destination: Path, source: Path, relative: Path) -> None:
    before = destination.read_text(encoding="utf-8").splitlines(keepends=True) if destination.exists() else []
    after = source.read_text(encoding="utf-8").splitlines(keepends=True)
    sys.stdout.writelines(
        difflib.unified_diff(
            before,
            after,
            fromfile=f"consumer/{relative}",
            tofile=f"sc-publish/{relative}",
        )
    )


def render_template(template: Path, install_json: Path, output: Path) -> None:
    subprocess.run(
        [
            "sc-compose",
            "render",
            "--root",
            str(PACKAGE_ROOT),
            "--file",
            str(template),
            "--var-file",
            str(install_json),
            "--strict",
            "--check-render",
            "--output",
            str(output),
        ],
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="show drift and return 1 when installation is needed")
    parser.add_argument(
        "consumer_repository",
        nargs="?",
        type=Path,
        default=Path.cwd(),
        help="consumer repository (default: current directory)",
    )
    parser.add_argument("--crates", metavar="JSON", help="JSON array of crate names")
    parser.add_argument("--wheels", metavar="JSON", help="JSON array of wheel names")
    parser.add_argument("--binaries", metavar="JSON", help="JSON array of release binary names")
    parser.add_argument(
        "--example-json",
        action="store_true",
        help="print source-discovered JSON for manifest generation and exit",
    )
    if len(sys.argv) == 1:
        parser.print_help()
        return 0
    args = parser.parse_args()

    consumer = args.consumer_repository.resolve()
    if not consumer.is_dir():
        parser.error(f"consumer repository does not exist: {consumer}")
    try:
        crates = json_list(args.crates, "--crates") if args.crates else discover_crates(consumer)
        wheels = json_list(args.wheels, "--wheels") if args.wheels else discover_wheels(consumer)
        binaries = json_list(args.binaries, "--binaries") if args.binaries else []
    except (argparse.ArgumentTypeError, subprocess.CalledProcessError, tomllib.TOMLDecodeError) as error:
        parser.error(str(error))
    values = install_values(consumer, crates, wheels, binaries)
    if args.example_json:
        print(json.dumps(values, indent=2))
        return 0

    with tempfile.TemporaryDirectory() as temporary_directory:
        install_json = Path(temporary_directory) / "install.json"
        install_json.write_text(json.dumps(values), encoding="utf-8")
        rendered_templates = {
            template: Path(temporary_directory) / output.name
            for template, output in TEMPLATES.items()
        }
        for template, rendered in rendered_templates.items():
            render_template(template, install_json, rendered)

        changed = False
        for source in package_files():
            relative = source.relative_to(PACKAGE_ROOT)
            destination = consumer / relative
            if destination.exists() and destination.read_bytes() == source.read_bytes():
                continue
            changed = True
            if args.dry_run:
                print_diff(destination, source, relative)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            print(f"copied {relative}")

        for template, output in TEMPLATES.items():
            destination = consumer / output
            rendered = rendered_templates[template]
            if destination.exists() and destination.read_bytes() == rendered.read_bytes():
                continue
            changed = True
            if args.dry_run:
                print_diff(destination, rendered, output)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(rendered, destination)
                print(f"rendered {output}")

    if args.dry_run:
        if changed:
            return 1
        print("Publish-kit assets are in sync.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
