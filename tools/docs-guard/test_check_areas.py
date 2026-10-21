import json
import tempfile
import unittest
from pathlib import Path

import check_areas


class CheckAreasTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.features = Path(self._tmp.name) / "docs" / "features"
        for folder in ("done", "backlog", "dropped"):
            (self.features / folder).mkdir(parents=True)
        self.write_vocabulary(
            {
                "billing": {"description": "Billing.", "related": ["reports"]},
                "reports": {"description": "Printers.", "related": []},
            }
        )

    def write_vocabulary(self, areas, version=1):
        (self.features / "areas.json").write_text(
            json.dumps({"version": version, "areas": areas}), encoding="utf-8"
        )

    def write_doc(self, relative, areas_line=None, body="## Scope\n\nText.\n"):
        header = "# Title\n\n**Status**: Open.\n\n"
        if areas_line is not None:
            header += f"{areas_line}\n\n"
        path = self.features / relative
        path.write_text(header + body, encoding="utf-8")
        return path

    def run_guard(self, require_tags=False):
        return check_areas.run(
            self.features, self.features / "areas.json", require_tags
        )

    def test_passes_when_every_tag_is_in_the_vocabulary(self):
        self.write_doc("spec-001-a.md", "**Areas**: billing, reports")
        self.write_doc("done/spec-002-b.md", "**Areas**: billing")
        self.write_doc("backlog/001-ft-c.md", "**Areas**: reports")
        self.assertEqual(self.run_guard(require_tags=True), 0)

    def test_fails_on_an_unknown_tag(self):
        self.write_doc("spec-001-a.md", "**Areas**: billing, kitchen")
        self.assertEqual(self.run_guard(), 1)

    def test_fails_on_an_empty_line_a_stray_comma_and_a_duplicate(self):
        for line in ("**Areas**:", "**Areas**: billing,", "**Areas**: billing, menu"):
            with self.subTest(line=line):
                self.write_doc("spec-001-a.md", line)
                self.assertEqual(self.run_guard(), 1)

    def test_fails_on_two_areas_lines(self):
        self.write_doc("spec-001-a.md", "**Areas**: billing\n\n**Areas**: reports")
        self.assertEqual(self.run_guard(), 1)

    def test_untagged_document_warns_by_default_and_fails_when_required(self):
        self.write_doc("backlog/ft-a.md")
        self.assertEqual(self.run_guard(), 0)
        self.assertEqual(self.run_guard(require_tags=True), 1)

    def test_areas_line_below_the_first_heading_does_not_count(self):
        self.write_doc("spec-001-a.md", body="## Scope\n\n**Areas**: billing\n")
        self.assertEqual(self.run_guard(require_tags=True), 1)

    def test_indexes_roadmap_and_dropped_documents_are_not_checked(self):
        self.write_doc("README.md")
        self.write_doc("roadmap.md")
        self.write_doc("phase-p1-online-payment.md")
        self.write_doc("done/README.md")
        self.write_doc("dropped/spec-011-x.md")
        self.assertEqual(check_areas.tagged_documents(self.features), [])
        self.assertEqual(self.run_guard(require_tags=True), 0)

    def test_vocabulary_must_carry_a_version_and_valid_entries(self):
        bad = (
            ({"billing": {"description": ""}}, 1),
            ({"Menu": {"description": "Billing."}}, 1),
            ({"billing": {"description": "Billing.", "related": ["nope"]}}, 1),
            ({"billing": {"description": "Billing."}}, None),
        )
        for areas, version in bad:
            with self.subTest(areas=areas, version=version):
                self.write_vocabulary(areas, version)
                self.assertEqual(self.run_guard(), 1)


if __name__ == "__main__":
    unittest.main()
