#!/usr/bin/env python3
"""Provision the pinned sc-compose Python bindings used by publish-kit scripts."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


# The one exact renderer version used by every Python invocation in this
# package. The published wheel provides bindings only; publisher agents use
# their consumer's CLI and do not import these bindings directly.
SC_COMPOSE_VERSION = "1.5.0"


def python_path(venv: Path) -> Path:
    """Return the platform-specific interpreter path in a virtual environment."""
    directory = "Scripts" if sys.platform == "win32" else "bin"
    executable = "python.exe" if sys.platform == "win32" else "python"
    return venv / directory / executable


def installed_version(python: Path) -> str | None:
    """Return installed distribution metadata before importing the binding module."""
    result = subprocess.run(
        [
            str(python),
            "-c",
            "from importlib.metadata import version; print(version('sc-compose'))",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def require_pinned_version(installed: str) -> None:
    """Fail unless the managed wheel exactly matches the package contract."""
    if installed != SC_COMPOSE_VERSION:
        raise SystemExit(
            "managed environment has incompatible sc-compose wheel: "
            f"found {installed!r}; required exactly {SC_COMPOSE_VERSION}."
        )


def install_pinned_wheel(python: Path) -> None:
    """Install the one wheel version the package supports."""
    subprocess.run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            f"sc-compose=={SC_COMPOSE_VERSION}",
        ],
        check=True,
        stdout=sys.stderr,
    )


def provision_pinned_wheel(python: Path) -> None:
    """Install or replace a managed wheel until it exactly matches the pin."""
    existing = installed_version(python)
    if existing != SC_COMPOSE_VERSION:
        install_pinned_wheel(python)
        existing = installed_version(python)
    if existing is None:
        raise SystemExit(
            "managed environment has incompatible sc-compose wheel: "
            "installation completed but its version could not be determined"
        )
    require_pinned_version(existing)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--venv", required=True, type=Path, help="managed virtual environment")
    args = parser.parse_args()
    venv = args.venv.resolve()
    python = python_path(venv)
    if not python.is_file():
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)

    provision_pinned_wheel(python)
    print(python)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
