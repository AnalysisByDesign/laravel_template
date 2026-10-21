#!/usr/bin/env python3
"""Guard: The project's own spec-kit hooks must stay registered.

`.specify/extensions.yml` is spec-kit's file. The project adds entries to it so that
its own skills run at spec-kit boundaries without editing spec-kit's command
files, which an upgrade would overwrite. The cost of that choice is that the
entries live in a file spec-kit also writes: `specify extension add`, `remove`
or a re-init can rewrite it, and a dropped entry fails silently. The spec-kit
phase still runs, it just stops calling the project skill, and nothing says so.
This guard is what says so.

Each entry below names the hook, the command, and the skill the command
resolves to (spec-kit turns `{{SKILL_PREFIX}}.session.name` into `/{{SKILL_PREFIX}}-session-name`).

Host-side stdlib Python, like the other docs-guard checks: the Sail container
mounts `laravel/` only, and there is no YAML parser in the standard library, so
the hook blocks are read as text. That is enough for the flat shape spec-kit
writes; a hook it cannot find is reported, not guessed at.

Run from the repository root:

    python3 tools/docs-guard/check_spec_hooks.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXTENSIONS = ".specify/extensions.yml"

# (hook, command, why it is there)
REQUIRED_HOOKS = [
    (
        "after_specify",
        "{{SKILL_PREFIX}}.session.name",
        "gives the operator the /rename command naming the session for the spec",
    ),
]


def hook_entries(text: str, hook: str) -> list[dict[str, str]]:
    """The list entries under `hooks.<hook>`, each as a flat field map."""
    lines = text.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.rstrip() == f"  {hook}:")
    except StopIteration:
        return []

    entries: list[dict[str, str]] = []
    for line in lines[start + 1 :]:
        # The block ends at the next key at or above the hook's own indent.
        if line.strip() and not line.startswith("   ") and not line.startswith("  -"):
            break
        match = re.match(r"^  (?:- |  )(\w+):\s*(.*)$", line)
        if not match:
            continue
        if line.startswith("  - "):
            entries.append({})
        if entries:
            # A quoted scalar (needed while the value is a template placeholder)
            # reads the same as a bare one.
            entries[-1][match.group(1)] = match.group(2).strip().strip("\"'")
    return entries


def skill_dir(command: str) -> Path:
    return REPO_ROOT / ".claude/skills" / command.replace(".", "-")


def main() -> int:
    path = REPO_ROOT / EXTENSIONS
    if not path.exists():
        print(f"{EXTENSIONS} is missing, so no spec-kit hook can run.", file=sys.stderr)
        return 1
    text = path.read_text()

    problems: list[str] = []
    for hook, command, why in REQUIRED_HOOKS:
        found = [e for e in hook_entries(text, hook) if e.get("command") == command]
        if not found:
            problems.append(
                f"{hook} no longer registers {command}, which {why}. A spec-kit "
                f"extension change probably rewrote {EXTENSIONS}; re-add the entry."
            )
        elif all(e.get("enabled") == "false" for e in found):
            problems.append(f"{hook} registers {command} but it is disabled.")

        if not (skill_dir(command) / "SKILL.md").exists():
            problems.append(
                f"{command} resolves to .claude/skills/{command.replace('.', '-')}/SKILL.md, "
                f"which does not exist."
            )

    if problems:
        print("project spec-kit hooks are not wired:\n", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    checked = ", ".join(f"{hook} {command}" for hook, command, _ in REQUIRED_HOOKS)
    print(f"{len(REQUIRED_HOOKS)} project spec-kit hook(s) registered: {checked}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
