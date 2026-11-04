# ADR: Consumer-declared preflight checks

Status: proposed for review, 2026-11-04. Scope: extend the existing
`publish-preflight.toml` runner; no mandatory consumer checks.

## Authority and context

Fenix relayed Rand's statements from 2026-09-23/24 (original session IDs not
retained): “sc-publish should be a set a agents and workflows with zero mandetory things that cause publish to fail” and “if you want custom checks run your own fucking script”. Fenix also relayed “you realize this is the 2nd redesign of this already” and “no more changing things on local repo, that is prohibited”. The earlier descriptions of a freeze at cbb9ce08 and a five-consumer condition were Fenix's paraphrases, not verbatim quotations; their original transcripts are unavailable.

On 2026-11-03 local (2026-11-04 UTC), Rand instructed the sc-compose lead:
“You can have comp make the update now on sc-publish now and have fenix@atm-dev + quality-mgr review it when he is done.” On 2026-11-04 Fenix relayed the following three parts verbatim: “any sc-publish change, it MUST be repo-agnostic and an extension point.  I ONLY allow changes that make sc-publish si” + “... simpler and easier more extensible” + “... for customers”. The lead authorized opening a PR for review, not merging. Interpretation of the earlier freeze remains for Rand to confirm.

## Numbered requirements

1. A consumer may declare named shell commands, whether required, and an optional evidence path in its own preflight manifest. Missing declarations preserve existing behavior; existing checks remain required by default.
2. Run declared checks from the repository root, preserve their stderr unmodified, report each exit code, and include required failures in the existing workflow verdict. Optional failures are reported without blocking. Invalid configuration fails closed.
3. When an evidence path is declared, expose it and the checked-out candidate SHA to the command. Evidence verification is consumer-owned: a file's existence alone is not verification. A consumer verifying a matrix must compare the candidate SHA and hashes of the exact published artifacts; preflight must not rerun the matrix.
4. A CLI consumer can declare a docli freshness command that dumps its neutral model, generates a reference in temporary storage and byte-compares it with its committed reference. The kit adds no built-in docli gate or repository-specific logic.
5. Provide deterministic tests for no-check compatibility, required/optional outcomes, diagnostics, manifest rendering, and the declared evidence path and candidate identity.

## Design choices and open decisions

- **Execution:** reuse `publish-preflight.toml` and its existing runner rather than introduce another configuration or workflow. Commands use the existing shell semantics.
- **Evidence:** options are (A) a generic file-existence check, (B) a fixed evidence schema, or (C) a consumer command with evidence path and candidate SHA. Recommend C: only the consumer knows its artifacts and evidence schema; mere existence cannot establish provenance. The exact matrix artifact handoff and verifier remain consumer decisions.
- **docli:** a kit built-in was considered; the current ruling selects a declared consumer script and documented recipe. Existing legacy docli configuration remains supported, but this change adds no new docli-specific runner.
- **Freeze:** the earlier rule's original text and release condition are unavailable; the lead has authorized a PR for review based on the newer instruction. Final interpretation and merge authority remain with Rand.

## Compliance for customers

The extended manifest fields reuse a familiar single declaration, so consumers need no workflow fork and can express more checks; all commands and evidence semantics remain repository-agnostic. Per-check exit reporting and nonblocking optional checks simplify diagnosis and allow more consumer policies without imposing defaults. The candidate SHA and evidence-path context simplify a consumer-owned verifier and enable more evidence formats without kit-specific policy. The docli recipe lets CLI owners reproduce a freshness check without requiring it of every customer. Documentation and deterministic tests explain and protect these same consumer capabilities; they add no gate by themselves.
