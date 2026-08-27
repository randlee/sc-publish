#!/usr/bin/env python3
"""Install a pinned, checksum-verified uniffi-bindgen-go release artifact."""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import stat
import sys
import tempfile
import tomllib
import urllib.error
import urllib.request
from pathlib import Path


PACKAGE = Path(__file__).resolve().parent
MANIFEST = PACKAGE / "manifest.toml"


def host_key() -> str:
    machine = platform.machine().lower()
    aliases = {"x86_64": "x86_64", "amd64": "x86_64", "aarch64": "aarch64", "arm64": "aarch64"}
    try:
        arch = aliases[machine]
    except KeyError as error:
        raise RuntimeError(f"unsupported host architecture: {machine}") from error
    if platform.system().lower() != "linux":
        raise RuntimeError(
            "the generator artifact is Linux-only; run generation on Ubuntu and "
            "consume its generated-source artifact on this platform"
        )
    return f"linux-{arch}"


def load_manifest() -> dict:
    with MANIFEST.open("rb") as stream:
        return tomllib.load(stream)


def artifact_url(manifest: dict, artifact: dict) -> str:
    repository = manifest["repository"]
    tag = manifest["release_tag"]
    return f"https://github.com/{repository}/releases/download/{tag}/{artifact['asset']}"


def download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "sc-publish-uniffi-installer"})
    with urllib.request.urlopen(request, timeout=60) as response, destination.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)


def release_checksum(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "sc-publish-uniffi-installer"})
    with urllib.request.urlopen(request, timeout=60) as response:
        text = response.read().decode("ascii").strip()
    checksum = text.split()[0] if text else ""
    if len(checksum) != 64 or any(character not in "0123456789abcdef" for character in checksum.lower()):
        raise RuntimeError(f"invalid SHA-256 sidecar at {url}")
    return checksum.lower()


def install(destination: Path, *, dry_run: bool = False) -> Path:
    manifest = load_manifest()
    key = host_key()
    artifact = manifest["artifacts"][key]
    target = destination / "uniffi-bindgen-go"
    url = artifact_url(manifest, artifact)
    checksum_url = artifact_url(manifest, {"asset": artifact["checksum_asset"]})
    if dry_run:
        print(f"would install {url} (checksum: {checksum_url}) -> {target}")
        return target
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        downloaded = Path(temporary) / artifact["asset"]
        download(url, downloaded)
        digest = hashlib.sha256()
        with downloaded.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        actual = digest.hexdigest()
        expected = release_checksum(checksum_url)
        if actual != expected:
            raise RuntimeError(f"checksum mismatch: expected {expected}, got {actual}")
        target.write_bytes(downloaded.read_bytes())
    target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"installed {target}")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bin-dir", type=Path, default=Path(".venv/bin"), help="installation directory")
    parser.add_argument("--dry-run", action="store_true", help="print the selected artifact without downloading")
    args = parser.parse_args(argv)
    try:
        install(args.bin_dir.resolve(), dry_run=args.dry_run)
    except (OSError, RuntimeError, KeyError, urllib.error.URLError) as error:
        print(f"uniffi-bindgen-go install failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
