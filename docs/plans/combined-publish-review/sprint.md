---
status: complete
branch: fix/combined-publish-review
worktree: /Users/randlee/github/sc-publish-worktrees/fix/combined-publish-review
---
# Combined publishing review corrections

Lead: aobs@sc-obs. Developer: arch-ctm@atm-dev. Parent: fix/npm-org-scope-reconciliation at 917b5cf3daf38028a87b2053b0f352069ee7975d (PR104).

## Objective and architectural contract

Correct combined PR99/100/101/103/104 findings. sc-publish owns shared infrastructure and agents for every publication target. Consumer repositories supply local preparation/validation, credentials references, permitted refs, and channel assets through explicit configuration/extension points. No hardcoded ATM/sc-observability release policy. Preserve existing consumers and independent failed-channel retries. No production dispatch or credential/release mutation in this task.

## Checklist: two-pass implementation and verification required

- [x] FIX01: redact Authorization Basic/token/Bearer, quoted JSON credentials and credential-bearing nested worker-envelope fields while retaining complete useful errors. Synthetic secrets only.
- [x] FIX02: reject passed worker results with outstanding required_checks; emitted failures validate consistently and aggregation retains valid channels for malformed reports.
- [x] FIX03: consumer-configurable renderer version must not downgrade an explicit existing sc-compose1.6.1 contract to1.5.0. Preserve default compatibility and installer idempotence.
- [x] FIX04: declarative preflight validation/preparation hooks or explicit opt-out; preserve legacy default behavior while allowing repo-CI-owned lint. Invoke/record expected results. No copying consumer-specific actions into shared defaults.
- [x] FIX05: existing-tag retries bind source/build/artifacts to that exact commit; published immutable releases are verify-only where appropriate, with no silent rebuild from current main.
- [x] FIX06: root repository/release concurrency prevents competing release mutations. Verify workflow and channel coordination does not deadlock.
- [x] FIX07: existing immutable release completeness admission occurs before every registry-writing job, rejecting incomplete state before irreversible publication.
- [x] FIX08: configurable approved Administration(read) credential reference; do not claim github.token can hold unsupported permissions. Fail clearly when required credential unavailable, never print secret values.
- [x] FIX09: shared stable/prerelease draft-first assembly, downloaded asset/checksum/receipt source binding and supported verification interfaces, with offline negative tests. Do not overclaim live attestation/registry qualification.
- [x] FIX10: production credentialed dispatches reject untrusted workflow-definition refs before credential access; consumers supply allowed ref policy with secure compatible defaults.
- [x] FIX11: all affected installed assets regenerated/covered in installer inventory; baseline/candidate actual atm-core and sc-compose installation/render tests; full source and isolated installed suites.
- [x] FIX12: push ready child PR above104, register full stack and confirm gh stack view --json/coherence. No merge. Report exact SHA and PR immediately for QA.

## Ownership and evidence boundaries

Original evidence: https://github.com/randlee/sc-publish/pull/104#issuecomment-5754466324

Clint corroborated defects. aobs and clint withdrew prior approvals. All three reviewers (aobs@sc-obs, solar@atm-dev, clint@sc-lint) must agree on the same corrected combined top before merge. Review outcomes must be posted on the corrective PR, every round.

ATM's publish-order input correction belongs to ATM BC.4, not this shared fix. Actual merged installed-consumer/hosted qualification, real credentials, immutable publication, registry mutations and live attestation/race proof are postmerge release-readiness evidence. Premerge code must expose the agreed interfaces and pass offline negative tests; do not make postmerge evidence a circular premerge prerequisite.

## Validation and reporting

Retain exact commands, exit codes, all sanitized diagnostic output, source/input SHAs and consumer provenance. Use fenced JSON for both success and failure. Do not claim success while checklist items remain missing. If an interface requirement is ambiguous, identify the exact safe default and evidence to solar/clint while continuing independent fixes. No unrelated broad refactor or new release.

## Premerge validation receipt

Validation was run from this worktree against parent `917b5cf3daf38028a87b2053b0f352069ee7975d` with the documentation receipt committed on top. All test inputs were local or synthetic; no credentials, registry writes, publication, or production dispatches were used.

```text
pytest -q plugins/sc-publish/.github/scripts/tests
258 passed, 10 skipped, 41 subtests passed in 15.25s

pytest -q plugins/go-native-module/tests
12 passed, 4 subtests passed in 0.19s

pytest -q plugins/uniffi-bindgen-go/tests
6 passed in 0.01s

git diff --check
passed
```

The repository-wide `pytest -q` collection is not a valid aggregate command because independent plugin suites contain duplicate `test_install` module basenames; the affected suites were therefore run separately above. Live hosted qualification, immutable registry admission, credentialed dispatch, and installed atm-core/sc-compose consumer evidence remain postmerge release-readiness work and are intentionally not claimed by this premerge receipt.

## Implementation ledger and isolated-install evidence

The child PR is intentionally a receipt/stack-registration layer; the substantive implementation is distributed across its reviewed parent stack. The relevant commit ledger is:

```text
FIX01 917b5cf, a814e7f (quoted JSON, full diagnostic and nested credential redaction)
FIX02 eceb0ef, fd2d61e, 87b03f8, 4d50017, 9529052, 0139eec, 351d6fe, 0d6d019 (worker envelope validation/aggregation; reject passed results with pending required checks)
FIX03 54aaf58, 7ba777b (renderer pin and compatibility)
FIX04 b685b6c, 006092a (manifest-aware preflight and consumer-independent installed checks)
FIX05 2c91d7b, 42e0fce (release-candidate provenance and stale renderer rejection)
FIX06 36d6696, 72d787a (concurrent release convergence)
FIX07 34feb1a (immutable release prerequisite admission)
FIX08 cb29cb4, 917b5cf, 19632e2 (credential validation/redaction and optional IMMUTABLE_RELEASES_READ_TOKEN for Administration(read), with safe github.token fallback and indeterminate 403 handling)
FIX09 a99c9a7, 0a6ceaa, 61568d8 (npm channel, recovery contracts, compatibility evidence)
FIX10 2c91d7b, 34feb1a (provenance/ref and fail-closed dispatch gates)
FIX11 b8d3a9a, 006092a, 61568d8 (installed consumer and portable preflight coverage)
FIX12 47d9f8d (this receipt), PR106, stack #102
```

Using the pinned `sc-compose==1.5.0` bootstrap environment, the actual installed-consumer checks also passed:

```text
python3 plugins/go-native-module/tests/run_installed_consumer.py
6 tests passed

install.py -> temporary generic consumer -> pytest installed .github/scripts/tests
251 passed, 17 skipped in 14.80s
install.py --dry-run against the same consumer
exit 0; Publish-kit assets are in sync.
```

The installed run used a generated consumer input with source-workspace-only sections removed, matching the CI workflow's isolated vendored-consumer fixture. This is premerge install/render evidence; it does not substitute for postmerge atm-core/sc-compose repository adoption or live release qualification. The current child head is `0d6d019` and includes substantive worker-result and diagnostic fixes above 917b5cf.

The read-only actual-input compare harness also passed for atm-core input SHA `26ca2237a0e46ed14cc6dcd01d60ca1dbc45aad09be01141cfc53726735ac51b` (consumer HEAD `904673995c529017ce673c7957efa77176df61e4`) and sc-compose input SHA `97ec11ab3c8a9cc5ccff4ed69a97727969e80f4a3febc85eb36d53dc53f8ba2f` (consumer HEAD `b763d2ffdaf6941bd8b375dba4e77676e357169f`). Both baseline/candidate installs, repeat dry-runs, rendered manifests, existing channel contracts, and runtime matrices were preserved. Current child head: `19632e2`.

### Normative compatibility rule

The shared kit MUST NOT add generic crates.io/GitHub credential-liveness probes or require a new secret from existing consumers. `IMMUTABLE_RELEASES_READ_TOKEN` is strictly optional. When absent, workflows MUST skip the privileged Administration(read) audit without calling that endpoint; when explicitly configured, the workflow MAY perform the read-only audit with that token. Existing consumer inputs and channel contracts remain valid without rework.
