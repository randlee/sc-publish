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
        changed = [k for k in old[2] if old[2][k] != new[2][k]]
        # Credential preflight may add a new liveness probe for an existing
        # root channel.  That is additive shared safety: preserve every
        # existing field while allowing the candidate to require an explicit
        # check that the older kit could not perform.
        for command in changed:
            if command != 'preflight-secret-plan':
                raise AssertionError(f'{source}: runtime contract changed: {changed}')
            before = old[2][command]
            after = new[2][command]
            before_plan, after_plan = json.loads(before), json.loads(after)
            def without_liveness(value):
                if isinstance(value, dict):
                    return {
                        key: without_liveness(item)
                        for key, item in value.items()
                        if key not in {'liveness_checks', 'liveness_channel_checks'}
                    }
                if isinstance(value, list):
                    return [without_liveness(item) for item in value]
                return value
            assert without_liveness(after_plan) == without_liveness(before_plan), f'{source}: preflight contract changed non-liveness fields'
            assert set(map(json.dumps, before_plan['liveness_checks'])).issubset(
                map(json.dumps, after_plan['liveness_checks'])
            )
            assert set(map(json.dumps, before_plan['liveness_channel_checks'])).issubset(
                map(json.dumps, after_plan['liveness_channel_checks'])
            )
        for key, value in old[1]['channels'].items():
            candidate = new[1]['channels'][key]
            assert all(candidate.get(field) == field_value for field, field_value in value.items()), f'{source}: existing channel contract changed for {key}'
        revision = subprocess.check_output(['git','-C',str(source.parent),'rev-parse','HEAD'],text=True).strip()
        print(json.dumps({'consumer_input':str(source), 'consumer_head':revision, 'input_sha256':hashlib.sha256(source.read_bytes()).hexdigest(), 'install_and_repeat_dry_run':'passed for baseline and candidate', 'unchanged':['rendered artifact manifest','all existing channel contracts',*old[2]]}))


if __name__ == '__main__':
    main()
