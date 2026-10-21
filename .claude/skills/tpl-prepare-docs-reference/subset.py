#!/usr/bin/env python3
"""Rebuild the mobile upload folder and generate its index.

Companion to build.py. The claude.ai project gets the full documentation set
through the GitHub connector, but the connector does not reach the mobile app,
so a small curated subset is uploaded as project files as well. This script
keeps that folder honest:

    subset.py           rebuild docs/claude-transfer/ and write its reference.md
    subset.py --check   report only, touch nothing

It reads docs/claude-transfer/members.txt (paths and globs, ! to exclude),
replaces every symlink in the folder with file-level links to the members,
refuses on a filename collision (the upload flattens paths, so a collision
silently loses a document), and writes docs/claude-transfer/reference.md
mapping each uploaded filename back to its repository path with the summary
docs/reference.md gives it. Summaries are never written here: both indexes
describe a document with the sentence docs/reference.md holds, so if a member
has no summary there, that is what to fix.

Exit status: 2 on a hard problem in the folder, 1 when a member lacks a
summary, 0 otherwise.
"""

import fnmatch
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

UPLOAD_DIR = Path("docs/claude-transfer")
MEMBERS_FILE = UPLOAD_DIR / "members.txt"
SUBSET_INDEX = UPLOAD_DIR / "reference.md"
FULL_INDEX = Path("docs/reference.md")
OWN_FILES = {"members.txt", "reference.md"}
CURRENT_BATCH_GLOB = "docs/work-packages/wp-000*.md"
TARGET, CEILING = 20, 30

ROW_RE = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*(.*?)\s*\|\s*$")
STATUS_RE = re.compile(r"^\*\*Status\*\*:?\s*(.+)$", re.I)
FINISHED_RE = re.compile(r"\b(shipped|released|merged|done|closed|delivered|implemented|complete[d]?)\b", re.I)
STILL_OPEN_RE = re.compile(r"\bnot (yet )?(shipped|done|started)\b|\boutstanding\b|\bremaining\b", re.I)


def repo_root() -> Path:
    out = subprocess.run(["git", "rev-parse", "--show-toplevel"], check=True, capture_output=True, text=True).stdout
    return Path(out.strip())


def changelog_version() -> str:
    m = re.search(r"^## \[?(\d+\.\d+\.\d+)", Path("CHANGELOG.md").read_text(encoding="utf-8", errors="replace"), re.M)
    return m.group(1) if m else "unknown"


def state_phrase(path: str) -> str:
    """Leading state of the document's status line, up to the first full stop."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for _ in range(40):
                line = fh.readline()
                if not line:
                    break
                m = STATUS_RE.match(line.strip())
                if m:
                    body = m.group(1).strip("* ")
                    return re.split(r"\.\s|\s\|\s", body, maxsplit=1)[0][:120]
    except OSError:
        pass
    return ""


def read_members():
    includes, excludes = [], []
    for raw in MEMBERS_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        (excludes if line.startswith("!") else includes).append(line.lstrip("!").strip())
    return includes, excludes


def resolve_members(includes, excludes):
    problems, chosen = [], set()
    for pat in includes:
        if any(ch in pat for ch in "*?["):
            matches = [p.as_posix() for p in Path(".").glob(pat) if p.is_file() and not p.is_symlink()]
            if not matches:
                problems.append(f"members.txt pattern `{pat}` matches nothing.")
            chosen.update(matches)
        elif Path(pat).is_file():
            chosen.add(pat)
        else:
            problems.append(f"members.txt names `{pat}`, which does not exist.")
    for pat in excludes:
        chosen = {c for c in chosen if not fnmatch.fnmatch(c, pat) and not c.startswith(pat.rstrip("/") + "/")}
    return sorted(chosen), problems


def folder_problems(members):
    """Collisions and anything in the folder that is not ours. Read-only."""
    problems = []
    by_name = defaultdict(list)
    for rel in members:
        by_name[Path(rel).name.lower()].append(rel)
    for name in OWN_FILES:
        if name in by_name:
            problems.append(f"NAME COLLISION: `{name}` is reserved for the folder's own files; {by_name[name]} cannot be a member.")
    for name, rels in by_name.items():
        if len(rels) > 1:
            problems.append("NAME COLLISION: `" + Path(rels[0]).name + "` appears at " + " and ".join(f"`{r}`" for r in rels)
                            + ". Only one survives the flattened upload.")
    if UPLOAD_DIR.is_dir():
        for entry in UPLOAD_DIR.iterdir():
            if not entry.is_symlink() and entry.name not in OWN_FILES:
                problems.append(f"UNEXPECTED FILE: `{entry.as_posix()}` is a regular file or directory, not a symlink. "
                                "A write through a symlink replaces the link with a copy; look at it before deleting anything.")
    return problems


def rebuild_folder(members):
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    for entry in list(UPLOAD_DIR.iterdir()):
        if entry.is_symlink():
            entry.unlink()
    problems = []
    for rel in members:
        link = UPLOAD_DIR / Path(rel).name
        link.symlink_to(os.path.relpath(rel, UPLOAD_DIR))
        if not link.exists():
            problems.append(f"BROKEN LINK: `{link.name}` does not resolve to `{rel}`.")
    return problems


def summaries_from_full_index():
    """path -> summary from docs/reference.md, ignoring the Start here table,
    whose second column says why to open a file rather than what it is."""
    out, section = {}, ""
    if not FULL_INDEX.is_file():
        return out
    for line in FULL_INDEX.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        m = ROW_RE.match(line)
        if m and section != "Start here":
            out[m.group(1)] = m.group(2)
    return out


def selected_features():
    live_specs = {p.name[:3] for p in Path("specs").glob("[0-9][0-9][0-9]-*") if p.is_dir()}
    return [p.as_posix() for p in sorted(Path("docs/features").glob("spec-[0-9][0-9][0-9]-*.md")) if p.name[5:8] not in live_specs]


def membership_review(members):
    notes, member_set = [], set(members)
    for rel in members:
        state = state_phrase(rel)
        if state and FINISHED_RE.search(state) and not STILL_OPEN_RE.search(state):
            notes.append(f"REMOVAL CANDIDATE: `{rel}` status reads as finished: {state}")
    for p in sorted(Path(".").glob(CURRENT_BATCH_GLOB)):
        if p.as_posix() not in member_set:
            notes.append(f"ADDITION CANDIDATE: `{p.as_posix()}` is in the current batch and not in the subset.")
    for rel in selected_features():
        if rel not in member_set:
            notes.append(f"ADDITION CANDIDATE: `{rel}` is selected for development (numbered, no specs/ directory) and not in the subset.")
    others = [p.name for p in sorted(Path("docs/work-packages").glob("wp-*.md")) if p.as_posix() not in member_set]
    if others:
        notes.append(f"{len(others)} other live work packages are not in the subset, by design unless a batch is picked up: " + ", ".join(others))
    if len(members) > CEILING:
        notes.append(f"SUBSET TOO LARGE: {len(members)} files. Past {CEILING} it has stopped being a subset.")
    elif len(members) > TARGET:
        notes.append(f"Subset holds {len(members)} files; the target is about {TARGET} and the ceiling is {CEILING}.")
    return notes


def section_of(rel: str) -> str:
    parts = rel.split("/")
    if len(parts) == 1:
        return "Root documents"
    if rel.startswith(".specify/memory/"):
        return ".specify/memory/"
    return "/".join(parts[:2]) + "/"


def write_subset_index(members, summaries, problems, version, today):
    missing, out = [], []
    out += ["# Mobile context reference", "",
            "Generated file. Do not hand-edit; regenerate with the tpl-prepare-docs-reference skill (`subset.py`), which rebuilds `docs/claude-transfer/` and this index together.",
            f"Generated: {today}, at version {version} (the CHANGELOG.md version at the time).", "",
            "This file describes ONLY the small subset of project documents uploaded to the claude.ai project as project files, "
            "chosen so that the documents the operator reasons against most are available on every surface, including the mobile app. "
            "The upload flattens paths to bare filenames, so each row below maps an uploaded filename back to its real repository path.", "",
            "This is not the full documentation set. The full set is synced into the project through the GitHub connector with real paths intact, "
            "and its index is `docs/reference.md`. That synced set is available in the project on desktop; it is not available in the mobile app. "
            "If a document is not listed here and you are on mobile, say that it is in the synced set rather than that it does not exist.", "",
            f"{len(members)} files are uploaded alongside this index.", ""]
    if problems:
        out += ["## Problems detected", ""] + [f"- {p}" for p in problems] + [""]
    groups = defaultdict(list)
    for rel in members:
        groups[section_of(rel)].append(rel)
    order = ["Root documents", ".specify/memory/"] + sorted(k for k in groups if k not in ("Root documents", ".specify/memory/"))
    for key in order:
        if key not in groups:
            continue
        out += [f"## {key}", "", "| Uploaded filename | Repository path | What it is |", "|---|---|---|"]
        for rel in sorted(groups[key], key=lambda r: Path(r).name.lower()):
            s = summaries.get(rel, "")
            if not s:
                s, _ = "NO SUMMARY in docs/reference.md", missing.append(rel)
            out.append(f"| {Path(rel).name} | `{rel}` | {s} |")
        out.append("")
    SUBSET_INDEX.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    return missing


def main() -> int:
    os.chdir(repo_root())
    check_only = "--check" in sys.argv
    if not MEMBERS_FILE.is_file():
        print(f"{MEMBERS_FILE} does not exist; nothing to build.")
        return 2

    includes, excludes = read_members()
    members, problems = resolve_members(includes, excludes)
    problems += folder_problems(members)
    summaries = summaries_from_full_index()
    missing = [m for m in members if m not in summaries]
    review = membership_review(members)

    rc = 2 if problems else (1 if missing else 0)
    if check_only:
        print(f"Subset: {len(members)} members from {MEMBERS_FILE}. Check only; nothing written.")
    elif problems:
        print(f"Subset: {len(members)} members. NOT rebuilt: fix the problems below first.")
    else:
        problems += rebuild_folder(members)
        missing = write_subset_index(members, summaries, problems, changelog_version(), date.today().isoformat())
        rc = 2 if problems else (1 if missing else 0)
        print(f"Subset: {len(members)} file-level symlinks rebuilt in {UPLOAD_DIR}; {SUBSET_INDEX} regenerated.")

    if problems:
        print("PROBLEMS (nothing is safe to upload until these are clear):")
        for p in problems:
            print(f"  {p}")
    if missing:
        print(f"Members with no summary row in {FULL_INDEX} ({len(missing)}); write them there, then re-run:")
        for m in missing:
            print(f"  {m}")
    if review:
        print("Membership review (reported, not applied):")
        for n in review:
            print(f"  {n}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
