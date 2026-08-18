# sc-publish

Shared, manifest-driven release/publish kit used across repositories. This
repository is the single source of truth for the package: change shared assets
here, then vendor them into consumers. Do not make consumer-local edits to
overlay-owned files and copy them back as an alternate source.

The canonical, consumer-root overlay is under
[`docs/publish-kit/overlay`](docs/publish-kit/overlay). Every overlay file is
shared unchanged between consumers except `release/publish-artifacts.toml`,
which each consumer supplies for its own crates, wheels, binaries, and enabled
destinations. A generic starting point is at
[`docs/publish-kit/examples/release/publish-artifacts.toml`](docs/publish-kit/examples/release/publish-artifacts.toml).

Use [`docs/publish-kit/sync-overlay.sh`](docs/publish-kit/sync-overlay.sh) to
vendor the overlay into a consumer repository. The consumer manifest is the
only intentionally repository-specific file and remains consumer-owned:

```bash
# Review every changed shared file as a unified diff; exits 1 when drift exists.
docs/publish-kit/sync-overlay.sh --dry-run /path/to/consumer

# Copy only changed overlay files; does not delete consumer-owned files.
docs/publish-kit/sync-overlay.sh /path/to/consumer
```
