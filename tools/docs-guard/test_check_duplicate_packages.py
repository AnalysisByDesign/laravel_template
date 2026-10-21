"""Unit tests for the duplicate-document guard.

The first test is the one that matters: it is the squash-merge pair the guard exists for,
which a leading-number strip does not report. If this test ever passes with the canonicalisation reverted, the
guard has gone back to being decorative.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import check_duplicate_packages as guard


class TestCanonical(unittest.TestCase):
    def test_strips_a_batch_number_from_inside_the_name(self):
        # The squash-merge pair. These must compare equal or the guard is useless.
        self.assertEqual(
            guard.canonical("wp-002-user-export-follow-ups.md"),
            guard.canonical("wp-user-export-follow-ups.md"),
        )

    def test_strips_a_sequence_letter_with_the_batch_number(self):
        # Sequence letters (wp-000a-, wp-000b-) belong to the batch number.
        self.assertEqual(
            guard.canonical("wp-000b-example-session.md"),
            guard.canonical("wp-example-session.md"),
        )

    def test_the_old_leading_strip_would_not_have_matched_that_pair(self):
        # Documents why the fix was needed: under the current convention
        # the number is never at the front, so a leading strip is a
        # no-op and the two names stay different.
        import re

        old = re.compile(r"^\d{3}-")
        self.assertNotEqual(
            old.sub("", "wp-002-user-export-follow-ups.md"),
            old.sub("", "wp-user-export-follow-ups.md"),
        )

    def test_strips_a_priority_prefix_from_the_front(self):
        self.assertEqual(
            guard.canonical("001-ft-allergen-declarations.md"), "ft-allergen-declarations.md"
        )

    def test_keeps_a_spec_number(self):
        # spec-011 was deliberately reused for a different feature, so merging
        # spec numbers would report a duplicate that is not one.
        self.assertNotEqual(
            guard.canonical("spec-011-receipt-templates.md"),
            guard.canonical("spec-012-user-export.md"),
        )


class TestDuplicateDetection(unittest.TestCase):
    def _repo(self, files: dict[str, list[str]]):
        root = Path(self.tmp.name)
        for folder, names in files.items():
            directory = root / folder
            directory.mkdir(parents=True, exist_ok=True)
            for name in names:
                (directory / name).write_text("x")
        return root

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_reports_the_same_slug_under_two_names(self):
        root = self._repo(
            {
                "docs/work-packages": ["wp-002-friction.md", "README.md"],
                "docs/work-packages/done": ["wp-friction.md", "README.md"],
            }
        )
        with mock.patch.object(guard, "REPO_ROOT", root):
            found = guard.duplicates_in(["docs/work-packages", "docs/work-packages/done"])
        self.assertEqual(list(found), ["wp-friction.md"])

    def test_readme_in_every_directory_is_not_a_duplicate(self):
        # Without the exclusion this fires on every run, and a check that always
        # cries wolf is worse than none.
        root = self._repo(
            {
                "docs/work-packages": ["README.md", "wp-a.md"],
                "docs/work-packages/done": ["README.md", "wp-b.md"],
            }
        )
        with mock.patch.object(guard, "REPO_ROOT", root):
            found = guard.duplicates_in(["docs/work-packages", "docs/work-packages/done"])
        self.assertEqual(found, {})

    def test_a_clean_folder_set_reports_nothing(self):
        root = self._repo(
            {
                "docs/work-packages": ["wp-000-merge-skill.md", "wp-release-checklist.md"],
                "docs/work-packages/done": ["wp-pricing-strategy.md"],
            }
        )
        with mock.patch.object(guard, "REPO_ROOT", root):
            found = guard.duplicates_in(["docs/work-packages", "docs/work-packages/done"])
        self.assertEqual(found, {})

    def test_a_missing_folder_is_not_an_error(self):
        root = self._repo({"docs/work-packages": ["wp-a.md"]})
        with mock.patch.object(guard, "REPO_ROOT", root):
            found = guard.duplicates_in(["docs/work-packages", "docs/work-packages/done"])
        self.assertEqual(found, {})


class TestAgainstTheRealRepository(unittest.TestCase):
    def test_the_repository_is_currently_clean(self):
        self.assertEqual(guard.main(), 0)


if __name__ == "__main__":
    unittest.main()
