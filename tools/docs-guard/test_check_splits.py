#!/usr/bin/env python3
"""Unit tests for the split link guard.

Driven against throwaway feature trees rather than this checkout, so they
assert the logic and cannot pass merely because today's backlog is consistent.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import check_splits as guard


def parent(*slices: str) -> str:
    listed = "\n".join(f"{i}. `{s}`" for i, s in enumerate(slices, start=1))
    return f"# Backlog: Big thing\n\n**Slices** (build order):\n{listed}\n\n## Build order\n"


def child(parent_name: str, n: int, m: int) -> str:
    return f"# Backlog: Part\n\n**Parent**: `{parent_name}`, slice {n} of {m}.\n"


class SplitGuardTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.features = Path(self._tmp.name) / "docs" / "features"
        for sub in ("backlog", "done"):
            (self.features / sub).mkdir(parents=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self, path: str, text: str) -> None:
        (self.features / path).write_text(text)

    def consistent_pair(self) -> None:
        self.write("backlog/ft-big.md", parent("ft-one.md", "ft-two.md"))
        self.write("backlog/ft-one.md", child("ft-big.md", 1, 2))
        self.write("backlog/ft-two.md", child("ft-big.md", 2, 2))

    def test_consistent_split_passes(self) -> None:
        self.consistent_pair()
        self.assertEqual(guard.run(self.features), [])

    def test_unsplit_backlog_passes(self) -> None:
        self.write("backlog/ft-plain.md", "# Backlog: Plain\n")
        self.assertEqual(guard.run(self.features), [])

    def test_a_promoted_slice_still_resolves_by_slug(self) -> None:
        # Promotion renames ft-one.md and rewrites the parent's list to match.
        self.write("backlog/ft-big.md", parent("spec-060-one.md", "ft-two.md"))
        self.write("spec-060-one.md", child("ft-big.md", 1, 2))
        self.write("backlog/ft-two.md", child("ft-big.md", 2, 2))
        self.assertEqual(guard.run(self.features), [])

    def test_a_priority_prefixed_parent_resolves(self) -> None:
        self.write("backlog/002-ft-big.md", parent("ft-one.md", "ft-two.md"))
        self.write("backlog/ft-one.md", child("ft-big.md", 1, 2))
        self.write("backlog/ft-two.md", child("ft-big.md", 2, 2))
        self.assertEqual(guard.run(self.features), [])

    def test_missing_slice_fails(self) -> None:
        self.consistent_pair()
        (self.features / "backlog/ft-two.md").unlink()
        self.assertTrue(any("resolves to no document" in p for p in guard.run(self.features)))

    def test_slice_without_parent_line_fails(self) -> None:
        self.consistent_pair()
        self.write("backlog/ft-two.md", "# Backlog: Part\n")
        self.assertTrue(any("no **Parent** line" in p for p in guard.run(self.features)))

    def test_wrong_position_fails(self) -> None:
        self.consistent_pair()
        self.write("backlog/ft-two.md", child("ft-big.md", 1, 2))
        self.assertTrue(any("1 of 2" in p for p in guard.run(self.features)))

    def test_orphan_parent_line_fails(self) -> None:
        self.consistent_pair()
        self.write("backlog/ft-stray.md", child("ft-big.md", 3, 3))
        self.assertTrue(any("does not list it" in p for p in guard.run(self.features)))

    def test_parent_line_naming_a_non_parent_fails(self) -> None:
        self.write("backlog/ft-plain.md", "# Backlog: Plain\n")
        self.write("backlog/ft-stray.md", child("ft-plain.md", 1, 2))
        self.assertTrue(any("no **Slices** list" in p for p in guard.run(self.features)))

    def test_promoted_parent_fails(self) -> None:
        self.write("spec-061-big.md", parent("ft-one.md", "ft-two.md"))
        self.write("backlog/ft-one.md", child("ft-big.md", 1, 2))
        self.write("backlog/ft-two.md", child("ft-big.md", 2, 2))
        self.assertTrue(any("has been promoted" in p for p in guard.run(self.features)))

    def test_single_slice_fails(self) -> None:
        self.write("backlog/ft-big.md", parent("ft-one.md"))
        self.write("backlog/ft-one.md", child("ft-big.md", 1, 1))
        self.assertTrue(any("at least two" in p for p in guard.run(self.features)))


if __name__ == "__main__":
    unittest.main()
