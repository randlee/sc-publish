"""Strict, credential-safe validation for channel-worker result envelopes."""
from __future__ import annotations

import json
import re
from typing import Any

REQUIRED_FIELDS = {
    "channel", "status", "tag", "commit", "command", "exit_status",
    "error", "attempts", "workflow_url", "job_url", "evidence",
    "registry_outcome",
}
STATUSES = {"passed", "failed", "blocked", "apparently_available", "taken", "indeterminate"}
_FENCE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL | re.IGNORECASE)


class WorkerResultError(ValueError):
    """A missing, malformed, incomplete, or inconsistent worker result."""


def parse_fenced_result(text: str) -> dict[str, Any]:
    matches = _FENCE.findall(text)
    if len(matches) != 1:
        raise WorkerResultError("worker result must contain exactly one fenced JSON object")
    try:
        result = json.loads(matches[0])
    except json.JSONDecodeError as error:
        raise WorkerResultError(f"worker result contains invalid JSON: {error.msg}") from None
    if not isinstance(result, dict):
        raise WorkerResultError("worker result JSON must be an object")
    return validate_result(result)


def validate_result(result: dict[str, Any]) -> dict[str, Any]:
    missing = sorted(REQUIRED_FIELDS - result.keys())
    if missing:
        raise WorkerResultError("worker result missing required fields: " + ", ".join(missing))
    if not isinstance(result["channel"], str) or not result["channel"]:
        raise WorkerResultError("worker result channel must be a non-empty string")
    if result["status"] not in STATUSES:
        raise WorkerResultError("worker result has an invalid status")
    if not isinstance(result["tag"], str) or not result["tag"]:
        raise WorkerResultError("worker result tag must be present")
    if not isinstance(result["commit"], str) or not result["commit"]:
        raise WorkerResultError("worker result commit must be present")
    if not isinstance(result["command"], list) or not all(isinstance(item, str) for item in result["command"]):
        raise WorkerResultError("worker result command must be an argv array")
    if not isinstance(result["exit_status"], int):
        raise WorkerResultError("worker result exit_status must be an integer")
    if not isinstance(result["attempts"], int) or result["attempts"] < 1:
        raise WorkerResultError("worker result attempts must be a positive integer")
    for field in ("evidence", "registry_outcome"):
        if not isinstance(result[field], (str, list, dict)):
            raise WorkerResultError(f"worker result {field} must be structured or text")
    if result["status"] == "passed" and result["error"] not in (None, "", {}):
        raise WorkerResultError("successful worker result must have error=null or empty")
    if result["status"] != "passed" and not result["error"]:
        raise WorkerResultError("failed or blocked worker result must preserve error details")
    return result


def aggregate_results(results: list[dict[str, Any] | None], expected_channels: list[str]) -> list[dict[str, Any]]:
    """Validate every result and fail closed for missing or malformed workers."""
    if len(results) != len(expected_channels):
        raise WorkerResultError("worker result count does not match manifest channels")
    validated = []
    for channel, result in zip(expected_channels, results):
        if result is None:
            raise WorkerResultError(f"missing worker result for channel {channel}")
        item = validate_result(result)
        if item["channel"] != channel:
            raise WorkerResultError(f"worker result channel mismatch: expected {channel}")
        validated.append(item)
    return validated
