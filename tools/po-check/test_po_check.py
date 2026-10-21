import json
import tempfile
import unittest
from pathlib import Path

import context
import verdict as verdicts


class ContextTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        for folder in ("docs/features/backlog", "docs/features/done", "docs/work-packages",
                       "docs/epics", ".specify/memory", "specs/041-blog"):
            (self.root / folder).mkdir(parents=True)
        self.write("docs/features/backlog/ft-loyalty-points.md",
                   "# Backlog: Loyalty\n\n**Status**: Unnumbered backlog item.\n\n**Areas**: promotions\n\n## Why\n\nText.\n")
        self.write("docs/features/backlog/001-ft-allergens.md", "# Backlog: Allergens\n\n**Status**: Open.\n\n## Why\n")
        self.write("docs/features/spec-041-blog.md",
                   "# Spec-041: Blog\n\n**Status**: In flight.\n\n**Areas**: marketing-site\n\n## Scope\n")
        self.write("docs/features/areas.json", json.dumps({"version": 1, "areas": {"promotions": {"description": "Offers."}}}))
        self.write("docs/work-packages/README.md",
                   "# Packages\n\n| Band | Package | Owner | Gate | Where it stands |\n| --- | --- | --- | --- | --- |\n"
                   "| 000 | `wp-000-x.md` | Operator | none | Open. |\n|  | `wp-y.md` | Claude | `wp-000-x.md` | Proposed. |\n")
        self.write("docs/features/roadmap.md",
                   "# Roadmap\n\n### Standing placement rules\n\n- Rule one.\n\n## Build order\n\n- Spec-000\n\n### Changelog: old\n\nnoise\n\n## Deferred\n\nlater\n")
        self.write("docs/epics/epic-main-tier.md",
                   "# Epic\n\n| Item | Kind |\n| --- | --- |\n| `docs/features/backlog/ft-loyalty-points.md` | Feature |\n")
        self.write(".specify/memory/constitution.md",
                   "# Constitution\n\n## Core Principles\n\n### I. Isolation\n\nEvery query is scoped.\n\n### II. Tests\n\nTests first.\n\n## Governance\n\nRules.\n")

    def write(self, relative, text):
        (self.root / relative).write_text(text, encoding="utf-8")

    def test_finds_a_feature_by_slug_filename_or_prefixed_name(self):
        for name in ("loyalty-points", "ft-loyalty-points", "ft-loyalty-points.md",
                     "docs/features/backlog/ft-loyalty-points.md", "allergens", "001-ft-allergens.md"):
            with self.subTest(name):
                self.assertTrue(context.find_feature(self.root, name).exists())

    def test_unknown_feature_is_refused(self):
        with self.assertRaises(context.ContextError):
            context.find_feature(self.root, "nothing-here")

    def test_bundle_carries_each_input_and_nothing_stray(self):
        bundle = context.build(self.root, "loyalty-points")
        self.assertEqual(bundle["feature"]["status"], "**Status**: Unnumbered backlog item.")
        self.assertEqual([r["package"] for r in bundle["batches"]], ["wp-000-x.md", "wp-y.md"])
        self.assertEqual(bundle["batches"][1]["batch"], None)
        self.assertEqual(bundle["roadmap"]["Standing placement rules"], "- Rule one.")
        self.assertEqual(bundle["roadmap"]["Build order"], "- Spec-000")
        self.assertNotIn("noise", json.dumps(bundle["roadmap"]))
        self.assertEqual(bundle["in_flight_specs"][0]["spec_kit_directory"], "specs/041-blog")
        self.assertEqual(bundle["in_flight_specs"][0]["areas"], "marketing-site")
        self.assertEqual([e["epic"] for e in bundle["epics"]], ["docs/epics/epic-main-tier.md"])
        self.assertEqual([p["title"] for p in bundle["principles"]], ["I. Isolation", "II. Tests"])
        self.assertNotIn("Governance", json.dumps(bundle["principles"]))


class VerdictTest(unittest.TestCase):
    def good(self, **overrides):
        v = {"verdict": "challenge", "reason": "Displaces Gate A.", "displaces": ["wp-000-x.md"],
             "principle_conflicts": [], "spec_exists": False}
        v.update(overrides)
        return v

    def test_a_sound_verdict_passes(self):
        self.assertEqual(verdicts.check(self.good()), [])
        self.assertEqual(verdicts.check(self.good(verdict="promote", displaces=[])), [])
        self.assertEqual(verdicts.check(self.good(verdict="defer", recommended_batch="002")), [])

    def test_broken_verdicts_are_named(self):
        cases = [
            self.good(verdict="maybe"),
            self.good(reason="  "),
            self.good(displaces="wp-000-x.md"),
            self.good(principle_conflicts=[""]),
            self.good(spec_exists="no"),
            self.good(verdict="defer"),
            self.good(verdict="promote"),
            {k: v for k, v in self.good().items() if k != "spec_exists"},
        ]
        for case in cases:
            with self.subTest(case):
                self.assertTrue(verdicts.check(case))

    def test_override_needs_a_reason_and_appends_with_a_header_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "po-overrides.md"
            with self.assertRaises(ValueError):
                verdicts.override_entry(self.good(), "ft-x.md", "   ", "2026-09-30")
            with self.assertRaises(ValueError):
                verdicts.override_entry(self.good(), "ft-x.md", "because", "30/09/2026")
            for i in range(2):
                verdicts.append_override(log, verdicts.override_entry(self.good(), "ft-x.md", f"reason {i}", "2026-09-30"))
            text = log.read_text()
            self.assertEqual(text.count("# Product owner overrides"), 1)
            self.assertEqual(text.count("## 2026-09-30: ft-x.md"), 2)
            self.assertIn("**Operator's reason to proceed**: reason 1", text)

    def test_cli_refuses_an_override_for_a_promote_verdict(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "v.json"
            path.write_text(json.dumps(self.good(verdict="promote", displaces=[])))
            code = verdicts.main(["override", str(path), "--feature", "ft-x.md", "--reason", "r",
                                  "--date", "2026-09-30", "--log", str(Path(tmp) / "log.md")])
            self.assertEqual(code, 1)
            self.assertFalse((Path(tmp) / "log.md").exists())


if __name__ == "__main__":
    unittest.main()
