"""Controlled publication inventories; no network, sleeps, tags or uploads."""
import argparse
import base64
import os
import json
from pathlib import Path
import subprocess
import sys
import tomllib

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from publication_continuity import ContinuityError, check, configuration, normalize_asset
from publication_inventory import Inventory
from test_install import INSTALL, InstallValuesTests


def manifest():
    return {"publication_continuity": {}, "project": {"archive_prefix": "tool"},
            "release_binaries": [{"name": "tool"}],
            "release_targets": [{"target": "cpu-platform", "archive": "zip"}],
            "crates": [{"package": "tool-core", "publish": True}], "channels": {}}


def previous():
    return {"tag": "v1.2.3", "assets": ["tool_1.2.3_cpu-platform.zip", "checksums.txt"],
            "publications": ["crate:tool-core"]}


def approval(identifier):
    return {"identifier": identifier, "reason": "The user approved retiring this publication",
            "approved_by": "release-owner", "approval_ref": "https://example.test/team/repo/issues/12"}


def test_unchanged_surface_and_version_normalized_identifiers():
    result = check(manifest(), previous())
    assert result["status"] == "pass"
    assert "asset:tool_{version}_cpu-platform.zip" in result["published"]
    assert normalize_asset("tool_11.2.30_cpu.zip", "1.2.3") == "tool_11.2.30_cpu.zip"


def test_planted_dropped_asset_is_refused_and_exact_approved_deprecation_is_accepted():
    old = previous()
    old["assets"].append("binding-cpu-platform.zip")
    with pytest.raises(ContinuityError, match="asset:binding-cpu-platform.zip"):
        check(manifest(), old)
    values = manifest()
    values["publication_continuity"]["deprecations"] = [approval("asset:binding-cpu-platform.zip")]
    assert check(values, old)["deprecated"] == ["asset:binding-cpu-platform.zip"]


@pytest.mark.parametrize("field,value", [("reason", ""), ("approved_by", ""),
    ("approval_ref", "not an approval"), ("identifier", ""), ("identifier", "invented:item")])
def test_planted_malformed_deprecations_are_refused(field, value):
    row = approval("asset:binding.zip")
    row[field] = value
    values = manifest()
    values["publication_continuity"]["deprecations"] = [row]
    with pytest.raises(ContinuityError):
        check(values, previous())


@pytest.mark.parametrize("config", [None, False, "yes", [], {"enabled": False},
    {"deprecations": {}}, {"deprecations": [{}]}])
def test_bad_or_bypass_configuration_fails_closed(config):
    values = manifest()
    values["publication_continuity"] = config
    with pytest.raises(ContinuityError):
        configuration(values)


def test_deprecations_cannot_name_never_published_or_retained_items():
    values = manifest()
    values["publication_continuity"]["deprecations"] = [approval("crate:never-published")]
    with pytest.raises(ContinuityError, match="never published"):
        check(values, previous())
    values["publication_continuity"]["deprecations"] = [approval("crate:tool-core")]
    with pytest.raises(ContinuityError, match="does not name a dropped"):
        check(values, previous())


@pytest.mark.parametrize("identifier", ["crate:removed", "pypi:removed", "npm:@scope/removed",
    "go:example.test/team/repo/binding", "homebrew:team/tap/Formula/removed.rb",
    "scoop:team/bucket/removed.json", "winget:Vendor.Removed"])
def test_every_published_channel_drop_is_blocking(identifier):
    old = previous()
    old["publications"].append(identifier)
    with pytest.raises(ContinuityError, match="would drop"):
        check(manifest(), old)


def test_non_adopter_is_unchanged_and_never_needs_inventory_or_repository(tmp_path):
    assert check({}, None) == {"status": "disabled"}
    path = tmp_path / "manifest.toml"
    path.write_text('schema_version = 1\n')
    script = Path(__file__).parents[1] / "publication_continuity.py"
    env = {key: value for key, value in os.environ.items() if key not in {"GITHUB_REPOSITORY", "GH_TOKEN"}}
    env["PATH"] = ""
    result = subprocess.run([sys.executable, str(script), "--manifest", str(path), "--version", "1.3.0"],
                            capture_output=True, text=True, timeout=30, env=env)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"status": "disabled"}


def test_first_release_and_go_tags_without_a_github_release():
    assert check(manifest(), {"tag": None, "assets": [], "publications": []})["status"] == "pass"
    with pytest.raises(ContinuityError, match="go:"):
        check(manifest(), {"tag": None, "assets": [], "publications": ["go:example.test/old"]})


def test_manifest_and_installer_round_trip_only_opt_in_values(tmp_path):
    values = InstallValuesTests.valid_values()
    path = tmp_path / "input.json"
    path.write_text(json.dumps(values))
    plain = INSTALL.load_install_values(path)
    assert INSTALL.template_values(plain)["has_continuity"] is False
    values["publication_continuity"] = {"deprecations": [approval("crate:old")]}
    path.write_text(json.dumps(values))
    parsed = INSTALL.load_install_values(path)
    rendered = INSTALL.template_values(parsed)
    assert rendered["has_continuity"] is True
    assert tomllib.loads("config=" + rendered["publication_continuity"])["config"] == values["publication_continuity"]
    values["publication_continuity"]["deprecations"][0]["approved_by"] = ""
    path.write_text(json.dumps(values))
    with pytest.raises(argparse.ArgumentTypeError):
        INSTALL.load_install_values(path)


def encoded(text):
    return {"encoding": "base64", "content": base64.b64encode(text.encode()).decode()}


def test_actual_previous_inventory_excludes_current_retry_and_queries_old_declared_package():
    calls, probes = [], []
    old_manifest = '[[crates]]\npackage="old-core"\npublish=true\n'
    responses = {
        "repos/team/repo/releases?per_page=100&page=1": [
            {"id": 9, "tag_name": "v1.3.0", "draft": False, "prerelease": False},
            {"id": 8, "tag_name": "v1.2.3", "draft": False, "prerelease": False}],
        "repos/team/repo/releases/8/assets?per_page=100&page=1": [{"name": "old-1.2.3.zip", "state": "uploaded"}],
        "repos/team/repo/contents/release/publish-artifacts.toml?ref=v1.2.3": encoded(old_manifest),
        "repos/team/repo/tags?per_page=100&page=1": [{"name": "binding/v1.1.0"}, {"name": "binding/v1.3.0"}],
        "repos/team/repo/contents/binding/go.mod?ref=binding%2Fv1.1.0": encoded("module example.test/team/repo/binding\n"),
    }
    def query(path):
        calls.append(path)
        assert path in responses, path
        return 200, responses[path]
    def probe(url):
        probes.append(url)
        return "published"
    old = Inventory("team/repo", query=query, probe=probe).previous("1.3.0", "release/publish-artifacts.toml")
    assert old == {"tag": "v1.2.3", "assets": ["old-1.2.3.zip"],
                   "publications": ["crate:old-core", "go:example.test/team/repo/binding"]}
    assert probes == ["https://crates.io/api/v1/crates/old-core/1.2.3"]
    assert not any("releases/9/" in path for path in calls)


@pytest.mark.parametrize("status,value", [(403, None), (500, None), (200, {}),
    (200, [{"id": 1, "tag_name": "v1.2.3"}])])
def test_incomplete_previous_listing_is_not_treated_as_first_release(status, value):
    with pytest.raises(ContinuityError):
        Inventory("team/repo", query=lambda _: (status, value)).previous("1.3.0", "manifest.toml")


def test_unknown_registry_state_fails_closed():
    inventory = Inventory("team/repo", query=lambda _: pytest.fail("no GitHub query"), probe=lambda _: "unknown")
    with pytest.raises(ContinuityError, match="indeterminate"):
        inventory.registries({"crates": [{"package": "old", "publish": True}]}, "1.2.3")


def test_missing_historical_manifest_does_not_guess_a_registry_surface():
    def query(path):
        if "/releases?" in path:
            return 200, [{"id": 8, "tag_name": "v1.2.3", "draft": False, "prerelease": False}]
        if "/assets?" in path:
            return 200, []
        if "/contents/" in path:
            return 404, None
        pytest.fail(path)
    with pytest.raises(ContinuityError, match="inventory cannot be established"):
        Inventory("team/repo", query=query).previous("1.3.0", "manifest.toml")


def test_workflows_block_on_the_same_checker_before_tag_and_in_preflight_summary():
    workflows = Path(__file__).parents[2] / "workflows"
    release = yaml.safe_load((workflows / "release.yml").read_text())
    steps = release["jobs"]["gate-and-tag"]["steps"]
    admission = next(i for i, step in enumerate(steps) if "publication_continuity.py" in step.get("run", ""))
    mutation = next(i for i, step in enumerate(steps) if "git push" in step.get("run", ""))
    assert admission < mutation
    assert "--source-ref" in steps[admission]["run"]
    assert not steps[admission].get("continue-on-error", False)
    preflight = yaml.safe_load((workflows / "release-preflight.yml").read_text())
    steps = preflight["jobs"]["preflight"]["steps"]
    assert any(step.get("id") == "publication_continuity" and "publication_continuity.py" in step["run"] for step in steps)
    gate = next(step for step in steps if step.get("name") == "Deny release after complete preflight summary")
    assert gate["env"]["PUBLICATION_CONTINUITY"] == "${{ steps.publication_continuity.outcome }}"
    assert 'record publication-continuity "${PUBLICATION_CONTINUITY}"' in gate["run"]
