"""Execute the release workflow's staging steps without publishing a release."""

import hashlib
import os
from pathlib import Path
import re
import subprocess

import pytest


WORKFLOW = Path(__file__).resolve().parents[2] / "workflows" / "release.yml"


def step_script(name: str) -> str:
    text = WORKFLOW.read_text(encoding="utf-8")
    step = text.split(f"      - name: {name}\n", 1)[1].split("\n      - ", 1)[0]
    script = step.split("        run: |\n", 1)[1]
    return "\n".join(line.removeprefix("          ") for line in script.splitlines())


def run_step(name: str, cwd: Path, env: dict[str, str]) -> None:
    result = subprocess.run(
        ["bash", "-c", step_script(name)],
        cwd=cwd,
        env={**os.environ, **env},
        # Nonempty stdin exposes the no-argument sha256sum bug deterministically.
        input="must never become an asset checksum\n",
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("with_archives", [False, True])
def test_asset_collection_isolated_from_tracked_release_files(tmp_path, with_archives):
    repo = tmp_path / "repo"
    config = repo / "release"
    config.mkdir(parents=True)
    (config / "publish-artifacts.toml").write_text("tracked configuration\n")
    (config / "do-not-upload.zip").write_bytes(b"tracked example archive")
    downloads = tmp_path / "runner-temp" / "release-artifacts"
    stage = tmp_path / "runner-temp" / "release-assets"
    archives = {
        "sdk.tar.gz": b"tar archive",
        "sdk.zip": b"zip archive",
        "sdk.whl": b"wheel archive",
        "sdk with spaces.tgz": b"npm archive",
    } if with_archives else {}
    if with_archives:
        artifact = downloads / "artifact-one"
        artifact.mkdir(parents=True)
        for filename, content in archives.items():
            (artifact / filename).write_bytes(content)
        (artifact / "build-log.txt").write_text("not a release asset\n")
    else:
        assert not downloads.exists(), "model download-artifact with no matching uploads"
    env = {"RELEASE_DOWNLOAD_DIR": str(downloads), "RELEASE_ASSET_DIR": str(stage)}
    run_step("Collect archives", repo, env)
    run_step("Generate checksums", stage, env)

    assert {p.name for p in stage.iterdir()} == {*archives, "checksums.txt"}
    for filename, content in archives.items():
        assert (stage / filename).read_bytes() == content
    expected = {
        f"{hashlib.sha256(content).hexdigest()}  {filename}"
        for filename, content in archives.items()
    }
    assert set((stage / "checksums.txt").read_text().splitlines()) == expected
    assert (config / "publish-artifacts.toml").read_text() == "tracked configuration\n"
    assert (config / "do-not-upload.zip").exists()


def test_upload_and_verification_use_the_isolated_asset_directory():
    text = WORKFLOW.read_text(encoding="utf-8")
    release_job = text.split("\n  release:\n", 1)[1]
    assert "path: ${{ env.RELEASE_DOWNLOAD_DIR }}" in release_job
    assert '--asset-dir "$RELEASE_ASSET_DIR"' in release_job
    assert "working-directory: ${{ env.RELEASE_ASSET_DIR }}" in release_job
    upload = release_job.split("      - name: Create GitHub Release\n", 1)[1]
    assert "files: |\n            ${{ env.RELEASE_ASSET_DIR }}/*" in upload
    assert "release/*" not in upload


@pytest.mark.parametrize(
    ("channels", "expected"),
    [
        ("", "false"),
        ("github_release", "false"),
        ("crates_io", "true"),
        ("github_release, crates_io ", "true"),
        ("crates_io,github_release", "true"),
        ("not_crates_io", "false"),
    ],
)
def test_retry_channel_selection_skips_only_preserved_crates(tmp_path, channels, expected):
    output = tmp_path / "output"
    run_step("Read channel retry selection", tmp_path, {
        "ALREADY_PUBLISHED_CHANNELS": channels,
        "GITHUB_OUTPUT": str(output),
    })
    assert output.read_text() == f"crates_already_published={expected}\n"
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "crates_already_published: ${{ steps.retry_channels.outputs.crates_already_published }}" in text
    publish_condition = re.search(r"\n  publish:\n    if: (.+)", text).group(1)
    assert "needs.gate-and-tag.outputs.crates_already_published != 'true'" in publish_condition


def test_staging_paths_use_the_runner_temporary_directory(tmp_path):
    output = tmp_path / "environment"
    runner_temp = tmp_path / "runner temp"
    run_step("Initialize release staging paths", tmp_path, {
        "RUNNER_TEMP": str(runner_temp), "GITHUB_ENV": str(output),
    })
    assert output.read_text().splitlines() == [
        f"RELEASE_DOWNLOAD_DIR={runner_temp}/release-artifacts",
        f"RELEASE_ASSET_DIR={runner_temp}/release-assets",
    ]
