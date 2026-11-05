"""Release-mode setup-sc-lint steps against the published sc-lint archive contract.

Published sc-lint release archives (verified for v0.7.0 through v0.8.6) nest
their binaries as ``sc-lint_<version>_<target>/bin/<binary>``, report their
version in ``version --json`` as ``data.version``, and ship a source tarball
whose ``.just`` directory no longer contains ``run_lint.py``. The action's
default release path must install and verify against that contract.

The tests run the action's real Unix steps in bash. ``curl`` is replaced by a
local shim that serves archives built here, so no network or timing is used.
"""
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tarfile
import tempfile
import unittest

import yaml

ACTION = Path(__file__).resolve().parents[2] / 'actions/setup-sc-lint/action.yml'
TARGET = 'x86_64-unknown-linux-gnu'
BACKENDS = ('sc-lint', 'sc-lint-boundary', 'sc-lint-portability', 'sc-lint-runtime')

FAKE_CURL = """#!/usr/bin/env bash
set -euo pipefail
out=""
url=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --output) out="$2"; shift 2 ;;
    --retry) shift 2 ;;
    -*) shift ;;
    *) url="$1"; shift ;;
  esac
done
case "$url" in
  */releases/download/*) cp "$FIXTURE_RELEASE_ARCHIVE" "$out" ;;
  */archive/refs/tags/*) cp "$FIXTURE_SOURCE_ARCHIVE" "$out" ;;
  *) echo "unexpected url: $url" >&2; exit 22 ;;
esac
"""


def _add(archive, name, data, mode=0o644):
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = mode
    archive.addfile(info, io.BytesIO(data))


def release_archive(path, version):
    prefix = f'sc-lint_{version}_{TARGET}'
    version_json = json.dumps({
        'ok': True, 'command': 'version',
        'data': {'contract_schema': 'sc-lint-version-v1', 'self_contained': True,
                 'status': 'pass', 'tool': 'sc-lint', 'version': version},
        'diagnostics': []})
    with tarfile.open(path, 'w:gz') as archive:
        for name in BACKENDS:
            body = f"#!/usr/bin/env bash\necho '{version_json}'\n".encode()
            _add(archive, f'{prefix}/bin/{name}', body, 0o755)
        _add(archive, f'{prefix}/share/sc-lint/sc-lint-docs/README.md', b'docs\n')


def source_archive(path, version):
    with tarfile.open(path, 'w:gz') as archive:
        _add(archive, f'sc-lint-{version}/.just/prerelease_tag.py', b'# utility\n')


def step(name):
    steps = yaml.safe_load(ACTION.read_text())['runs']['steps']
    return next(x for x in steps if x['name'] == name)


@unittest.skipUnless(shutil.which('bash') and shutil.which('jq'), 'bash and jq required')
class ReleaseModeContractTests(unittest.TestCase):
    def run_step(self, name, root, version, extra_path=''):
        script = root / 'step.sh'
        script.write_text(step(name)['run'])
        env = dict(
            os.environ,
            PATH=os.pathsep.join(filter(None, [extra_path, str(root / 'shim'), os.environ['PATH']])),
            RUNNER_OS='Linux', RUNNER_ARCH='X64', RUNNER_TEMP=str(root / 'temp'),
            GITHUB_PATH=str(root / 'github_path'), GITHUB_WORKSPACE=str(root / 'workspace'),
            SC_LINT_VERSION=version, SC_LINT_REPOSITORY='example/sc-lint',
            FIXTURE_RELEASE_ARCHIVE=str(root / 'release.tar.gz'),
            FIXTURE_SOURCE_ARCHIVE=str(root / 'source.tar.gz'))
        return subprocess.run(['bash', str(script)], cwd=root, env=env,
                              capture_output=True, text=True)

    def prepare(self, directory, version):
        root = Path(directory)
        for sub in ('shim', 'temp', 'workspace'):
            (root / sub).mkdir()
        (root / 'github_path').write_text('')
        curl = root / 'shim/curl'
        curl.write_text(FAKE_CURL)
        curl.chmod(curl.stat().st_mode | stat.S_IXUSR)
        release_archive(root / 'release.tar.gz', version)
        source_archive(root / 'source.tar.gz', version)
        return root

    def test_default_release_path_installs_and_verifies_published_layout(self):
        for version in ('0.8.4', '0.8.6'):
            with self.subTest(version=version), tempfile.TemporaryDirectory() as directory:
                root = self.prepare(directory, version)

                result = self.run_step('Install sc-lint release (Unix)', root, version)
                self.assertEqual(result.returncode, 0, result.stderr)
                path_dirs = (root / 'github_path').read_text().split()
                self.assertEqual(len(path_dirs), 1)
                for backend in BACKENDS:
                    self.assertTrue(os.access(Path(path_dirs[0]) / backend, os.X_OK), backend)

                result = self.run_step('Verify sc-lint version contract', root, version,
                                       extra_path=path_dirs[0])
                self.assertEqual(result.returncode, 0, result.stderr)

                result = self.run_step('Materialize pinned sc-lint Python utilities (Unix)',
                                       root, version, extra_path=path_dirs[0])
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue((root / 'workspace/.just/prerelease_tag.py').is_file())
                self.assertEqual(
                    (root / 'workspace/.just/.sc-lint-runtime-version').read_text().strip(), version)

    def test_version_mismatch_still_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.prepare(directory, '0.8.6')
            result = self.run_step('Install sc-lint release (Unix)', root, '0.8.6')
            self.assertEqual(result.returncode, 0, result.stderr)
            path_dir = (root / 'github_path').read_text().split()[0]
            result = self.run_step('Verify sc-lint version contract', root, '0.8.5',
                                   extra_path=path_dir)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('version contract failed', result.stderr)

    def test_archive_missing_a_backend_still_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.prepare(directory, '0.8.6')
            prefix = f'sc-lint_0.8.6_{TARGET}'
            with tarfile.open(root / 'release.tar.gz', 'w:gz') as archive:
                _add(archive, f'{prefix}/bin/sc-lint', b'#!/usr/bin/env bash\n', 0o755)
            result = self.run_step('Install sc-lint release (Unix)', root, '0.8.6')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('missing sibling backend', result.stderr)


if __name__ == '__main__':
    unittest.main()
