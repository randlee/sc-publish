# Cursor runtime profile

sc-publish supports two publisher runtimes. The manifest, workflows, and channel
contracts are identical; only **how channel work is executed** differs.

| Runtime | Entry | Channel execution |
|---------|-------|-------------------|
| **ATM/rmux** | Named teammate `publisher` (`.claude/agents/publisher.md`) | Fan out **background channel workers** per `.claude/agents/<channel>.md` |
| **Cursor** | `.cursor/agents/publisher.md` + `/cursor-publish` | **Inline** in one foreground session — read channel agents as playbooks; **never spawn Task subagents** |

## Cursor constraints

1. **No nested Tasks** — Cursor cannot run `publisher` as a Task agent that
   spawns `crates-io-publisher`, `github-release-publisher`, etc. as background
   Tasks. Multitask Mode must not delegate publisher to a background worker.
2. **Foreground publisher** — one session owns preflight → root release →
   post-release verification.
3. **Channel agents remain authoritative** — in Cursor, read each
   `.claude/agents/<channel>-publisher.md` and
   `publisher-channel-protocol.md`, then perform the same checks and workflow
   dispatches yourself (shell + `gh` + `python3`).
4. **Completion JSON** — use `inline_step` and `dispatch_run_id` instead of
   ATM `worker.child_task_id` / `result_ref`.

## Inline channel map

For each manifest-declared channel, the Cursor publisher:

| Channel agent | Inline responsibility |
|---------------|---------------------|
| `crates-io-publisher` | `public-registry-inquiry-plan` + crates.io API verify; monitor root `publish-crates` or `crates-io` workflow job; partial retry via manifest idempotent plan |
| `pypi-publisher` | PyPI/TestPyPI inquiry URLs from helper; monitor `pypi-publish.yml` when enabled |
| `github-release-publisher` | Never manual tag push; monitor root `release.yml` asset jobs; verify `gh release view` |
| `homebrew-publisher` | Monitor tap update workflow / job; verify formula version in declared tap repo |
| `scoop-publisher` | Monitor scoop workflow; verify manifest-declared bucket |
| `winget-publisher` | Monitor winget workflow; expect bootstrap waiver until package exists in winget-pkgs |

Derive the active channel set from:

```bash
python3 scripts/release_artifacts.py preflight-secret-plan \
  --manifest release/publish-artifacts.toml
```

Use `channel-dispatch-plan` only for post-release channels after the immutable
GitHub Release exists.

## Shared rules (both runtimes)

- Never inspect, request, or print publish tokens.
- Release Preflight workflow is authoritative before root publish.
- Never manually create, move, or delete release tags from local git.
- Retry only failed channels; preserve passed results on the same tag/ref.

## Cursor entrypoints

- Command: `.cursor/commands/cursor-publish.md`
- Agent: `.cursor/agents/publisher.md`
- Skill: `.cursor/skills/cursor-publish/SKILL.md`

When vendoring via `install.py`, these copy into the consumer repository
alongside `.claude` and `.github` assets.
