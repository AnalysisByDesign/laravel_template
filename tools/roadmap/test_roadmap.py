"""Unit tests for the roadmap generator.

    python3 -m unittest discover tools/roadmap

Two kinds of test here, and the split is deliberate. Most are pure functions
checked against fixtures, because the parsing rules are where this goes wrong
quietly. The last group runs against the real repository, because a generator
that only works on fixtures is a generator nobody notices has stopped reading
the folder it was pointed at.
"""

from __future__ import annotations

import re
import subprocess
import unittest

import shutil
from unittest import mock

import diagram
import model
import render


class TestCanonical(unittest.TestCase):
    def test_strips_a_work_package_batch_number(self):
        # The number is reused and is stripped on archiving, so a reference to
        # the numbered name has to match the archived file.
        self.assertEqual(model.canonical("wp-000-rollup.md"), "wp-rollup.md")
        self.assertEqual(model.canonical("wp-rollup.md"), "wp-rollup.md")

    def test_strips_a_backlog_priority_prefix(self):
        self.assertEqual(
            model.canonical("001-ft-allergen-declarations.md"), "ft-allergen-declarations.md"
        )

    def test_keeps_a_spec_number(self):
        # A spec number is identity, not scheduling. Stripping it would merge
        # two different specs into one row.
        self.assertEqual(model.canonical("spec-048-go-live.md"), "spec-048-go-live.md")


class TestParseHeader(unittest.TestCase):
    def test_reads_the_ordinary_shape(self):
        title, fields = model.parse_header(
            "# Feature: thing\n\n**Status**: Open, not started.\n\n**Areas**: menu, printing\n\n## Why\n"
        )
        self.assertEqual(title, "Feature: thing")
        self.assertEqual(fields["status"], "Open, not started.")
        self.assertEqual(fields["areas"], "menu, printing")

    def test_reads_a_colon_inside_the_bold(self):
        # `**Status (2026-09-29 assessment): SHIPPED**, by spec-024` occurs in
        # the backlog and is not the ordinary shape.
        _, fields = model.parse_header(
            "# X\n\n**Status (2026-09-29 assessment): SHIPPED**, by spec-024 T088.\n"
        )
        self.assertEqual(fields["status"], "SHIPPED, by spec-024 T088.")

    def test_keeps_the_first_value_for_a_label(self):
        _, fields = model.parse_header("# X\n\n**Status**: first\n\n**Status**: second\n")
        self.assertEqual(fields["status"], "first")

    def test_stops_at_the_first_section(self):
        _, fields = model.parse_header("# X\n\n**Status**: a\n\n## Body\n\n**Owner**: b\n")
        self.assertNotIn("owner", fields)


class TestSummaries(unittest.TestCase):
    def test_skips_a_boilerplate_opening_clause(self):
        self.assertEqual(
            model.first_sentence("Unnumbered backlog item. Captured 2026-09-07 from a session."),
            "Captured 2026-09-07 from a session.",
        )

    def test_keeps_an_informative_first_sentence(self):
        self.assertEqual(
            model.first_sentence("Open, not started. More detail follows."), "Open, not started."
        )

    def test_keeps_the_only_sentence_even_when_boilerplate(self):
        self.assertEqual(model.first_sentence("Backlog."), "Backlog.")

    def test_truncates_on_a_word_boundary(self):
        out = model.first_sentence("word " * 60, limit=40)
        self.assertTrue(out.endswith("..."))
        self.assertLessEqual(len(out), 40)


class TestGate(unittest.TestCase):
    def test_none_is_an_absence_however_the_sentence_continues(self):
        self.assertEqual(model.real_gate("none. The policy is decided."), "")
        self.assertEqual(model.real_gate("None on the design."), "")
        self.assertEqual(model.real_gate(""), "")

    def test_a_real_gate_survives(self):
        self.assertEqual(model.real_gate("Alan's written permission"), "Alan's written permission")

    def test_does_not_swallow_a_gate_that_merely_starts_with_the_letters(self):
        self.assertEqual(model.real_gate("nonetheless blocked"), "nonetheless blocked")


class TestTitles(unittest.TestCase):
    def test_strips_the_kind_prefix_whatever_its_case(self):
        for given, wanted in (
            ("Feature: claim code expiry", "claim code expiry"),
            ("FEATURE: cuisine prompts", "cuisine prompts"),
            ("Backlog: powered-by attribution", "powered-by attribution"),
            ("Work Package: merge skill", "merge skill"),
            ("Spec-048: Go-live pricing gate", "Go-live pricing gate"),
        ):
            self.assertEqual(model.strip_kind_prefix(given), wanted)

    def test_leaves_an_unprefixed_title_alone(self):
        self.assertEqual(model.strip_kind_prefix("Hero scene library"), "Hero scene library")


class TestClassify(unittest.TestCase):
    def test_the_folder_wins_where_it_says_anything(self):
        # An archived document whose prose still reads "open" is done, because
        # the folder is maintained by the archive skills and the prose is not.
        self.assertEqual(model.classify("Open, not started.", model.DONE), model.DONE)

    def test_waiting_beats_done_when_both_words_appear(self):
        self.assertEqual(
            model.classify("Blocked until the migration is complete.", None), model.WAITING
        )

    def test_falls_back_to_open(self):
        self.assertEqual(model.classify("Something with no keywords in it.", None), model.OPEN)


class TestCells(unittest.TestCase):
    def test_escapes_a_pipe(self):
        self.assertEqual(render.cell("a | b"), r"a \| b")

    def test_collapses_newlines(self):
        self.assertEqual(render.cell("a\nb  c"), "a b c")

    def test_never_returns_empty(self):
        # An empty cell closes the table in some renderers.
        self.assertEqual(render.cell(""), " ")


class TestSliceRendering(unittest.TestCase):
    """A split feature renders as its parent with ordered slices beneath.

    Fixtures rather than real documents, because nothing in the repository has
    been split yet. The fixtures use the exact `**Parent**` line that
    `tpl-split-feature` writes and `tools/docs-guard/check_splits.py` enforces,
    so this is a test of the shared contract rather than of a shape invented
    here.
    """

    def _split_family(self):
        parent = model.Item(key="ft-parent.md", kind="feature", title="Parent feature")
        children = []
        # Deliberately out of order, so the sort is doing the work.
        for key, title, line in (
            ("ft-b.md", "Second slice", "`ft-parent.md`, slice 2 of 3."),
            ("ft-a.md", "First slice", "`ft-parent.md`, slice 1 of 3."),
            ("ft-c.md", "Third slice", "`ft-parent.md`, slice 3 of 3."),
        ):
            name, position = model.parse_parent(line)
            children.append(
                model.Item(key=key, kind="feature", title=title, parent=name, slice_of=position)
            )
        items = {i.key: i for i in [parent, *children]}
        model._attach_slices(items)
        return items, parent

    def test_the_parent_line_is_read_in_the_shape_the_split_skill_writes(self):
        self.assertEqual(
            model.parse_parent("`ft-the-parent.md`, slice 1 of 2."), ("ft-the-parent.md", (1, 2))
        )

    def test_a_bare_filename_still_links(self):
        self.assertEqual(model.parse_parent("ft-plain.md"), ("ft-plain.md", None))

    def test_no_parent_line_is_not_a_slice(self):
        self.assertEqual(model.parse_parent(""), (None, None))

    def test_slices_hang_off_the_parent_in_build_order(self):
        _, parent = self._split_family()
        self.assertEqual([s.title for s in parent.slices], ["First slice", "Second slice", "Third slice"])

    def test_the_lane_shows_the_parent_once_with_its_slices_indented(self):
        items, _ = self._split_family()
        lines = render._lane("Features", list(items.values()))
        rows = [line for line in lines if line.startswith("|") and "---" not in line][1:]
        self.assertEqual(len(rows), 4, "parent plus three slices, each once")
        self.assertTrue(rows[0].startswith("| Parent feature"))
        self.assertIn("&nbsp;", rows[1])
        self.assertIn("(1 of 3)", rows[1])
        self.assertIn("(3 of 3)", rows[3])

    def test_a_slice_is_never_also_a_top_level_row(self):
        items, _ = self._split_family()
        lines = render._lane("Features", list(items.values()))
        top_level = [line for line in lines if line.startswith("| First slice")]
        self.assertEqual(top_level, [])


class TestEpicOrdering(unittest.TestCase):
    """Items appear in the order the epic declares, not alphabetically."""

    EPIC = """# Epic: thing

**Status**: Proposed.

## Sequence

This section is authoritative on ordering.

1. `ft-zebra.md`
2. `ft-apple.md`

## Items

| Item | State |
| --- | --- |
| `ft-apple.md` | open |
| `ft-zebra.md` | open |
| `ft-mango.md` | open |

## Related, homed elsewhere

- `ft-elsewhere.md`
"""

    def test_the_sequence_section_wins_over_the_items_table(self):
        # Scanning in document order picks the sequence up without naming it,
        # because it sits above the items table in every epic that has one.
        members, _ = model._epic_members(self.EPIC)
        self.assertEqual(members, ["ft-zebra.md", "ft-apple.md", "ft-mango.md"])

    def test_alphabetical_order_would_have_been_wrong(self):
        # Sorting would have put the epic's last item first.
        members, _ = model._epic_members(self.EPIC)
        self.assertNotEqual(members, sorted(members))

    def test_a_related_item_is_not_homed_here(self):
        members, _ = model._epic_members(self.EPIC)
        self.assertNotIn("ft-elsewhere.md", members)

    def test_a_repeated_reference_appears_once_at_its_first_position(self):
        members, _ = model._epic_members(self.EPIC)
        self.assertEqual(members.count("ft-apple.md"), 1)


class TestFilenameColumn(unittest.TestCase):
    def test_an_item_prints_its_real_filename(self):
        # The name on disk, not the canonical one, since the point is to open it.
        item = model.Item(
            key="wp-rollup.md",
            kind="work-package",
            title="Rollup",
            path=model.REPO / "docs/work-packages/wp-000-rollup.md",
        )
        self.assertEqual(item.filename, "wp-000-rollup.md")

    def test_an_issue_prints_its_number(self):
        self.assertEqual(model.Item(key="#108", kind="issue", title="x").filename, "#108")

    def test_every_lane_row_carries_the_file_column(self):
        item = model.Item(key="ft-a.md", kind="feature", title="A", path=None)
        rows = [l for l in render._lane("Features", [item]) if l.startswith("| ")]
        self.assertIn("| Item | File | State | Where it stands |", rows[0])
        self.assertIn("`ft-a.md`", rows[-1])


def _issue(number: int, *labels: str) -> model.Item:
    return model.Item(key="#%d" % number, kind="issue", title="Issue %d" % number, areas=list(labels))


LABELS = {"wp-001": "epic-gate-b-second.md", "epic: polish": "epic-polish.md"}


@mock.patch.dict(model.ISSUE_LABEL_EPIC, LABELS, clear=True)
class TestIssueEpics(unittest.TestCase):
    def test_a_batch_label_places_the_issue_in_its_gate(self):
        self.assertEqual(model.issue_epic(_issue(1, "wp-001")), "epic-gate-b-second.md")
        self.assertEqual(model.issue_epic(_issue(2, "bug", "epic: polish")), "epic-polish.md")
        self.assertIsNone(model.issue_epic(_issue(3, "bug")))

    def test_a_label_wins_over_a_mention_so_an_issue_is_listed_once(self):
        gate_a = model.Epic("epic-gate-a-first.md", "Gate A", 1, "", "", "", issues=[326])
        gate_b = model.Epic("epic-gate-b-second.md", "Gate B", 3, "", "", "", issues=[326])
        roadmap = model.Roadmap(items={}, epics=[gate_a, gate_b], issues=[_issue(326, "wp-001"), _issue(9)])
        self.assertEqual([i.key for i in roadmap.issues_for(gate_a)], [])
        self.assertEqual([i.key for i in roadmap.issues_for(gate_b)], ["#326"])

    def test_an_unlabelled_issue_falls_back_to_the_epics_that_mention_it(self):
        epic = model.Epic("epic-x.md", "X", 5, "", "", "", issues=[9])
        roadmap = model.Roadmap(items={}, epics=[epic], issues=[_issue(9)])
        self.assertEqual([i.key for i in roadmap.issues_for(epic)], ["#9"])


class TestDiagram(unittest.TestCase):
    def test_bar_is_always_the_full_width(self):
        for counts in ({model.DONE: 1, model.IN_PROGRESS: 0, model.OPEN: 2, model.WAITING: 7},
                       {model.DONE: 0, model.IN_PROGRESS: 0, model.OPEN: 0, model.WAITING: 0}):
            visible = re.sub(r"<[^>]+>", "", diagram._bar(counts))
            self.assertEqual(len(visible), diagram.BAR_WIDTH)

    def test_text_is_quoted_safely_and_shortened(self):
        self.assertNotIn('"', diagram._text('a "quoted" title'))
        self.assertLessEqual(len(diagram._text("x" * 100)), diagram.TITLE_LIMIT)


class TestAgainstTheRealRepository(unittest.TestCase):
    """Cheap checks that the generator is still pointed at a folder with things in it."""

    @classmethod
    def setUpClass(cls):
        cls.roadmap = model.load(include_issues=False)

    def test_every_gate_epic_is_recognised_as_a_gate(self):
        on_disk = sorted(p.name for p in model.EPICS.glob("epic-gate-*.md"))
        gates = sorted(e.key for e in self.roadmap.epics if e.is_gate)
        self.assertEqual(gates, on_disk)

    def test_every_epic_homes_something_or_is_an_empty_shelf(self):
        # Not an assertion that each has members: an add-on epic may record a
        # gap rather than an item. The check is that the parse found any at all,
        # once there are epics homing documents to find.
        if not any(e.members for e in self.roadmap.epics) and not self.roadmap.items:
            self.skipTest("no feature documents or work packages yet")
        if self.roadmap.epics and self.roadmap.items:
            self.assertTrue(any(e.members for e in self.roadmap.epics) or self.roadmap.unhomed())

    def test_most_archived_documents_carry_their_merge(self):
        # Skipped on a shallow clone, where there is no history to read and the
        # assertion would be testing the checkout rather than the generator.
        # CI checks out full history for this job so it does run there.
        if subprocess.run(
            ["git", "rev-parse", "--is-shallow-repository"],
            capture_output=True, text=True, cwd=model.REPO,
        ).stdout.strip() == "true":
            self.skipTest("shallow clone: no history for attach_merges to read")
        done = self.roadmap.completed()
        if len(done) < 5:
            self.skipTest("too few archived documents for a meaningful ratio")
        with_pr = [i for i in done if i.merged_pr]
        self.assertGreater(len(with_pr), len(done) * 0.7)

    def test_the_documents_render_as_well_formed_tables(self):
        for text in (render.upcoming(self.roadmap), render.completed(self.roadmap)):
            self.assertTrue(text.startswith("# Roadmap"))
            self.assertIn(render.BANNER, text)
            # Every row in a table block has the header's column count. A row
            # one cell short silently shifts every value left of it.
            #
            # Count separators, not pipe characters: a status line quoting
            # `a | b` is escaped to `\|` by `cell`, which is correct Markdown and
            # not a column. A naive count read those rows as ragged.
            def columns(line: str) -> int:
                return len(re.findall(r"(?<!\\)\|", line))

            expected = None
            for line in text.splitlines():
                if not line.startswith("|"):
                    expected = None
                    continue
                if expected is None:
                    expected = columns(line)
                self.assertEqual(
                    columns(line), expected, "ragged table row: %s" % line[:90]
                )

    def test_no_em_or_en_dashes_reach_the_output(self):
        # House prose style. The generator quotes existing documents, so
        # this is the check that it does not carry an old one through.
        for text in (render.upcoming(self.roadmap), render.completed(self.roadmap)):
            self.assertNotIn("—", text)
            self.assertNotIn("–", text)


if __name__ == "__main__":
    unittest.main()


class TestDiagramsAgainstTheRealRepository(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.roadmap = model.load(include_issues=False)
        cls.sources = {"overview": diagram.overview(cls.roadmap), "gates": diagram.gates(cls.roadmap)}

    def test_package_names_never_collide(self):
        # PlantUML merges packages that share a name and alias, which puts one
        # gate's features inside another unless every lane carries its own alias.
        for name, source in self.sources.items():
            aliases = re.findall(r'^\s*package "[^"]*" as (\S+)', source, re.MULTILINE)
            self.assertEqual(len(aliases), len(set(aliases)), name)
            unaliased = re.findall(r'^\s*package "[^"]*"\s*\{', source, re.MULTILINE)
            self.assertLessEqual(len(unaliased), 1, name)

    def test_no_label_starts_with_a_hash(self):
        # A leading "#" is a numbered list in creole: "#227" rendered as "1. 227".
        for name, source in self.sources.items():
            self.assertNotRegex(source, r'rectangle "#', name)

    def test_every_gate_epic_has_a_package(self):
        gates = [e for e in self.roadmap.epics if e.is_gate]
        for epic in gates:
            self.assertIn(diagram._alias("G", epic.key), self.sources["gates"])

    @unittest.skipUnless(shutil.which("plantuml"), "plantuml is not installed")
    def test_plantuml_accepts_both_sources(self):
        for name, source in self.sources.items():
            result = subprocess.run(["plantuml", "-syntax"], input=source, capture_output=True, text=True)
            self.assertFalse(result.stdout.startswith("ERROR"), "%s: %s" % (name, result.stdout))
