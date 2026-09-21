#!/usr/bin/env python3
"""Compare existing consumer contracts against two isolated publish-kit trees.

Read-only with respect to both kits and consumers. Installs only into temporary
folders; never dispatches workflows or accesses a registry.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib


def run(*args):
    result = subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"{args}: {result.stderr}")
    return result.stdout


def inspect(kit, source):
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        run(kit / 'install.py', '--input', source, target)
        assert 'Publish-kit assets are in sync.' in run(kit / 'install.py', '--dry-run', '--input', source, target)
        manifest = target / 'release/publish-artifacts.toml'
        commands = ['python-wheel-matrix', 'python-sdist-matrix', 'list-publish-plan', 'preflight-secret-plan', 'release-asset-patterns']
        outputs = {command:run(target / '.github/scripts/release_artifacts.py', command, '--manifest', manifest) for command in commands}
        # Also compare the actually installed working manifest: it may include
        # runner additions not yet synchronized back into a consumer's input.
        installed = source.parent / 'publish-artifacts.toml'
        if installed.exists():
            outputs['existing installed wheel matrix'] = run(target / '.github/scripts/release_artifacts.py', 'python-wheel-matrix', '--manifest', installed)
        return (tomllib.loads(manifest.read_text()), tomllib.loads((target / 'release/publish-channel-contracts.toml').read_text()), outputs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-kit', required=True, type=Path)
    parser.add_argument('--candidate-kit', required=True, type=Path)
    parser.add_argument('--consumer-input', required=True, type=Path, action='append')
    args = parser.parse_args()
    for source in args.consumer_input:
        old = inspect(args.baseline_kit, source)
        new = inspect(args.candidate_kit, source)
        assert old[0] == new[0], f'{source}: rendered artifact manifest changed'
        assert old[2] == new[2], f'{source}: runtime contract changed: {[k for k in old[2] if old[2][k] != new[2][k]]}'
        assert all(new[1]['channels'][key] == value for key,value in old[1]['channels'].items()), f'{source}: existing channel contract changed'
        revision = subprocess.check_output(['git','-C',str(source.parent),'rev-parse','HEAD'],text=True).strip()
        print(json.dumps({'consumer_input':str(source), 'consumer_head':revision, 'input_sha256':hashlib.sha256(source.read_bytes()).hexdigest(), 'install_and_repeat_dry_run':'passed for baseline and candidate', 'unchanged':['rendered artifact manifest','all existing channel contracts',*old[2]]}))


if __name__ == '__main__':
    main()
