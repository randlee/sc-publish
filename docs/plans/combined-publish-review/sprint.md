---
status: in_review
branch: fix/combined-publish-review
worktree: /Users/randlee/github/sc-publish-worktrees/fix/combined-publish-review
---
# Combined publishing review corrections

Lead: aobs@sc-obs. Developer: arch-ctm@atm-dev.
Parent: PR104 at `917b5cf3daf38028a87b2053b0f352069ee7975d`.
Corrective PR: https://github.com/randlee/sc-publish/pull/106

## Accepted scope

The owner limited this follow-up to missing sc-lint requirements, npm as an
independent publication channel, and fenced JSON results from every publishing
subagent so failures retain useful diagnostics. Shared target infrastructure and
agents belong in sc-publish; consumer-specific policy belongs in consumer
configuration or extension points. Preserve existing publishing paths. No new
publication, release mutation, or version bump is part of this task.

The child contains substantive reporting fixes, not merely a documentation
receipt. The scope limit applies to this child relative to PR104. Inherited
PR101 immutable-release prerequisites remain intentionally in the stack under
Solar's lead ruling; this child neither removes them nor claims to correct their inherited permission behavior.

The sc-lint consumer/source-pin requirement is inherited from PR99
(`be170540`); this child does not change that implementation. The independent
npm publication path and organization-scope handling are inherited from the
parent stack through PR104. This child strengthens their shared reporting and
sanitization, rather than adding another publishing path.

## Implementation and disposition

| Original item | Disposition and evidence |
| --- | --- |
| FIX01 | Implemented. `plugins/sc-publish/.github/scripts/worker_result.py` sanitizes nested result diagnostics; `npm_release.py` uses the shared sanitizer. Tests cover authorization-header variants, quoted JSON, command arguments, and nested fields while retaining useful errors. Substantive child commit: `a814e7f`. |
| FIX02 | Implemented. `worker_result.py` rejects passed results with outstanding required checks; existing aggregation retains valid channel results and reports malformed results. Child commits `351d6fe` and `0d6d019`, with reporting tests. All seven channel agents inherit the shared reporting protocol. |
| FIX03 | Deferred, not fixed by this child. The default renderer remains sc-compose 1.5.0. No claim that a 1.6.1 contract was added. |
| FIX04 | Deferred, not fixed by this child. No generic preflight preparation/validation hook or opt-out was added. |
| FIX05 | Deferred, not fixed by this child. Existing-tag source/build policy was not redesigned. |
| FIX06 | Deferred, not fixed by this child. No root release concurrency mechanism was added. |
| FIX07 | Inherited PR101 behavior, not a completed child correction or proof of admission before every registry write. |
| FIX08 | Inherited PR101 behavior; not changed or claimed by this child. |
| FIX09 | Deferred, not fixed by this child. No new cross-channel draft/attestation lifecycle was implemented or live-qualified. |
| FIX10 | Deferred, not fixed by this child. No new trusted workflow-ref policy was implemented. |
| FIX11 | Validation evidence only; see below. Downstream adoption and joint approval remain separate outstanding work. |
| FIX12 | PR106 is ready for review and registered above PR104. This is not merge approval. |

Deferrals describe the agreed boundary of this correction, not proof that the
broader concerns were fixed. The existing parent stack remains subject to the
three-party compatibility review. No blanket FIX01–FIX12 completion is claimed.

## Validation receipt

Source reviewed: `dd6a03e1ff0ac6ee6cfac9f2fd6eef8344506fa6`.
This receipt correction changes documentation only relative to that source.

Clint independently reported the following at that exact source:

```text
pytest -q plugins/sc-publish/.github/scripts/tests
270 passed, 10 skipped
```

Review: https://github.com/randlee/sc-publish/pull/106#issuecomment-5755139580
The review requested correction of the prior receipt's false completion claims;
it did not approve the PR.

cobs@sc-obs reported installation (ATM message
`01M311CWKAG1JY8EGN82K1XVCR`) from that exact source into a temporary
consumer, repeat installer dry-run with no drift, and the installed suite:

```text
install.py --input install.json: exit 0
install.py --dry-run --input install.json: exit 0; assets in sync
pytest -q installed .github/scripts/tests
273 passed, 14 skipped, 43 subtests
```

This is isolated installation evidence, not a claim that PR200 already adopted
the pin or that real publishing ran. Actual consumer adoption, current CI and
same-head agreement from aobs, solar and clint remain required for closeout.
Previous receipts' stale child-head references and blanket parent-commit ledger
are superseded by this document.

## Compatibility and reporting rule

Do not block or ask about tokens unless preflight or publish fails.

All publishing subagents must return fenced JSON for success and failure,
including commands, exit status, provenance and sanitized diagnostics. Do not
hide errors or report passed with outstanding required checks. Never retain
credential values in reports. No live credential or registry operation was
performed for this documentation correction.
