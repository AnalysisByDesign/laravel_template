#!/usr/bin/env python3
"""Unit tests for the machine-local-state guard.

The guard's own job is to notice when something that must stay local has become
tracked. These tests drive its three predicates against throwaway git
repositories rather than against this one, so they assert the logic rather than
the current state of the checkout, and cannot pass merely because today's
repository happens to be correct.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import check_local_state as guard


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


class LocalStateGuardTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)

        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "guard@test.local")
        git(self.repo, "config", "user.name", "Guard Test")

        (self.repo / ".specify").mkdir()

        # The guard reads module-level REPO_ROOT, so point it at the fixture
        # and restore it afterwards rather than leaving it pointed at a
        # deleted temporary directory.
        self._real_root = guard.REPO_ROOT
        guard.REPO_ROOT = self.repo

    def tearDown(self) -> None:
        guard.REPO_ROOT = self._real_root
        self._tmp.cleanup()

    def write_pointer(self) -> None:
        (self.repo / ".specify/feature.json").write_text(
            json.dumps({"feature_directory": "specs/001-thing"}) + "\n"
        )

    def write_example(self) -> None:
        (self.repo / ".specify/feature.json.example").write_text(
            json.dumps({"feature_directory": "specs/NNN-short-name"}, indent=2) + "\n"
        )

    def ignore_pointer(self) -> None:
        (self.repo / ".gitignore").write_text(".specify/feature.json\n")

    def commit_all(self) -> None:
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "fixture")

    def test_passes_when_ignored_untracked_and_exemplified(self) -> None:
        self.write_pointer()
        self.write_example()
        self.ignore_pointer()
        self.commit_all()

        self.assertEqual(guard.main(), 0)

    def test_fails_when_the_pointer_is_tracked(self) -> None:
        # The case that actually happened: committed, so every checkout shares
        # one slot and a stale pointer fails silently.
        self.write_pointer()
        self.write_example()
        self.commit_all()

        self.assertEqual(guard.main(), 1)
        self.assertIn(".specify/feature.json", guard.tracked_files())

    def test_fails_when_untracked_but_not_ignored(self) -> None:
        # Untracked and unignored is the state that lets the next `git add -A`
        # put it straight back.
        self.write_pointer()
        self.write_example()
        self.commit_all()
        git(self.repo, "rm", "--cached", "-q", ".specify/feature.json")

        self.assertFalse(guard.is_ignored(".specify/feature.json"))
        self.assertEqual(guard.main(), 1)

    def test_fails_when_the_example_is_missing(self) -> None:
        # A fresh clone has no pointer at all, so the example is the only
        # thing showing its shape.
        self.write_pointer()
        self.ignore_pointer()
        self.commit_all()

        self.assertEqual(guard.main(), 1)

    def test_fails_when_the_example_is_not_valid_json(self) -> None:
        self.write_pointer()
        (self.repo / ".specify/feature.json.example").write_text("{ not json\n")
        self.ignore_pointer()
        self.commit_all()

        self.assertEqual(guard.main(), 1)


if __name__ == "__main__":
    unittest.main()
