"""Tests for init_app.py and check_placeholders.py, against a throwaway repo."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_placeholders  # noqa: E402
import init_app  # noqa: E402
from placeholders import MARKER  # noqa: E402

ANSWERS = {
    "app_name": "Acme Orders",
    "app_slug": "acme",
    "app_description": "Orders for Acme.",
    "skill_prefix": "acm",
    "github_owner": "acme-co",
    "github_repo": "acme-orders",
    "port_suffix": "123",
    "local_domain": "acme.test",
    "production_domain": "orders.acme.example",
    "generate_passwords": True,
}

ENV_EXAMPLE = """APP_NAME="{{APP_NAME}}"
APP_KEY=
APP_PORT=8{{PORT_SUFFIX}}
DB_DATABASE={{APP_SLUG}}
DB_USERNAME={{APP_SLUG}}_rw
DB_PASSWORD=
DB_RO_USERNAME={{APP_SLUG}}_ro
DB_RO_PASSWORD=
DB_ROOT_PASSWORD=
"""

README = """<!-- TEMPLATE-ONLY:START -->
# The template

Run the init skill. {{APP_SLUG}} is filled in.
<!-- TEMPLATE-ONLY:END -->

# {{APP_NAME}}

Blade stays {{ $name }} and Actions stays ${{ github.sha }}.
"""


class InitTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.write("laravel/.env.example", ENV_EXAMPLE)
        self.write("README.md", README)
        self.write(".claude/skills/{{SKILL_PREFIX}}-merge/SKILL.md", '---\nname: "{{SKILL_PREFIX}}-merge"\n---\nSee /{{SKILL_PREFIX}}-sync-local.\n')
        self.write("tools/init/notes.md", "{{APP_SLUG}} stays: init tooling is excluded.\n")
        self.write("docs/logo.png", "\0binary {{APP_SLUG}}")
        self.write("laravel/composer.lock", json.dumps({"packages": [
            {"name": "laravel/tinker", "version": "v3.0.0"},
            {"name": "laravel/framework", "version": "v13.38.0"},
        ]}))
        self.git("init", "-q")
        self.git("add", "-A")
        self.commit("template")
        self.git("remote", "add", "origin", "git@github.com:acme-co/acme-orders.git")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write(self, rel: str, text: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def commit(self, message: str) -> None:
        # The machine's global hooks (gitleaks) are not under test here.
        self.git("-c", "user.email=t@example.com", "-c", "user.name=t",
                 "-c", "core.hooksPath=/dev/null", "commit", "-qm", message)

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.root, capture_output=True, text=True, check=True).stdout

    def test_detect_reads_the_github_remote(self) -> None:
        facts = init_app.detect(self.root)
        self.assertEqual((facts["github_owner"], facts["github_repo"]), ("acme-co", "acme-orders"))
        self.assertEqual(facts["suggested"]["app_slug"], "acmeorders")
        self.assertEqual(facts["laravel_version"], "13.38.0")
        self.assertFalse(facts["initialised"])

    def test_apply_substitutes_renames_and_strips_template_blocks(self) -> None:
        init_app.apply(dict(ANSWERS), self.root)

        readme = (self.root / "README.md").read_text()
        self.assertNotIn("TEMPLATE-ONLY", readme)
        self.assertNotIn("The template", readme)
        self.assertIn("# Acme Orders", readme)
        self.assertIn("{{ $name }}", readme)
        self.assertIn("${{ github.sha }}", readme)

        skill = self.root / ".claude/skills/acm-merge/SKILL.md"
        self.assertTrue(skill.exists())
        self.assertIn('name: "acm-merge"', skill.read_text())
        self.assertIn("/acm-sync-local", skill.read_text())
        self.assertFalse((self.root / ".claude/skills/{{SKILL_PREFIX}}-merge").exists())

        self.assertIn("{{APP_SLUG}}", (self.root / "tools/init/notes.md").read_text())
        self.assertIn("{{APP_SLUG}}", (self.root / "docs/logo.png").read_text())

    def test_apply_writes_env_with_key_and_generated_passwords(self) -> None:
        init_app.apply(dict(ANSWERS), self.root)
        env = (self.root / "laravel/.env").read_text()
        values = dict(line.split("=", 1) for line in env.splitlines() if "=" in line)

        self.assertTrue(values["APP_KEY"].startswith("base64:"))
        self.assertEqual(values["DB_DATABASE"], "acme")
        self.assertEqual(values["DB_USERNAME"], "acme_rw")
        self.assertEqual(values["DB_RO_USERNAME"], "acme_ro")
        self.assertEqual(values["APP_PORT"], "8123")
        passwords = [values[k] for k in init_app.PASSWORD_KEYS]
        self.assertTrue(all(len(p) == 32 and p.isalnum() for p in passwords))
        self.assertEqual(len(set(passwords)), 3)

        example = (self.root / "laravel/.env.example").read_text()
        self.assertIn("DB_PASSWORD=\n", example)
        for secret in passwords:
            self.assertNotIn(secret, (self.root / init_app.SUMMARY).read_text())
            self.assertNotIn(secret, (self.root / MARKER).read_text())

    def test_without_generation_the_passwords_stay_blank(self) -> None:
        init_app.apply({**ANSWERS, "generate_passwords": False}, self.root)
        env = (self.root / "laravel/.env").read_text()
        self.assertIn("DB_PASSWORD=\n", env)
        self.assertIn("Not generated", (self.root / init_app.SUMMARY).read_text())

    def test_an_existing_env_is_moved_aside(self) -> None:
        self.write("laravel/.env", "OLD=1\n")
        self.git("update-index", "--skip-worktree", "laravel/.env.example")  # keep the tree clean
        (self.root / ".gitignore").write_text("laravel/.env\nlaravel/.env.*\n!laravel/.env.example\n")
        self.git("add", ".gitignore")
        self.commit("ignore")
        init_app.apply(dict(ANSWERS), self.root)
        aside = list((self.root / "laravel").glob(".env.pre-init-*"))
        self.assertEqual(len(aside), 1)
        self.assertEqual(aside[0].read_text(), "OLD=1\n")

    def test_runs_once_only(self) -> None:
        init_app.apply(dict(ANSWERS), self.root)
        self.git("add", "-A")
        self.commit("init")
        with self.assertRaisesRegex(init_app.InitError, "already initialised"):
            init_app.apply(dict(ANSWERS), self.root)

    def test_refuses_a_dirty_tree(self) -> None:
        self.write("stray.txt", "x")
        with self.assertRaisesRegex(init_app.InitError, "uncommitted"):
            init_app.apply(dict(ANSWERS), self.root)

    def test_bad_answers_are_all_named_and_nothing_is_written(self) -> None:
        bad = {**ANSWERS, "app_slug": "Acme-Orders", "port_suffix": "42", "app_name": 'Say "hi"'}
        with self.assertRaises(init_app.InitError) as caught:
            init_app.apply(bad, self.root)
        for key in ("app_slug", "port_suffix", "app_name"):
            self.assertIn(key, str(caught.exception))
        self.assertFalse((self.root / MARKER).exists())

    def test_an_unknown_placeholder_aborts_before_writing(self) -> None:
        self.write("docs/x.md", "{{NOT_A_REAL_ONE}}\n")
        self.git("add", "-A")
        self.commit("x")
        with self.assertRaisesRegex(init_app.InitError, "NOT_A_REAL_ONE"):
            init_app.apply(dict(ANSWERS), self.root)
        self.assertIn("{{APP_NAME}}", (self.root / "README.md").read_text())
        self.assertFalse((self.root / "laravel/.env").exists())

    def test_dry_run_writes_nothing(self) -> None:
        out = init_app.apply(dict(ANSWERS), self.root, dry_run=True)
        self.assertIn("Dry run", out)
        self.assertFalse((self.root / MARKER).exists())
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_guard_passes_a_template_and_fails_leftovers_after_init(self) -> None:
        self.assertEqual(check_placeholders.main(self.root), 0)
        init_app.apply(dict(ANSWERS), self.root)
        self.git("add", "-A")
        self.commit("init")
        self.assertEqual(check_placeholders.main(self.root), 0)
        self.write("docs/late.md", "{{APP_NAME}}\n")
        self.git("add", "docs/late.md")
        self.assertEqual(check_placeholders.main(self.root), 1)

    def test_marker_records_values_but_no_secrets(self) -> None:
        init_app.apply(dict(ANSWERS), self.root)
        marker = json.loads((self.root / MARKER).read_text())
        self.assertEqual(marker["values"]["APP_SLUG"], "acme")
        self.assertTrue(marker["passwords_generated"])
        self.assertNotIn("APP_KEY", json.dumps(marker))

    def test_records_the_laravel_version_from_composer_lock(self) -> None:
        init_app.apply(dict(ANSWERS), self.root)
        marker = json.loads((self.root / MARKER).read_text())
        self.assertEqual(marker["laravel_version"], "13.38.0")
        self.assertIn("carrying Laravel 13.38.0", (self.root / init_app.SUMMARY).read_text())

    def test_a_missing_lock_records_unknown(self) -> None:
        (self.root / "laravel/composer.lock").unlink()
        self.assertEqual(init_app.laravel_version(self.root), "unknown")


class SampleTest(unittest.TestCase):
    def test_every_placeholder_has_a_sample_value(self) -> None:
        import placeholders

        self.assertEqual(set(placeholders.SAMPLE), set(placeholders.PLACEHOLDERS))

    def test_sample_rendering_leaves_no_placeholder_in_the_env_example(self) -> None:
        import placeholders

        example = (placeholders.REPO_ROOT / "laravel/.env.example").read_text()
        rendered = placeholders.render_sample(example)
        self.assertEqual(placeholders.PLACEHOLDER_RE.findall(rendered), [])
        self.assertIn("APP_URL=http://localhost:8", rendered)


if __name__ == "__main__":
    unittest.main()
