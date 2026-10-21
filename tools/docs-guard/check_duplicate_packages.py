#!/usr/bin/env python3
"""Guard: no work package or feature document exists twice under two names.

The shape it catches: a package is added unnumbered in one PR, a second PR
branched from the first renames it to `wp-NNN-<slug>.md`, both are
squash-merged, and the rename half of the second squash does not remove the
first name. `main` then holds the same package twice. Git warns about none of
this.

The batch number sits after the `wp-` prefix, so a comparison must strip
`wp-NNN-` rather than a leading `NNN-`, or it strips nothing and reports clean.
A check that only runs when somebody remembers to paste it reports clean
because it was never run, so this is the same comparison on every pull request.

Scope is both archive pairs, because the same squash-merge shape applies to
feature documents, which `tpl-archive-spec` moves between the same kind of live
and `done/` folders.

Host-side stdlib Python rather than a Pest test, for the same reason
`check_areas.py` is: the Sail container mounts `laravel/` only, so `docs/` is
not visible from inside it.

Run from the repository root:

    python3 tools/docs-guard/check_duplicate_packages.py
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Folder sets that hold the same documents under live and archived names. A
# duplicate within one of these sets is the defect; the same slug appearing in
# two different sets is not, because a work package and a feature are different
# documents that may legitimately share a topic.
FOLDER_SETS = [
    ("work packages", ["docs/work-packages", "docs/work-packages/backlog", "docs/work-packages/done"]),
    (
        "features",
        [
            "docs/features",
            "docs/features/backlog",
            "docs/features/done",
            "docs/features/dropped",
        ],
    ),
]

# A work package's batch number sits INSIDE the name, after the `wp-` prefix,
# and is stripped when the package is archived. A backlog
# capture's batch number sits inside the name the same way (`ft-001-<slug>`);
# the older priority prefix in front is still recognised. Both are scheduling rather than identity, so both come
# off before comparing. A spec number is identity and stays: spec-011 was
# deliberately reused for a different feature, and merging the two would report
# a duplicate that is not one.
BATCH_INSIDE = re.compile(r"^(wp|ft)-\d{3}[a-z]?-")
PRIORITY_IN_FRONT = re.compile(r"^\d{3}-(ft-)")


def canonical(name: str) -> str:
    """A filename reduced to the identity two copies of one document share."""
    name = PRIORITY_IN_FRONT.sub(r"\1", name)
    return BATCH_INSIDE.sub(r"\1-", name)


def duplicates_in(folders: list[str]) -> dict[str, list[str]]:
    """Canonical names appearing more than once across a folder set.

    `README.md` is excluded and the exclusion is load-bearing: there is
    legitimately one per directory, so without it this reports a duplicate on
    every single run, and a check that always cries wolf is worse than no check
    because people stop reading it.
    """
    seen: dict[str, list[str]] = defaultdict(list)
    for folder in folders:
        directory = REPO_ROOT / folder
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.md")):
            if path.name == "README.md":
                continue
            seen[canonical(path.name)].append(f"{folder}/{path.name}")
    return {key: paths for key, paths in seen.items() if len(paths) > 1}


def main() -> int:
    problems: list[str] = []
    counted = 0

    for label, folders in FOLDER_SETS:
        found = duplicates_in(folders)
        counted += sum(
            1
            for folder in folders
            if (REPO_ROOT / folder).is_dir()
            for path in (REPO_ROOT / folder).glob("*.md")
            if path.name != "README.md"
        )
        for key, paths in sorted(found.items()):
            problems.append(f"{label}: {key} exists {len(paths)} times: " + ", ".join(paths))

    if problems:
        print("The same document exists under more than one name:\n", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        print(
            "\nThis is almost always a squash-merge of a stacked PR whose rename half\n"
            "did not remove the old name. Delete the copy that is in the wrong folder,\n"
            "keeping the one whose location matches its status line.",
            file=sys.stderr,
        )
        return 1

    print(f"{counted} documents checked, no slug appears twice")
    return 0


if __name__ == "__main__":
    sys.exit(main())
