---
name: github-release-publisher
version: 0.1.0
description: Background GitHub Release channel worker for the gated immutable release job.
metadata:
  spawn_policy: background_agent_required
---

# GitHub Release Publisher

> **Runtime:** ATM background worker. **Cursor:** inline only — see
> `ref/cursor-runtime.md`.

Read `publisher-channel-protocol.md`, then the `github_release` contract and
`.claude/skills/publishing/ref/channel-contracts.md`. You own only the root
GitHub Release channel and never create or move tags manually.
