"""Consumer-defined release checks run without repository-specific kit policy."""
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

RUNNER = Path(__file__).resolve().parents[1] / "run-consumer-preflight.sh"


def setup_repo(tmp_path):
    script = tmp_path / ".github/scripts/run-consumer-preflight.sh"
    script.parent.mkdir(parents=True)
    shutil.copyfile(RUNNER, script)
    (tmp_path / "release").mkdir()
    return script


def run(script):
    return subprocess.run(["bash", str(script)], capture_output=True, text=True)


def test_absent_or_empty_manifest_is_noop(tmp_path):
    script = setup_repo(tmp_path)
    assert run(script).returncode == 0
    (tmp_path / "release/publish-preflight.toml").write_text("schema_version = 1\n")
    assert run(script).returncode == 0


@pytest.mark.parametrize("required,expected", [(True, 1), (False, 0)])
def test_check_outcomes_and_verbatim_stderr(tmp_path, required, expected):
    script = setup_repo(tmp_path)
    (tmp_path / "release/publish-preflight.toml").write_text(
        "[[checks]]\nname = 'failure'\ncommand = \"printf 'diagnostic!\\n' >&2; exit 7\"\n"
        f"required = {str(required).lower()}\n"
        "[[checks]]\nid = 'later'\nrun = 'exit 0'\n"
    )
    result = run(script)
    assert result.returncode == expected
    assert "diagnostic!\n" in result.stderr
    assert "failure: exit 7" in result.stdout
    assert "later: exit 0" in result.stdout


def test_evidence_verifier_receives_checked_out_commit_and_rejects_stale(tmp_path):
    script = setup_repo(tmp_path)
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "--allow-empty", "-qm", "candidate"], check=True)
    sha = subprocess.check_output(["git", "-C", str(tmp_path), "rev-parse", "HEAD"], text=True).strip()
    (tmp_path / "verify.py").write_text(
        "import json, os, sys\n"
        "data = json.load(open(os.environ['PREFLIGHT_EVIDENCE_PATH']))\n"
        "sys.exit(0 if data['sha'] == os.environ['PREFLIGHT_CANDIDATE_SHA'] and data['artifact_sha256'] == 'expected' else 1)\n"
    )
    (tmp_path / "release/publish-preflight.toml").write_text(
        "[[checks]]\nid = 'evidence'\nrun = 'python3 verify.py'\nevidence_path = 'release/evidence.json'\n"
    )
    evidence = tmp_path / "release/evidence.json"
    evidence.write_text(json.dumps({"sha": sha, "artifact_sha256": "expected"}))
    assert run(script).returncode == 0
    evidence.write_text(json.dumps({"sha": "stale", "artifact_sha256": "expected"}))
    assert run(script).returncode == 1
    evidence.write_text(json.dumps({"sha": sha, "artifact_sha256": "wrong"}))
    assert run(script).returncode == 1
    evidence.unlink()
    assert run(script).returncode == 1


def test_bad_configuration_rejected_before_any_command(tmp_path):
    script = setup_repo(tmp_path)
    (tmp_path / "release/publish-preflight.toml").write_text(
        "[[checks]]\nid='first'\nrun='touch should-not-exist'\n"
        "[[checks]]\nid='invalid'\nrun='true'\nrequired='yes'\n"
    )
    assert run(script).returncode == 1
    assert not (tmp_path / "should-not-exist").exists()
