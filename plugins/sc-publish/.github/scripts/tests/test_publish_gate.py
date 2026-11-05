"""Opt-in consumer publish gate (sc-publish#156).

A consumer check that declares ``before_publish = true`` must pass before every
publication path publishes. A repository that declares no such check must behave
exactly as before. All tests are deterministic: they drive the real runner,
action step and workflow files with controlled inputs; no network, no sleeps.
"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import pytest
import yaml

GITHUB = Path(__file__).resolve().parents[2]
RUNNER = GITHUB / "scripts" / "run-consumer-preflight.sh"
ACTION = GITHUB / "actions" / "run-publish-gate" / "action.yml"
WORKFLOWS = GITHUB / "workflows"
INSTALLER = next(p / "install.py" for p in Path(__file__).resolve().parents if (p / "install.py").is_file())
TEMPLATE_DIR = INSTALLER.parent

# Every workflow that publishes (or pushes a tag/release for) a channel, with
# the job that all of its other jobs must depend on and the gate's label.
PUBLISH_PATHS = {
    "release.yml": ("gate-and-tag", "release"),
    "crates-publish.yml": ("verify-release", "crates-publish"),
    "pypi-publish.yml": ("verify-release", "pypi-publish"),
    "npm-publish.yml": ("publish", "npm-publish"),
    "homebrew-publish.yml": ("verify-release", "homebrew-publish"),
    "winget-publish.yml": ("verify-release", "winget-publish"),
    "scoop-publish.yml": ("verify-release", "scoop-publish"),
    "prerelease-archive.yml": ("plan", "prerelease-archive"),
}


def make_repo(tmp_path, manifest=None):
    script = tmp_path / ".github/scripts/run-consumer-preflight.sh"
    script.parent.mkdir(parents=True)
    shutil.copyfile(RUNNER, script)
    (tmp_path / "release").mkdir()
    if manifest is not None:
        (tmp_path / "release/publish-preflight.toml").write_text(manifest)
    return script


def run_runner(script, *args, env=None):
    return subprocess.run(["bash", str(script), *args], capture_output=True, text=True,
                          env=env or os.environ)


def action_step():
    return yaml.safe_load(ACTION.read_text())["runs"]["steps"][0]


def run_action(root, tag="v1.2.3", path="crates-publish", python_shim=None, version=""):
    script = root / "gate-step.sh"
    script.write_text(action_step()["run"])
    env = dict(os.environ, RELEASE_TAG=tag, PUBLISH_PATH=path, RELEASE_VERSION_INPUT=version)
    if python_shim is not None:
        env["PATH"] = f"{python_shim}{os.pathsep}{env['PATH']}"
    return subprocess.run(["bash", str(script)], cwd=root, env=env, capture_output=True, text=True)


# --- runner: publish mode ---------------------------------------------------

def test_publish_mode_without_manifest_or_opt_in_runs_nothing(tmp_path):
    script = make_repo(tmp_path)
    assert run_runner(script, "--publish").returncode == 0
    (tmp_path / "release/publish-preflight.toml").write_text(
        "[[checks]]\nid='a'\nrun='touch ran-a'\n[[checks]]\nid='b'\nrun='touch ran-b'\nbefore_publish=false\n")
    result = run_runner(script, "--publish")
    assert result.returncode == 0
    assert not (tmp_path / "ran-a").exists() and not (tmp_path / "ran-b").exists()


def test_publish_mode_runs_only_opted_in_checks_and_fails_closed(tmp_path):
    script = make_repo(tmp_path,
        "[[checks]]\nid='plain'\nrun='touch ran-plain'\n"
        "[[checks]]\nid='gate'\nrun='touch ran-gate; exit 9'\nbefore_publish=true\n"
        "[[checks]]\nid='gate-two'\nrun='touch ran-two'\nbefore_publish=true\n")
    result = run_runner(script, "--publish")
    assert result.returncode == 1
    assert "gate: exit 9" in result.stderr
    assert (tmp_path / "ran-gate").exists() and (tmp_path / "ran-two").exists()
    assert not (tmp_path / "ran-plain").exists()


def test_publish_mode_passing_opted_in_checks_proceeds(tmp_path):
    script = make_repo(tmp_path, "[[checks]]\nid='gate'\nrun='exit 0'\nbefore_publish=true\n")
    result = run_runner(script, "--publish")
    assert result.returncode == 0
    assert "OK (1 check(s))" in result.stdout


def test_publish_mode_rejects_non_boolean_flag_before_running_anything(tmp_path):
    script = make_repo(tmp_path,
        "[[checks]]\nid='first'\nrun='touch ran-first'\nbefore_publish=true\n"
        "[[checks]]\nid='bad'\nrun='true'\nbefore_publish='yes'\n")
    result = run_runner(script, "--publish")
    assert result.returncode == 1
    assert "before_publish must be a boolean" in result.stderr
    assert not (tmp_path / "ran-first").exists()


def test_unknown_runner_argument_is_rejected(tmp_path):
    script = make_repo(tmp_path, "[[checks]]\nid='a'\nrun='true'\n")
    result = run_runner(script, "--bogus")
    assert result.returncode == 1
    assert "unknown argument" in result.stderr


def test_default_mode_is_unchanged_and_still_runs_every_check(tmp_path):
    script = make_repo(tmp_path,
        "[[checks]]\nid='plain'\nrun='touch ran-plain'\n"
        "[[checks]]\nid='gate'\nrun='touch ran-gate'\nbefore_publish=true\n")
    assert run_runner(script).returncode == 0
    assert (tmp_path / "ran-plain").exists() and (tmp_path / "ran-gate").exists()


# --- action step ------------------------------------------------------------

def test_action_without_opt_in_is_a_no_op_that_needs_no_tooling(tmp_path):
    make_repo(tmp_path)
    shim = tmp_path / "shim"
    shim.mkdir()
    for name in ("python3", "python"):  # any interpreter use would fail loudly
        (shim / name).write_text("#!/usr/bin/env bash\necho 'unexpected interpreter use' >&2\nexit 99\n")
        (shim / name).chmod(0o755)
    # No manifest at all, then a manifest with checks but no opt-in.
    assert run_action(tmp_path, python_shim=shim).returncode == 0
    (tmp_path / "release/publish-preflight.toml").write_text("[[checks]]\nid='a'\nrun='touch ran'\n")
    result = run_action(tmp_path, python_shim=shim)
    assert result.returncode == 0, result.stderr
    assert "skipping" in result.stdout
    assert not (tmp_path / "ran").exists()


def test_action_opted_in_failing_command_blocks_and_passing_proceeds(tmp_path):
    make_repo(tmp_path, "[[checks]]\nid='gate'\nrun='bash scripts/gate.sh'\nbefore_publish=true\n")
    (tmp_path / "scripts").mkdir()
    gate = tmp_path / "scripts/gate.sh"
    gate.write_text('#!/usr/bin/env bash\n[ -f allow ]\n')
    assert run_action(tmp_path).returncode == 1
    (tmp_path / "allow").write_text("")
    assert run_action(tmp_path).returncode == 0


def test_action_binds_candidate_through_environment(tmp_path):
    make_repo(tmp_path,
        "[[checks]]\nid='gate'\nrun='printf \"%s|%s|%s\" \"$RELEASE_TAG\" \"$RELEASE_VERSION\" \"$PUBLISH_PATH\" > seen'\n"
        "before_publish=true\n")
    assert run_action(tmp_path, tag="v2.5.1", path="scoop-publish").returncode == 0
    assert (tmp_path / "seen").read_text() == "v2.5.1|2.5.1|scoop-publish"


def test_explicit_version_is_used_for_prefixed_tags(tmp_path):
    # prerelease-archive.yml tags are prefixed (prerelease/vX.Y.Z) and the workflow
    # computes the bare version itself; the candidate must not be derived from the tag.
    make_repo(tmp_path,
        "[[checks]]\nid='gate'\nrun='printf \"%s|%s\" \"$RELEASE_TAG\" \"$RELEASE_VERSION\" > seen'\n"
        "before_publish=true\n")
    assert run_action(tmp_path, tag="prerelease/v1.2.3", version="1.2.3",
                      path="prerelease-archive").returncode == 0
    assert (tmp_path / "seen").read_text() == "prerelease/v1.2.3|1.2.3"
    # A prefix that does not start with v is bound the same way.
    assert run_action(tmp_path, tag="pre/4.5.6", version="4.5.6").returncode == 0
    assert (tmp_path / "seen").read_text() == "pre/4.5.6|4.5.6"


def test_action_fails_closed_if_runner_is_missing(tmp_path):
    (tmp_path / "release").mkdir()
    (tmp_path / "release/publish-preflight.toml").write_text(
        "[[checks]]\nid='gate'\nrun='true'\nbefore_publish=true\n")
    assert run_action(tmp_path).returncode != 0


# --- every publication path -------------------------------------------------

def load(name):
    return yaml.safe_load((WORKFLOWS / name).read_text())


def needs(job):
    value = job.get("needs", [])
    return [value] if isinstance(value, str) else list(value)


def reaches(jobs, start, target, seen=None):
    seen = seen or set()
    for dep in needs(jobs[start]):
        if dep == target or (dep not in seen and reaches(jobs, dep, target, seen | {dep})):
            return True
    return False


@pytest.mark.parametrize("workflow", sorted(PUBLISH_PATHS))
def test_every_publication_path_runs_the_gate_before_anything_publishes(workflow):
    gate_job, label = PUBLISH_PATHS[workflow]
    jobs = load(workflow)["jobs"]
    steps = jobs[gate_job]["steps"]
    index = next(i for i, s in enumerate(steps) if s.get("uses") == "./.github/actions/run-publish-gate")
    assert steps[index]["with"]["publish_path"] == label
    assert steps[index]["with"]["release_tag"]
    # No other job may start without passing the gate job.
    for name in jobs:
        if name != gate_job:
            assert reaches(jobs, name, gate_job), f"{workflow}:{name} can run without the gate"
    # Nothing before the gate in its own job may publish, tag or push.
    for step in steps[:index]:
        text = json.dumps(step)
        for forbidden in ("git push", "gh release create", "cargo publish", "npm publish", "twine"):
            assert forbidden not in text, f"{workflow}: '{step.get('name')}' precedes the gate"
    if workflow == "release.yml":
        tag_step = next(i for i, s in enumerate(steps) if s.get("name") == "Ensure tag is correct or create it")
        assert index < tag_step


def test_prerelease_gate_binds_the_version_the_workflow_computed():
    steps = load("prerelease-archive.yml")["jobs"]["plan"]["steps"]
    version_index = next(i for i, s in enumerate(steps) if s.get("id") == "version")
    gate_index = next(i for i, s in enumerate(steps) if s.get("uses") == "./.github/actions/run-publish-gate")
    assert gate_index > version_index  # the gate sees the validated version
    with_ = steps[gate_index]["with"]
    assert with_["release_tag"] == "${{ github.ref_name }}"
    assert with_["release_version"] == "${{ steps.version.outputs.value }}"


# Anything that creates a release, uploads a package or pushes a tag/branch to a
# channel. A workflow containing one must be a gated path, or be the single
# candidate-tag workflow below.
PUBLISH_MARKERS = (
    "gh release create", "gh release upload", "gh release edit", "cargo publish",
    "npm_release.py publish", "twine upload", "maturin upload", "softprops/action-gh-release",
    "winget-releaser", "git push", "git tag ",
)
CANDIDATE_TAG_PUSH = 'git push origin "refs/tags/${candidate_tag}"'


def test_every_workflow_with_a_publish_marker_is_gated_or_candidate_tag_only():
    for path in sorted(WORKFLOWS.glob("*.yml")):
        text = path.read_text()
        if path.name == "release-candidate.yml":
            # Only creates/pushes the release-candidate-vX.Y.Z tag; it cannot create a
            # release, upload an asset or publish a package.
            remainder = text.replace(CANDIDATE_TAG_PUSH, "")
            assert CANDIDATE_TAG_PUSH in text
            assert [m for m in PUBLISH_MARKERS if m in remainder and m not in ("git tag ",)] == []
            continue
        found = [m for m in PUBLISH_MARKERS if m in text]
        if found:
            assert path.name in PUBLISH_PATHS, f"{path.name} has {found} but no publish gate"


def test_any_workflow_declaring_an_environment_is_a_gated_publication_path():
    for path in sorted(WORKFLOWS.glob("*.yml")):
        jobs = yaml.safe_load(path.read_text()).get("jobs", {})
        if any("environment" in job for job in jobs.values()):
            assert path.name in PUBLISH_PATHS, f"{path.name} publishes without the opt-in gate"


# --- installer and rendered manifest ---------------------------------------

def installer():
    spec = importlib.util.spec_from_file_location("sc_publish_install_gate", INSTALLER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def valid_values():
    import test_install
    values = test_install.InstallValuesTests.valid_values()
    for name in ("homebrew", "winget", "scoop"):
        del values["channels"][name]
    del values["project"]["renderer_archive_path"]
    return values


def load_values(module, values):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "input.json"
        path.write_text(json.dumps(values))
        return module.load_install_values(path)


def test_installer_validates_before_publish_as_an_optional_boolean():
    module = installer()
    values = valid_values()
    values["preflight_checks"] = [{"id": "a", "description": "d", "run": "true", "before_publish": True},
                                  {"id": "b", "description": "d", "run": "true"}]
    loaded = load_values(module, values)
    assert loaded["preflight_checks"][0]["before_publish"] is True
    assert "before_publish" not in loaded["preflight_checks"][1]  # absent stays absent
    values["preflight_checks"][0]["before_publish"] = "yes"
    with pytest.raises(Exception, match="before_publish must be a boolean"):
        load_values(module, values)


def render(module, values):
    pytest.importorskip("sc_compose", reason="sc-compose bindings are not provisioned")
    loaded = load_values(module, values)
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "publish-preflight.toml"
        cwd = os.getcwd()
        os.chdir(TEMPLATE_DIR)
        try:
            module.render_template(Path("release/publish-preflight.toml.j2"), loaded, output)
        finally:
            os.chdir(cwd)
        return output.read_text(encoding="utf-8")


def test_render_without_opt_in_is_unchanged_and_with_opt_in_marks_only_that_check():
    module = installer()
    values = valid_values()
    values["preflight_checks"] = [{"id": "a", "description": "d", "run": "bash a.sh"},
                                  {"id": "b", "description": "d", "run": "bash b.sh"}]
    plain = render(module, values)
    assert "before_publish" not in plain
    # Exact bytes the baseline kit (before this change) renders for the same input.
    assert plain.endswith(
        'schema_version = 1\n\n\n[[checks]]\nid = "a"\ndescription = "d"\nrun = "bash a.sh"\n'
        '[[checks]]\nid = "b"\ndescription = "d"\nrun = "bash b.sh"')
    values["preflight_checks"][1]["before_publish"] = True
    opted = render(module, values)
    import tomllib
    checks = tomllib.loads(opted)["checks"]
    assert [c.get("before_publish") for c in checks] == [None, True]
