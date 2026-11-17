# Publication continuity

Add `"publication_continuity": {}` to the consumer install JSON and rerun
the installer. Declaration enables a blocking, read-only check in both Release
Preflight and Release. Omitting the field preserves existing behavior, with no
additional service access. There is no runtime bypass once declared.

The check selects the greatest published, non-draft, stable semantic release
below the requested version. A retry excludes the current version. It reads
that release's actual GitHub assets, its historical artifact manifest, and
public registry version lookups for the historical crate, PyPI and npm names.
It also inventories published Go module tags, including submodule tags that
predate the previous GitHub release. Formula, bucket and Winget publications
are read through their declared GitHub repositories. Registry errors, incomplete
listings and unavailable historical metadata fail closed. A first GitHub
release has no prior assets; any historical Go module tags still count.

The baseline is never reconstructed from the new manifest. In particular,
removing a package from the new manifest cannot remove it from the comparison.
A historical GitHub release without an artifact manifest is indeterminate and
is refused; the check does not guess an external publication surface from
arbitrary source files.

Asset identifiers have the form `asset:<filename>` with the release version
replaced by `{version}`, for example
`asset:example_{version}_x86_64-unknown-linux-gnu.tar.gz`. The new manifest must
still produce that artifact family for the declared target. Platform wheels
must use explicit platform declarations when continuity is enabled; a runner
label alone does not establish which wheel platform will be published.
Other identifiers are `crate:<package>`, `pypi:<normalized-name>`,
`npm:<package>`, `go:<module>`, `homebrew:<tap>/<formula-path>`,
`scoop:<bucket>/<manifest-path>` and `winget:<identifier>`.

## User-approved retirement

Each dropped item needs its own reviewed manifest record:

```json
"publication_continuity": {
  "deprecations": [{
    "identifier": "crate:retired-library",
    "reason": "The user approved retiring the obsolete library",
    "approved_by": "release-owner",
    "approval_ref": "https://github.com/example/project/issues/42"
  }]
}
```

The approval reference must identify the issue or PR containing user approval;
the fields are documentary evidence for human review, not an automatic grant
of approval. Empty, malformed, duplicate, never-published or still-retained
entries are refused. No ledger or additional release asset is created.

## Ordering and extension

Release checks the manifest at its resolved release commit before the first
tag push. Preflight records the same check in its final blocking summary and
per-channel results. Both paths call `publication_continuity.py`; its pure
comparison accepts an injected previous inventory, and `publication_inventory`
owns read-only service access. Tests use controlled listings and never publish.
`DEFAULT_ENABLED` is the single default-policy switch; consumer declaration is
the default in this version.
