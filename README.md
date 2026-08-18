# sc-publish

`sc-publish` is the single source of truth for the shared publishing package.
The package lives at [`plugins/sc-publish`](plugins/sc-publish).

Install it into a consumer repository with a complete, caller-owned JSON input
document.  The document explicitly declares crate ordering and which channels
are active; the installer never infers a publish surface or enables channels.

```bash
python3 plugins/sc-publish/install.py --example-json /path/to/consumer > install.json
# Review install.json and explicitly confirm the discovered release surface.
# Crates enable crates.io; wheels enable PyPI; binaries enable GitHub Release,
# Homebrew, Scoop, and Winget. Unsupported channels remain false.
python3 plugins/sc-publish/install.py --input install.json /path/to/consumer
```

Use `--dry-run` to print drift without changing the consumer.  With no
arguments the installer prints help; `--example-json` provides a source-
discovered starting point only and cannot install anything.

The installer copies the shared `.claude`, `.github`, and release assets, then
uses `sc-compose render` to write the consumer-specific release manifests.
The non-CI examples in [`.integration/manifest_examples.py`](.integration/manifest_examples.py)
render generic inputs and compare parsed TOML values. CI provisions the pinned
`sc-compose` renderer before running them.
