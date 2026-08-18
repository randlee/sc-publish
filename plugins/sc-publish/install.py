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
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
TEMPLATES = {
    Path("release/publish-channel-contracts.toml.j2"): Path(
        "release/publish-channel-contracts.toml"
    ),
    Path("release/publish-artifacts.toml.j2"): Path("release/publish-artifacts.toml"),
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
    parser.add_argument("consumer_repository", type=Path)
    parser.add_argument("install_json", type=Path, help="JSON object used to render package templates")
    args = parser.parse_args()

    consumer = args.consumer_repository.resolve()
    install_json = args.install_json.resolve()
    if not consumer.is_dir():
        parser.error(f"consumer repository does not exist: {consumer}")
    try:
        values = json.loads(install_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        parser.error(f"install_json must be a readable JSON object: {error}")
    if not isinstance(values, dict):
        parser.error("install_json must contain a JSON object")

    with tempfile.TemporaryDirectory() as temporary_directory:
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
