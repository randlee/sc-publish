# sc-publish

`sc-publish` is the single source of truth for the shared publishing package.
The package lives at [`plugins/sc-publish`](plugins/sc-publish).

Install it into a consumer repository with fixed JSON arrays for the published
artifacts:

```bash
python3 plugins/sc-publish/install.py /path/to/consumer \
  --crates '["example-core", "example-cli"]' \
  --wheels '["example"]' \
  --binaries '["example"]'
```

Use `--dry-run` to print drift without changing the consumer.  With no
arguments the installer prints help; `--example-json` provides a minimal
source-discovered starting point for the current repository.

The installer copies the shared `.claude`, `.github`, and release assets, then
uses `sc-compose render` to write the consumer-specific release manifests.
The non-CI examples in [`.integration/manifest_examples.py`](.integration/manifest_examples.py)
render fixed `sc-compose` and `atm-core` inputs and compare parsed TOML values.
