#!/usr/bin/env python3
"""Provision the renderer version required by the publish-kit templates."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


SC_COMPOSE_VERSION = "1.4.1"


def renderer_path(root: Path) -> Path:
    """Return the platform-specific executable path in a Cargo install root."""
    executable = "sc-compose.exe" if sys.platform == "win32" else "sc-compose"
    return root / "bin" / executable


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="Cargo install root")
    args = parser.parse_args()
    root = args.root.resolve()
    subprocess.run(
        [
            "cargo",
            "install",
            "sc-compose",
            "--version",
            SC_COMPOSE_VERSION,
            "--locked",
            "--root",
            str(root),
        ],
        check=True,
        stdout=sys.stderr,
    )
    renderer = renderer_path(root)
    version = subprocess.check_output([str(renderer), "--version"], text=True).strip()
    expected = f"sc-compose {SC_COMPOSE_VERSION}"
    if version != expected:
        raise SystemExit(f"renderer version mismatch: expected {expected!r}, got {version!r}")
    print(renderer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
