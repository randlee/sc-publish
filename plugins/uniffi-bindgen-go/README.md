# uniffi-bindgen-go package

This package pins `NordSecurity/uniffi-bindgen-go` at `v0.7.1+v0.31.0` and
provides the reusable Ubuntu x86_64 generation workflow used by downstream Rust
repositories.

## Consumer contract

1. A release maintainer builds the generator and runs it on `ubuntu-latest` via
   [`release-workflow.yml`](release-workflow.yml).
2. The workflow publishes the generated Go source as the
   `uniffi-bindgen-go-generated` artifact.
3. Downstream macOS and Windows jobs may download that generated-source artifact;
   this package workflow does not run platform jobs and never executes the Linux
   generator outside Ubuntu.

The package installer is for Ubuntu consumers that explicitly need the pinned
binary:

```bash
python3 plugins/uniffi-bindgen-go/install.py \
  --bin-dir .venv/bin
```

Use `--dry-run` to inspect the selected URL without downloading. The installer
fails closed when the release checksum sidecar is absent, malformed, or does
not match. The release workflow publishes the binary and its `.sha256` sidecar
together, so the package metadata does not contain a fake or stale checksum.
