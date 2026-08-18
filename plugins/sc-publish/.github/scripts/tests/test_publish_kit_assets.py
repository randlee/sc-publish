"""Package-native assertions for the vendored Claude publishing assets."""

from __future__ import annotations

import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
AGENTS = PACKAGE_ROOT / ".claude" / "agents"
PUBLISHING = PACKAGE_ROOT / ".claude" / "skills" / "publishing"
CURSOR = PACKAGE_ROOT / ".cursor"
CURSOR_RUNTIME = PUBLISHING / "ref" / "cursor-runtime.md"

CHANNEL_AGENTS = (
    "crates-io-publisher",
    "github-release-publisher",
    "pypi-publisher",
    "homebrew-publisher",
    "scoop-publisher",
    "winget-publisher",
)


class PublishingAssetTests(unittest.TestCase):
    def test_channel_agents_are_background_workers_at_the_current_package_version(self) -> None:
        for name in CHANNEL_AGENTS:
            text = (AGENTS / f"{name}.md").read_text(encoding="utf-8")
            self.assertIn("version: 0.1.0", text)
            self.assertIn("spawn_policy: background_agent_required", text)
            self.assertIn("publisher-channel-protocol.md", text)

    def test_channel_agents_reference_cursor_runtime_profile(self) -> None:
        for name in CHANNEL_AGENTS:
            text = (AGENTS / f"{name}.md").read_text(encoding="utf-8")
            self.assertIn("cursor-runtime.md", text)

    def test_publisher_is_the_only_named_orchestrator(self) -> None:
        text = (AGENTS / "publisher.md").read_text(encoding="utf-8")
        self.assertIn("version: 1.7.0", text)
        self.assertIn("spawn_policy: named_teammate_required", text)
        self.assertIn("Runtime selection", text)
        self.assertIn(".cursor/agents/publisher.md", text)
        self.assertIn("cursor-runtime.md", text)
        self.assertIn("role-specific background workers", text)
        self.assertIn("Never ask whether a token exists", text)

    def test_cursor_runtime_profile_exists_and_mandates_inline_execution(self) -> None:
        self.assertTrue(CURSOR_RUNTIME.is_file())
        text = CURSOR_RUNTIME.read_text(encoding="utf-8")
        self.assertIn("Inline", text)
        self.assertIn("never spawn Task subagents", text)

    def test_cursor_publisher_agent_is_inline_only(self) -> None:
        text = (CURSOR / "agents" / "publisher.md").read_text(encoding="utf-8")
        self.assertIn("Cursor runtime", text)
        self.assertIn("cursor-runtime.md", text)
        self.assertIn("Forbidden:", text)
        self.assertIn("Task subagents", text)
        self.assertIn("inline_step", text)

    def test_cursor_publish_skill_and_command_exist(self) -> None:
        skill = (CURSOR / "skills" / "cursor-publish" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("name: cursor-publish", skill)
        self.assertIn("cursor-runtime.md", skill)
        self.assertIn("no nested task subagents", skill.lower())

        command = (CURSOR / "commands" / "cursor-publish.md").read_text(encoding="utf-8")
        self.assertIn("/cursor-publish", command)
        self.assertIn("cursor-runtime.md", command)
        self.assertIn("Inline only", command)
        self.assertIn("Task subagents", command)

    def test_task_templates_require_a_recipient(self) -> None:
        for name in ("preflight.xml.j2", "publish.xml.j2"):
            text = (PUBLISHING / name).read_text(encoding="utf-8")
            self.assertIn("version: 0.1.0", text)
            self.assertIn("- recipient", text)
            self.assertIn("<recipient>{{ recipient }}</recipient>", text)


if __name__ == "__main__":
    unittest.main()
