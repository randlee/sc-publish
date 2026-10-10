---
status: in-progress
branch: feature/documentation-bundle
worktree: /Users/randlee/github/sc-publish-worktrees/feature/documentation-bundle
---

# FEATURE: Optional `[documentation_bundle]` release-archive contract

## Goal

Let a consumer declare a documentation directory that is validated, staged into
every release archive, and verified in the produced archive, without any
consumer-specific logic in the kit. Tracking beads (sc-lint): lint-spx.43 (implementation and QA fixes), lint-spx.45 and lint-spx.46 (QA-1, QA-2).

## Deliverables

1. `release_documentation.py`: manifest loader/validator, `stage`, source
   `validate`, and `validate-release-archive` (tar.gz and zip), registered as
   `release_artifacts.py` subcommands (kept out of `release_artifacts.py` to
   hold its line ceiling).
2. `release_manifest.py` passes the optional table through; `release-package-config`
   includes it only when declared.
3. `release.yml` and `prerelease-archive.yml` packaging steps stage the bundle
   and validate each archive (identical logic; parity test preserved).
4. `install.py` and `publish-artifacts.toml.j2` accept and render the optional
   `documentation_bundle`; absent input renders no table.
5. Tests: `test_documentation_bundle.py` (declared and absent) plus script-list
   updates; README section "Optional documentation bundle".

## Notes

- No behavior change when the table is absent.
- Archive layout is unchanged: the bundle lands at
  `<archive-root>/<package_directory>/`.
- sc-publish has no `docs/project-plan.md`; the sprint doc is the only index.

## Acceptance criteria

- Absent table: rendered `publish-artifacts.toml` is byte-identical to the
  pre-feature render (golden test, fails if the renderer is unavailable).
- No consumer-specific names or logic in kit code.
- Declared table: validated, staged, and verified for tar.gz and zip archives,
  including through the workflow packager.
- Paths are normalized; package directory cannot collide with `bin/` or
  `bundled_paths`; symlinks, unsafe names, duplicates and non-regular archive
  members are rejected; staging never deletes an existing destination.
- Install-time validation mirrors release-time rules.

## QA-1 fixes (SP-B1..B2, SP-I1..I4, SP-M1..M4)

Addressed on this branch; status returns to `complete` after QA-2 passes.

## Archive layout option (`[project].archive_layout`)

Added on request of the first consumer (an installer shipped in an earlier
release extracts only flat archives, so a layout change would break upgrades).
`"kit"` (default, unchanged) or `"flat"`; absent renders byte-identically
(golden test). Covered: both workflow packagers, `validate-release-archive`
(tar.gz and zip, `./`-prefixed members), Homebrew `binary_paths`, the
prerelease skill, install-time validation, and package-directory collision with
a binary name in flat archives.
