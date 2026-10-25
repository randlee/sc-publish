# Getting started

Write two files, then run `install.py`. Add a script only if you opt into GitHub prereleases.

## Files you write

1. `release/sc-publish-pin.toml` — copy `release/sc-publish-pin.toml.example` and set the 40-character kit SHA.
2. `release/sc-publish-consumer-input.json` — the only release manifest. Sample below.
3. `scripts/prerelease_tag.py` — only when that JSON contains `"prerelease"`.

The kit does not choose a prerelease version or create that tag. Your script does. A real run must print a line the kit can parse:

```text
created and pushed prerelease/v0.1.1 from <commit>
```

The tag must start with `tag_prefix`. Do not pass a version to `/prerelease`.

Leave Homebrew and Scoop templates alone unless those names are in `"channels"`. The kit ships starters.

Do not edit files `install.py` copies or renders: `release/publish-artifacts.toml`, `release/publish-channel-contracts.toml`, `release/publish-preflight.toml`, and `.github/workflows/`. Change the JSON or the pin, then re-run install. A repeat `--dry-run` must exit 0.

## Install

Clone sc-publish at the pin SHA into a gitignored directory such as `.sc-publish-kit/`.

```bash
publish_python="$(python3 .sc-publish-kit/plugins/sc-publish/.github/scripts/bootstrap_sc_compose.py --venv .sc-publish-venv)"
"$publish_python" .sc-publish-kit/plugins/sc-publish/install.py \
  --input release/sc-publish-consumer-input.json .
"$publish_python" .sc-publish-kit/plugins/sc-publish/install.py \
  --dry-run --input release/sc-publish-consumer-input.json .
```

Then publish with `/cursor-publish` (`.cursor/agents/publisher.md`) or the ATM `publisher` teammate.

Before the first publish, enable immutable GitHub releases. Add the secrets in `.claude/skills/publishing/ref/channel-contracts.md` for each channel you declared. `"channels": {}` still publishes crates.io and the GitHub Release.

## Minimum JSON

`release_targets` must be non-empty. `"release_binaries": []` publishes no binary archives. Each binary name must be a Cargo `[[bin]]` name.

`/prerelease` needs `release_binaries` or Python wheels. A library with neither uses `/cursor-publish`, not `/prerelease`.

```json
{
  "schema_version": 1,
  "project": {
    "name": "example",
    "archive_prefix": "example",
    "description": "Example library",
    "homepage": "https://github.com/example/example",
    "license": "MIT",
    "workspace_toml": "Cargo.toml",
    "rust_toolchain": "1.94.1"
  },
  "release_targets": [
    {"target": "x86_64-unknown-linux-gnu", "os": "ubuntu-latest", "archive": "tar.gz"}
  ],
  "crates": [
    {
      "artifact": "example",
      "package": "example",
      "cargo_toml": "crates/example/Cargo.toml",
      "publish": true,
      "publish_order": 1,
      "wait_after_publish_seconds": 0
    }
  ],
  "release_binaries": [],
  "python_packages": [],
  "python_distributions": [],
  "npm_packages": [],
  "channels": {}
}
```

Field lists: `.claude/skills/publishing/ref/publish-kit-requirements.md`.
