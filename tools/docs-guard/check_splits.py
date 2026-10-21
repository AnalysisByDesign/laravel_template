#!/usr/bin/env python3
"""Guard: a split feature's parent and slices must agree.

`tpl-split-feature` turns one oversize backlog capture into ordered slices and
restates the original as their parent. The link lives in the files themselves,
so that the roadmap generator reads real
artefacts rather than a hand-kept index:

    parent:  **Slices** (build order):
             1. `ft-first-slice.md`
             2. `ft-second-slice.md`

    slice:   **Parent**: `ft-the-parent.md`, slice 1 of 2.

Two sides of one link drift the way every hand-kept pair here has drifted, and
a broken link fails silently: the roadmap just shows a slice as a free
standing feature. So this checks, across `docs/features/` (live, backlog,
done and dropped):

- every slice a parent lists resolves to exactly one document;
- that document names the parent back, at the right position and count;
- every `**Parent**` line points at a parent that lists it;
- no parent has been promoted, since a parent is never built itself.

Names resolve by slug, so a slice still reads correctly after promotion
renames `ft-<slug>.md` to `spec-NNN-<slug>.md`, and both a batch number
(`ft-NNN-<slug>.md`) and the older priority prefix
(`NNN-ft-<slug>.md`) are tolerated.

Host-side stdlib Python, like the other docs-guard checks: the Sail container
mounts `laravel/` only.

Run from the repository root:

    python3 tools/docs-guard/check_splits.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SUBDIRS = ["", "backlog", "done", "dropped"]

SLICES_RE = re.compile(r"^\*\*Slices\*\* \(build order\):\s*$", re.M)
LIST_ITEM_RE = re.compile(r"^(\d+)\. `([^`]+\.md)`\s*$")
PARENT_RE = re.compile(r"^\*\*Parent\*\*: `([^`]+\.md)`, slice (\d+) of (\d+)\.\s*$", re.M)


def slug_of(filename: str) -> str:
    name = Path(filename).name.removesuffix(".md")
    name = re.sub(r"^\d{3}-(?=ft-)", "", name)
    name = re.sub(r"^(ft-(\d{3}[a-z]?-)?|spec-\d{3}-)", "", name)
    return name


def documents(features: Path) -> list[Path]:
    found: list[Path] = []
    for sub in SUBDIRS:
        d = features / sub if sub else features
        if d.is_dir():
            found += sorted(p for p in d.glob("*.md") if p.name != "README.md")
    return found


def slice_list(text: str) -> list[tuple[int, str]] | None:
    """The parent's numbered list, or None if this is not a parent."""
    match = SLICES_RE.search(text)
    if not match:
        return None
    items: list[tuple[int, str]] = []
    for line in text[match.end():].lstrip("\n").splitlines():
        item = LIST_ITEM_RE.match(line)
        if not item:
            break
        items.append((int(item.group(1)), item.group(2)))
    return items


def run(features: Path) -> list[str]:
    docs = documents(features)
    by_slug: dict[str, list[Path]] = {}
    for doc in docs:
        by_slug.setdefault(slug_of(doc.name), []).append(doc)

    def rel(p: Path) -> str:
        return p.relative_to(features.parent.parent).as_posix() if features.parent.parent in p.parents else p.as_posix()

    def resolve(name: str) -> tuple[Path | None, str | None]:
        matches = by_slug.get(slug_of(name), [])
        if len(matches) == 1:
            return matches[0], None
        if not matches:
            return None, f"`{name}` resolves to no document under docs/features/"
        return None, f"`{name}` resolves to {len(matches)} documents: " + ", ".join(rel(m) for m in matches)

    problems: list[str] = []
    texts = {doc: doc.read_text(encoding="utf-8") for doc in docs}
    parents: dict[Path, list[tuple[int, str]]] = {}

    for doc, text in texts.items():
        items = slice_list(text)
        if items is None:
            continue
        parents[doc] = items
        if doc.name.startswith("spec-"):
            problems.append(f"{rel(doc)} is a split parent but has been promoted; promote its slices instead.")
        if len(items) < 2:
            problems.append(f"{rel(doc)} lists {len(items)} slice(s); a split has at least two.")
        if [n for n, _ in items] != list(range(1, len(items) + 1)):
            problems.append(f"{rel(doc)} numbers its slices out of sequence.")

        for position, (_, name) in enumerate(items, start=1):
            target, error = resolve(name)
            if error:
                problems.append(f"{rel(doc)} lists {error}.")
                continue
            back = PARENT_RE.search(texts[target])
            if not back:
                problems.append(f"{rel(target)} is listed as a slice of {rel(doc)} but has no **Parent** line.")
                continue
            parent_name, n, m = back.group(1), int(back.group(2)), int(back.group(3))
            if slug_of(parent_name) != slug_of(doc.name):
                problems.append(f"{rel(target)} names `{parent_name}` as its parent, but {rel(doc)} lists it.")
            if (n, m) != (position, len(items)):
                problems.append(
                    f"{rel(target)} says slice {n} of {m}; {rel(doc)} lists it as {position} of {len(items)}."
                )

    for doc, text in texts.items():
        back = PARENT_RE.search(text)
        if not back:
            continue
        parent, error = resolve(back.group(1))
        if error:
            problems.append(f"{rel(doc)} names a parent that {error.split(' ', 1)[1]}.")
            continue
        if parent not in parents:
            problems.append(f"{rel(doc)} names {rel(parent)} as its parent, which has no **Slices** list.")
        elif slug_of(doc.name) not in {slug_of(name) for _, name in parents[parent]}:
            problems.append(f"{rel(doc)} names {rel(parent)} as its parent, which does not list it.")

    return problems


def main() -> int:
    problems = run(REPO_ROOT / "docs" / "features")
    if problems:
        print("Split features do not agree with their slices:\n", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    print("Split links consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
