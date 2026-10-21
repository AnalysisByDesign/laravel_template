"""What the template's placeholders are, and where they may appear.

Shared by `init_app.py`, which fills them in once, and `check_placeholders.py`,
which fails an initialised repository that still has any. Stdlib only, so it
runs on the host before anything is installed.

A placeholder is `{{NAME}}`: two braces, an upper-case name, no spaces. The
no-spaces rule is what keeps Blade's `{{ $var }}` and GitHub Actions'
`${{ github.sha }}` out of it.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

PLACEHOLDER_RE = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")

# Written by init_app.py, committed. Its presence is what "initialised" means.
MARKER = ".laravel-app-initialised.json"

# Markdown between these lines exists only while the repository is the
# template (what the template is, how to use it) and is removed on init.
TEMPLATE_START = "<!-- TEMPLATE-ONLY:START -->"
TEMPLATE_END = "<!-- TEMPLATE-ONLY:END -->"

# The init tooling names the placeholders in its own source and must keep
# doing so, so it is never substituted or checked.
EXCLUDED_PREFIXES = (
    "tools/init/",
    ".claude/skills/init-laravel-app/",
)

# Every placeholder the template uses, with what it means. init_app.py
# refuses to write anything if a tracked file holds one not listed here.
PLACEHOLDERS = {
    "APP_NAME": "Display name, e.g. Acme Orders",
    "APP_SLUG": "Machine name: database, users, compose project, images",
    "APP_DESCRIPTION": "One-line description for README and CLAUDE.md",
    "SKILL_PREFIX": "Prefix for the project's own Claude skills, e.g. acme",
    "GITHUB_OWNER": "GitHub owner of this repository",
    "GITHUB_REPO": "GitHub repository name",
    "PORT_SUFFIX": "Three digits shared by the local ports, e.g. 100",
    "LOCAL_DOMAIN": "Local HTTPS hostname served by Caddy",
    "PRODUCTION_DOMAIN": "Production hostname",
}


def tracked_files(root: Path = REPO_ROOT) -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True
    ).stdout.decode()
    return [f for f in out.split("\0") if f]


def in_scope(path: str) -> bool:
    return not path.startswith(EXCLUDED_PREFIXES)


def read_text(path: Path) -> str | None:
    """The file as text, or None for anything binary (PNGs, PDFs)."""
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def find(root: Path = REPO_ROOT) -> dict[str, list[str]]:
    """Placeholder occurrences in scope: {path: [NAME, ...]}, paths included."""
    hits: dict[str, list[str]] = {}
    for rel in tracked_files(root):
        if not in_scope(rel):
            continue
        names = PLACEHOLDER_RE.findall(rel)
        text = read_text(root / rel)
        if text is not None:
            names += PLACEHOLDER_RE.findall(text)
        if names:
            hits[rel] = names
    return hits
