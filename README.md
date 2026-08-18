# sc-publish

`sc-publish` is the single source of truth for the shared publishing package.
The package lives at [`plugins/sc-publish`](plugins/sc-publish).

Install it into a consumer repository with a complete, caller-owned JSON input
document. The document declares the entire release surface: project metadata,
targets, crate order, binaries, Python distributions, and every publication
channel. The installer never infers a publish surface or enables a channel.

```bash
publish_python="$(python3 plugins/sc-publish/.github/scripts/bootstrap_sc_compose.py --venv /tmp/sc-publish-1.4.1)"
# Create and review a complete repository-specific install.json first.
"$publish_python" plugins/sc-publish/install.py --input install.json /path/to/consumer
"$publish_python" plugins/sc-publish/install.py --dry-run --input install.json /path/to/consumer
```

Use `--dry-run` to print drift without changing the consumer; it returns `1`
when an install would change files. With no arguments the installer prints
help. The installer deliberately has no source-discovery mode: release targets,
Python packaging details, and external publish channels are reviewed policy,
not values that can be inferred safely from a repository checkout.

The installer copies the shared `.claude`, `.github`, and release assets, then
uses the pinned `sc-compose` Python bindings to write consumer-specific release manifests.
The non-CI examples in [`.integration/manifest_examples.py`](.integration/manifest_examples.py)
render generic inputs and compare parsed TOML values. CI provisions the pinned
`sc-compose` wheel before running them.
