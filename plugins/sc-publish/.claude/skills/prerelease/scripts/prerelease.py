#!/usr/bin/env python3
"""GitHub-only prerelease publish/install planner driven by publish-artifacts.toml."""
from __future__ import annotations

import argparse
import subprocess
import sys
import tomllib
from pathlib import Path


def prerelease_manifest() -> dict[str, object]:
    data = tomllib.loads(Path("release/publish-artifacts.toml").read_text(encoding="utf-8"))
    value = data.get("prerelease")
    if not isinstance(value, dict):
        raise SystemExit("[prerelease] is not enabled in release/publish-artifacts.toml")
    return value


def parse_version(value: str) -> str:
    if len(value.split(".")) != 3 or not all(part.isdigit() for part in value.split(".")):
        raise SystemExit("version must be X.Y.Z")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--publish", metavar="X.Y.Z")
    mode.add_argument("--install", nargs="?", const="latest", metavar="X.Y.Z")
    parser.add_argument("--dry-run", action="store_true", help="print the plan without network calls")
    parser.add_argument("--authorized", action="store_true", help="confirm written operator authorization to publish")
    args = parser.parse_args()
    config = prerelease_manifest()
    if args.publish:
        value = parse_version(args.publish)
        tag = f"{config['tag_prefix']}{value}"
        if args.dry_run:
            print(f"would run {config['tag_script']} and publish GitHub prerelease {tag}")
            return 0
        if not args.authorized:
            raise SystemExit("--publish requires written operator authorization")
        subprocess.run(["git", "diff", "--quiet"], check=True)
        subprocess.run(["gh", "auth", "status"], check=True)
        subprocess.run([sys.executable, str(config["tag_script"])], check=True)
        print(f"tagged {tag}; wait for prerelease-archive before verifying Release assets")
        return 0
    value = args.install or "latest"
    command = str(config["post_install"]).replace("{version}", value).replace("{stage_dir}", str(Path(str(config["install_root"])).expanduser() / f"v{value}"))
    if args.dry_run:
        print(f"would install GitHub prerelease {value}: {command}")
        return 0
    subprocess.run(command, shell=True, check=True)
    verified = subprocess.check_output(str(config["verify"]), shell=True, text=True)
    if value != "latest" and value not in verified:
        raise SystemExit(f"verify command did not report {value}")
    print(verified.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
