---
name: prerelease
description: Publish or install a manifest-declared GitHub prerelease archive.
---

# Prerelease

Use `scripts/prerelease.py` from the repository root. This skill is GitHub-only
and never invokes Homebrew, crates.io, PyPI, winget, or Scoop. Publishing is an
external state change: use `--authorized` only with written operator approval.
It refuses protected or dirty branches, tags an explicit version (or delegates
`--bump` to the manifest tag script), waits for `prerelease-archive.yml`, then
re-checks every Release asset and checksum before printing the Release URL.

```sh
python3 .claude/skills/prerelease/scripts/prerelease.py --publish 1.5.11 --dry-run
python3 .claude/skills/prerelease/scripts/prerelease.py --bump --authorized
python3 .claude/skills/prerelease/scripts/prerelease.py --install 1.5.11
python3 .claude/skills/prerelease/scripts/prerelease.py --install --dry-run
```

Install resolves either the requested version or the latest matching GitHub
prerelease, verifies the host archive checksum, stages it under
`install_root/vX.Y.Z`, repoints the manifest's platform selector, invokes the
post-install command, and verifies the selected CLI version. Reinstalling an
already staged version skips downloading but still repairs selectors and runs
the post-install and verify commands. `--dry-run` does not call GitHub, git,
or any installer command.
