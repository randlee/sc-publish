# go-native-module peer package

`go-native-module` is an optional `sc-publish` peer package for a Go module
that ships a target-specific static Rust archive. It is independent of the
core publish-kit and of `uniffi-bindgen-go`.

## Immutable install contract

Pin this package by immutable release tag or merge SHA. Its `manifest.toml`
declares the compatible package version. Install using a consumer-owned JSON
file:

```json
{
  "schema_version": 1,
  "package_version": "0.1.0",
  "source": "bindings/sc-sha-go",
  "cargo_package": "sc-sha-go",
  "artifact_prefix": "sc-sha-go"
}
```

```bash
python3 <pinned-sc-publish>/plugins/go-native-module/install.py \
  --input release/go-native-module-install.json .
```

The installer uses the same pinned `sc-compose` Python-binding rendering
contract as the core package. It installs byte-identical helper/tests and
renders only `release/go-native-module.toml`. `--dry-run` reports drift without
writing; a repeat install is byte-identical.

The input deliberately contains only consumer facts. The helper validates and
derives the Go module from `<source>/go.mod`, the generated package and native
targets from `<source>/native/targets.toml`, and runner/archive selection from
the core `release/publish-artifacts.toml`.

## Helper commands

```bash
python3 .github/scripts/go_native_module.py target-matrix \
  --manifest release/publish-artifacts.toml \
  --config release/go-native-module.toml

python3 .github/scripts/go_native_module.py stage \
  --config release/go-native-module.toml \
  --target x86_64-unknown-linux-gnu \
  --native-library path/to/libsc_sha_go.a \
  --output dist/sc-sha-go-linux-amd64 \
  --version 1.6.0

python3 .github/scripts/go_native_module.py verify-version-lockstep \
  --config release/go-native-module.toml \
  --workspace-toml Cargo.toml
```

`target-matrix` writes exactly one GitHub Actions matrix JSON object on
success and no stdout on failure. `stage` validates all inputs before atomically
creating a self-contained module with exactly `go.mod`, `README.md`, `go/`,
`testdata/`, `native/targets.toml`, one matching archive, and `VERSION`.
