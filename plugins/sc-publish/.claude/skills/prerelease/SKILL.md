---
name: prerelease
description: Publish or install a manifest-declared GitHub prerelease archive.
---

# Prerelease

Use `scripts/prerelease.py` from the repository root. This skill is GitHub-only
and never invokes Homebrew, crates.io, PyPI, winget, or Scoop. Publishing is an
external state change: use `--authorized` only with written operator approval.

```sh
python3 .claude/skills/prerelease/scripts/prerelease.py --publish 1.5.11 --dry-run
python3 .claude/skills/prerelease/scripts/prerelease.py --install 1.5.11
```

Install verifies the Release archive checksum, stages a matched pair, invokes
the manifest post-install command, and verifies the selected CLI version.
