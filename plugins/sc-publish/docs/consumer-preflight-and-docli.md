# Consumer publish preflight and optional sc-docli

Release Preflight (`release-preflight.yml`) is the kit's fail-closed gate before
any release dispatch. Kit-owned checks cover credentials, registry state, manifest
validation, and (when declared) Cargo packaging.

Repositories also need **repository-specific** checks — for example crates.io README
metadata, checksum contracts, or generated CLI documentation. Those must not be
hand-wired into vendored workflow YAML (sync would erase them). Instead, declare
them in the consumer input JSON and let the kit render and execute them through a
single extension point.

## Extension point (required pattern)

1. **`preflight_checks`** (optional array in consumer input JSON) — each entry:
   `id`, `description`, and `run` (shell command, usually `bash scripts/...` under
   the repository root).
2. **`docli`** (optional object) — see below.
3. **Rendered manifest** — `release/publish-preflight.toml` (third rendered file
   alongside `publish-artifacts.toml` and `publish-channel-contracts.toml`).
4. **Kit runner** — `.github/scripts/run-consumer-preflight.sh`, invoked from
   `release-preflight.yml` as step `consumer_preflight`, recorded in the deny
   summary as `consumer-preflight`.

The runner is a no-op when the manifest is missing or declares no `[[checks]]`.

## Optional sc-docli for customer-facing CLIs

[sc-docli](https://crates.io/crates/sc-docli) generates committed CLI reference
HTML from a JSON model (typically produced by a small `gen-cli-model` binary).
That documentation ships with the product; it must not drift at release time.

**Strong recommendation (not mandatory):** every consumer that ships a
**customer-facing CLI** SHOULD enable docli in consumer input JSON, pin sc-docli in
a repository-owned file such as `release/docli-pin.toml`, and implement
`scripts/generate-cli-docs.sh` to regenerate the model and HTML.

When `"docli": { "enabled": true, ... }` is set, the kit:

- Adds a `[docli]` table and a `docli-cli-html` `[[checks]]` entry to
  `release/publish-preflight.toml`.
- Installs `.github/scripts/release-preflight-docli.sh`, which runs your
  `generate_script` and fails on `git diff` / dirty paths in `drift_paths`.

**Do not run docli on every pull-request CI job** unless you have a separate reason
to do so. Regenerating CLI HTML is release-shaped work: run it in **Release
Preflight** so sprint CI stays fast and release still fails closed when docs drift.
Remove or avoid a standing PR `cli-docs` job when you adopt this pattern.

Example consumer input fragment:

```json
"docli": {
  "enabled": true,
  "generate_script": "scripts/generate-cli-docs.sh",
  "drift_paths": [
    "fixtures/cli/my-cli-model.json",
    "site/cli/"
  ],
  "description": "CLI reference HTML matches usage_message() and shipped extensions"
},
"preflight_checks": [
  {
    "id": "crates-readme-metadata",
    "description": "Published crates include README and docs.rs metadata",
    "run": "bash scripts/check-crates-publish-manifest.sh"
  }
]
```

Pin sc-docli separately (not rendered by the kit), for example:

```toml
# release/docli-pin.toml
sc_docli_version = "0.2.0"
```
