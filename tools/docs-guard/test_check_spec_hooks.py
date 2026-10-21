#!/usr/bin/env python3
"""Unit tests for the project spec-kit hook guard.

Driven against throwaway directories rather than this checkout, so they assert
the logic and cannot pass merely because today's extensions.yml is correct.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import check_spec_hooks as guard

GIT_ENTRY = """\
  - extension: git
    command: speckit.git.commit
    enabled: true
    optional: true
    priority: 10
    condition: null
"""

TLX_ENTRY = """\
  - extension: tlx
    command: tpl.session.name
    enabled: {enabled}
    optional: false
    priority: 20
    condition: null
"""


def extensions(after_specify: str) -> str:
    return (
        "installed:\n- git\nhooks:\n"
        "  before_specify:\n" + GIT_ENTRY.replace("commit", "feature")
        + "  after_specify:\n" + after_specify
        + "  after_clarify:\n" + GIT_ENTRY
    )


class SpecHookGuardTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        (self.repo / ".specify").mkdir()
        self._real_root = guard.REPO_ROOT
        guard.REPO_ROOT = self.repo

    def tearDown(self) -> None:
        guard.REPO_ROOT = self._real_root
        self._tmp.cleanup()

    def write(self, after_specify: str, skill: bool = True) -> None:
        (self.repo / ".specify/extensions.yml").write_text(extensions(after_specify))
        if skill:
            d = self.repo / ".claude/skills/tpl-session-name"
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text("---\nname: tpl-session-name\n---\n")

    def test_passes_when_registered_enabled_and_the_skill_exists(self) -> None:
        self.write(GIT_ENTRY + TLX_ENTRY.format(enabled="true"))
        self.assertEqual(guard.main(), 0)

    def test_fails_when_an_upgrade_dropped_the_entry(self) -> None:
        # The case the guard exists for: spec-kit rewrote the file with only
        # its own entries.
        self.write(GIT_ENTRY)
        self.assertEqual(guard.main(), 1)

    def test_an_entry_under_a_different_hook_does_not_count(self) -> None:
        self.write(GIT_ENTRY)
        text = (self.repo / ".specify/extensions.yml").read_text()
        (self.repo / ".specify/extensions.yml").write_text(
            text + TLX_ENTRY.format(enabled="true")
        )
        self.assertEqual(
            [e["command"] for e in guard.hook_entries(text, "after_specify")],
            ["speckit.git.commit"],
        )
        self.assertEqual(guard.main(), 1)

    def test_fails_when_disabled(self) -> None:
        self.write(GIT_ENTRY + TLX_ENTRY.format(enabled="false"))
        self.assertEqual(guard.main(), 1)

    def test_fails_when_the_skill_is_missing(self) -> None:
        self.write(GIT_ENTRY + TLX_ENTRY.format(enabled="true"), skill=False)
        self.assertEqual(guard.main(), 1)


if __name__ == "__main__":
    unittest.main()
