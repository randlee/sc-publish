import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from worker_result import WorkerResultError, aggregate_results, parse_fenced_result


def result(**overrides):
    value = {
        "channel": "npm", "status": "passed", "tag": "v1.2.3", "commit": "a" * 40,
        "command": ["npm", "publish"], "exit_status": 0, "error": None, "attempts": 1,
        "workflow_url": "unavailable", "job_url": "unavailable", "evidence": ["run log"],
        "registry_outcome": "published",
    }
    value.update(overrides)
    return value


def test_success_result_requires_full_provenance():
    parsed = parse_fenced_result("before\n```json\n" + json.dumps(result()) + "\n```\nafter")
    assert parsed["status"] == "passed"


def test_failure_result_preserves_error_details():
    parsed = parse_fenced_result("```json\n" + json.dumps(result(status="failed", exit_status=1, error={"code": "NPM.PUBLISH_FAILED", "details": "denied"})) + "\n```")
    assert parsed["error"]["details"] == "denied"


@pytest.mark.parametrize("text", ["", "```json\n{}\n```", "```json\nnot-json\n```"])
def test_missing_or_malformed_result_fails_closed(text):
    with pytest.raises(WorkerResultError):
        parse_fenced_result(text)


def test_aggregation_rejects_missing_and_mismatched_workers():
    with pytest.raises(WorkerResultError, match="missing worker"):
        aggregate_results([None], ["npm"])
    with pytest.raises(WorkerResultError, match="mismatch"):
        aggregate_results([result(channel="pypi")], ["npm"])
