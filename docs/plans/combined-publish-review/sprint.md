---
status: in-progress
branch: fix/combined-publish-review
worktree: /Users/randlee/github/sc-publish-worktrees/fix/combined-publish-review
---
# Combined publishing review corrections

Lead: aobs@sc-obs. Developer: arch-ctm@atm-dev. Parent: fix/npm-org-scope-reconciliation at 917b5cf3daf38028a87b2053b0f352069ee7975d (PR104).

## Objective and architectural contract

Correct combined PR99/100/101/103/104 findings. sc-publish owns shared infrastructure and agents for every publication target. Consumer repositories supply local preparation/validation, credentials references, permitted refs, and channel assets through explicit configuration/extension points. No hardcoded ATM/sc-observability release policy. Preserve existing consumers and independent failed-channel retries. No production dispatch or credential/release mutation in this task.

## Checklist: two-pass implementation and verification required

- [ ] FIX01: redact Authorization Basic/token/Bearer, quoted JSON credentials and credential-bearing nested worker-envelope fields while retaining complete useful errors. Synthetic secrets only.
- [ ] FIX02: reject passed worker results with outstanding required_checks; emitted failures validate consistently and aggregation retains valid channels for malformed reports.
- [ ] FIX03: consumer-configurable renderer version must not downgrade an explicit existing sc-compose1.6.1 contract to1.5.0. Preserve default compatibility and installer idempotence.
- [ ] FIX04: declarative preflight validation/preparation hooks or explicit opt-out; preserve legacy default behavior while allowing repo-CI-owned lint. Invoke/record expected results. No copying consumer-specific actions into shared defaults.
- [ ] FIX05: existing-tag retries bind source/build/artifacts to that exact commit; published immutable releases are verify-only where appropriate, with no silent rebuild from current main.
- [ ] FIX06: root repository/release concurrency prevents competing release mutations. Verify workflow and channel coordination does not deadlock.
- [ ] FIX07: existing immutable release completeness admission occurs before every registry-writing job, rejecting incomplete state before irreversible publication.
- [ ] FIX08: configurable approved Administration(read) credential reference; do not claim github.token can hold unsupported permissions. Fail clearly when required credential unavailable, never print secret values.
- [ ] FIX09: shared stable/prerelease draft-first assembly, downloaded asset/checksum/receipt source binding and supported verification interfaces, with offline negative tests. Do not overclaim live attestation/registry qualification.
- [ ] FIX10: production credentialed dispatches reject untrusted workflow-definition refs before credential access; consumers supply allowed ref policy with secure compatible defaults.
- [ ] FIX11: all affected installed assets regenerated/covered in installer inventory; baseline/candidate actual atm-core and sc-compose installation/render tests; full source and isolated installed suites.
- [ ] FIX12: push ready child PR above104, register full stack and confirm gh stack view --json/coherence. No merge. Report exact SHA and PR immediately for QA.

## Ownership and evidence boundaries

Original evidence: https://github.com/randlee/sc-publish/pull/104#issuecomment-5754466324

Clint corroborated defects. aobs and clint withdrew prior approvals. All three reviewers (aobs@sc-obs, solar@atm-dev, clint@sc-lint) must agree on the same corrected combined top before merge. Review outcomes must be posted on the corrective PR, every round.

ATM's publish-order input correction belongs to ATM BC.4, not this shared fix. Actual merged installed-consumer/hosted qualification, real credentials, immutable publication, registry mutations and live attestation/race proof are postmerge release-readiness evidence. Premerge code must expose the agreed interfaces and pass offline negative tests; do not make postmerge evidence a circular premerge prerequisite.

## Validation and reporting

Retain exact commands, exit codes, all sanitized diagnostic output, source/input SHAs and consumer provenance. Use fenced JSON for both success and failure. Do not claim success while checklist items remain missing. If an interface requirement is ambiguous, identify the exact safe default and evidence to solar/clint while continuing independent fixes. No unrelated broad refactor or new release.
