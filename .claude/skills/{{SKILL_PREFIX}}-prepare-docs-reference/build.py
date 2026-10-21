#!/usr/bin/env python3
"""Enumerate the synced documentation set and propose index entries.

Companion to .claude/skills/{{SKILL_PREFIX}}-prepare-docs-reference/SKILL.md. Two modes:

    build.py            candidate index entries on stdout
    build.py --check    the pre-sync report only

Deliberately does no writing. The skill's whole point is that a person
rewrites the mechanical summaries into ones worth reading, and a script
that wrote docs/reference.md directly would make skipping that step the
path of least resistance.

It does, however, read the current docs/reference.md and hand back the
summaries already written there, marked "kept". Only genuinely new files
come back as "new" needing a sentence. Without that the skill's "replace
wholesale" instruction meant re-authoring every summary on every run,
which is not a thing anyone does, so in practice the file was hand-edited
or left to rot instead.
"""

import os
import re
import sys

ROOT_FILES = ["CLAUDE.md", "CHANGELOG.md", "README.md"]
TREES = ["docs", ".specify/memory"]
EXCLUDED = {"docs/sessions", "docs/claude-transfer"}

STATUS_RE = re.compile(r"^\*\*Status\*\*:\s*(.+)$", re.M)
HEADING_RE = re.compile(r"^#\s+(.+)$", re.M)
# Repo-relative paths cited inside backticks, e.g. `docs/features/x.md`.
CITED_RE = re.compile(r"`((?:docs|specs|laravel|\.specify|\.claude)/[^`\s]+?)`")


REFERENCE = "docs/reference.md"
SECTION_RE = re.compile(r"^##\s+(.+?)\s*$")
# A summary row: | `path` | text |. The header and separator rows carry no
# backticks, so they do not match and need no special case.
ROW_RE = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*(.*?)\s*\|\s*$")
# A compact listing entry: - `path`. The done/ folders use these instead of
# per-file summaries, deliberately.
BULLET_RE = re.compile(r"^-\s*`([^`]+)`\s*$")


# Patterns that stand for a shape rather than naming a file: `specs/NNN-*/`,
# `docs/sessions/YYYY-MM-DD-topic.md`, `docs/decisions/0001-*.md`. Reporting
# these as broken would bury the real findings under noise, and a check
# nobody trusts is worse than no check.
PLACEHOLDER_RE = re.compile(r"[*{}]|NNN|YYYY|MM-DD|<[^>]+>")


def is_placeholder(path):
    return bool(PLACEHOLDER_RE.search(path))


# A citation may carry a line reference, `path/to/file.php:49-50`. The file is
# what has to exist; the line number is not part of its name.
LINE_SUFFIX_RE = re.compile(r":\d+(?:-\d+)?$")

# Citations that are meant not to resolve: a file since deleted that a
# historical record names, an example, a branch or package name that happens
# to look like a path, a document a work package proposes to write. One line
# each, tab separated: citing file, cited path, reason. Kept beside the script
# so that excusing a broken path is a reviewable diff, never a silent one.
ALLOW_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "unresolved-allow.tsv")


def allowed_unresolved():
    allowed = set()
    try:
        lines = open(ALLOW_FILE, encoding="utf-8").read().split("\n")
    except OSError:
        return allowed
    for line in lines:
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            allowed.add((parts[0], parts[1]))
    return allowed


def normalise_dashes(text):
    """House style forbids em and en dashes in anything written here.

    Source headings predate that rule in a few places, and an index that
    copies them verbatim quietly reintroduces the thing the rule exists to
    stop. Replaced with a colon, which is what the dash was standing in for
    in every observed case.
    """
    return text.replace(" \u2014 ", ": ").replace(" \u2013 ", ": ").replace("\u2014", "-").replace("\u2013", "-")


def excluded(path):
    return any(path == e or path.startswith(e + "/") for e in EXCLUDED)


def synced_files():
    found = [f for f in ROOT_FILES if os.path.isfile(f)]

    for tree in TREES:
        for dirpath, dirnames, filenames in os.walk(tree):
            dirnames[:] = [d for d in dirnames if not excluded(os.path.join(dirpath, d))]
            if excluded(dirpath):
                continue
            for name in sorted(filenames):
                if name.endswith(".md"):
                    found.append(os.path.join(dirpath, name))

    return sorted(set(found))


def summarise(path):
    """First heading, and the first line of prose that is not boilerplate."""
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return "", ""

    heading = HEADING_RE.search(text)
    heading = heading.group(1).strip() if heading else os.path.basename(path)
    heading = normalise_dashes(heading)

    for line in text.split("\n"):
        line = line.strip()
        if not line or line.startswith(("#", "|", "-", "*", ">", "<!--", "```")):
            continue
        if line.startswith("**") and "**:" in line:
            continue
        return heading, line[:200]

    return heading, ""


def authored_index(path=REFERENCE):
    """The summaries a person has already written into the current index.

    Returned as a list of (path, section, summary) in file order rather than
    a dict, because a path legitimately appears more than once: "Start here"
    carries a terse orientation line and the document's own section carries
    the full one. Four of the five repeated paths differ that way today.
    Keying by path alone would drop one of the pair, which is the whole
    failure this function exists to prevent.

    A compact listing entry yields an empty summary. That is deliberate: the
    done/ folders are listed by path only, and turning one into a blank table
    row would be a worse index, not a more complete one.
    """
    rows, section = [], ""

    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return rows

    for line in text.split("\n"):
        heading = SECTION_RE.match(line)
        if heading:
            section = heading.group(1)
            continue

        row = ROW_RE.match(line)
        if row:
            rows.append((row.group(1), section, row.group(2)))
            continue

        bullet = BULLET_RE.match(line)
        if bullet:
            rows.append((bullet.group(1), section, ""))

    return rows


def check(files):
    problems = {"uncovered": [], "orphaned": [], "unresolved": [], "no_status": [], "stale_allow": []}
    allowed, used = allowed_unresolved(), set()

    for path in files:
        try:
            text = open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            continue

        for cited in set(CITED_RE.findall(text)):
            if is_placeholder(cited):
                continue
            target = LINE_SUFFIX_RE.sub("", cited).rstrip("/")
            if os.path.exists(target):
                continue
            if (path, cited) in allowed:
                used.add((path, cited))
                continue
            problems["unresolved"].append((path, cited))

        if path.startswith("docs/features/spec-") and not STATUS_RE.search(text):
            problems["no_status"].append(path)

    # Files the index does not mention at all. The dict has carried a key for
    # this since the skill was written and nothing ever filled it, so the
    # check the SKILL.md promises has never actually run.
    authored = authored_index()

    covered = {p for p, _, _ in authored}
    problems["uncovered"] = [p for p in files if p != REFERENCE and p not in covered]

    # Rows for files outside the synced set. Only synced files come back as
    # "kept", so a summary written against one of these is dropped on the next
    # regeneration without anything saying so. Silent loss is the reason the
    # index could not safely be regenerated at all, so it is reported here
    # rather than left to be noticed.
    synced = set(files)
    problems["orphaned"] = sorted({p for p, _, _ in authored
                                   if p != REFERENCE and p not in synced})

    # An allowance nothing used: the citation was fixed, removed, or now
    # resolves. Reported so the file shrinks again instead of only growing.
    problems["stale_allow"] = sorted(allowed - used)

    return problems


def main():
    files = synced_files()

    if "--check" in sys.argv:
        problems = check(files)
        print(f"Synced documents: {len(files)}\n")

        print(f"Cited paths that do not resolve: {len(problems['unresolved'])}")
        for path, cited in sorted(problems["unresolved"])[:60]:
            print(f"  {path}\n    -> {cited}")

        print(f"\nFiles in the synced set the index does not cover: {len(problems['uncovered'])}")
        for path in problems["uncovered"]:
            print(f"  {path}")

        print(f"\nIndex rows for files outside the synced set: {len(problems['orphaned'])}")
        for path in problems["orphaned"]:
            print(f"  {path}")

        print(f"\nSpec feature docs with no Status line: {len(problems['no_status'])}")
        for path in problems["no_status"]:
            print(f"  {path}")

        print(f"\nAllowances in unresolved-allow.tsv that nothing used: {len(problems['stale_allow'])}")
        for path, cited in problems["stale_allow"]:
            print(f"  {path}\n    -> {cited}")
        return

    # Columns: state, path, section, text. One line per index occurrence, so a
    # path carrying both a "Start here" line and a full one comes back twice
    # and can be put back in both places.
    authored = {}
    for path, section, summary in authored_index():
        authored.setdefault(path, []).append((section, summary))

    for path in files:
        occurrences = authored.get(path)

        if not occurrences:
            heading, prose = summarise(path)
            print(f"new\t{path}\t\t{heading} | {prose}")
            continue

        for section, summary in occurrences:
            state = "kept" if summary else "listed"
            print(f"{state}\t{path}\t{section}\t{summary}")


if __name__ == "__main__":
    main()
