# sc-publish

`sc-publish` is the single source of truth for the shared publishing package.
The package lives at [`plugins/sc-publish`](plugins/sc-publish).

Install it into a consumer repository with a complete, caller-owned JSON input
document.  The document explicitly declares crate ordering and which channels
are active; the installer never infers a publish surface or enables channels.

```bash
publish_python="$(python3 plugins/sc-publish/.github/scripts/bootstrap_sc_compose.py --venv /tmp/sc-publish-1.4.1)"
"$publish_python" plugins/sc-publish/install.py --write-example install.json /path/to/consumer
# Review install.json and explicitly confirm the discovered release surface.
# Crates enable crates.io; wheels enable PyPI; binaries enable GitHub Release,
# Homebrew, Scoop, and Winget. Unsupported channels remain false.
"$publish_python" plugins/sc-publish/install.py --input install.json /path/to/consumer
"$publish_python" plugins/sc-publish/install.py --dry-run --input install.json /path/to/consumer
```

Use `--dry-run` to print drift without changing the consumer; it returns `1`
when an install would change files. With no arguments the installer prints
help. `--example-json` prints the same source-discovered starter document to
stdout; `--write-example` is usually clearer for a real installation.

The installer copies the shared `.claude`, `.github`, and release assets, then
uses the pinned `sc-compose` Python bindings to write consumer-specific release manifests.
The non-CI examples in [`.integration/manifest_examples.py`](.integration/manifest_examples.py)
render generic inputs and compare parsed TOML values. CI provisions the pinned
`sc-compose` wheel before running them.
