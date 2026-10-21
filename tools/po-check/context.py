#!/usr/bin/env python3
"""Assemble what the product owner node is handed.

The node judges a backlog promotion. So that it has grounds rather than
opinions, it is handed exactly these, and nothing else:

- the feature document being promoted;
- the area vocabulary, docs/features/areas.json;
- the batch table from docs/work-packages/README.md;
- the roadmap's standing placement rules and build order, without its
  changelog notes;
- the Status line of every in-flight spec;
- the epic that homes the item, if one does;
- the constitution's principles.

Prints one JSON object. Nothing here reads a secret or writes a file.

Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


class ContextError(Exception):
    pass


def find_feature(repo_root: Path, name: str) -> Path:
    """Resolve a slug or filename to one backlog document."""
    backlog = repo_root / "docs" / "features" / "backlog"
    stem = re.sub(r"\.md$", "", name.split("/")[-1])
    stem = re.sub(r"^(\d{3}-)?(ft-)?(\d{3}[a-z]?-)?", "", stem)
    matches = sorted(
        p for p in backlog.glob("*.md")
        if re.match(rf"^(\d{{3}}-)?ft-(\d{{3}}[a-z]?-)?{re.escape(stem)}\.md$", p.name)
    )
    if not matches:
        raise ContextError(f"no backlog item matches '{name}' in {backlog}")
    if len(matches) > 1:
        raise ContextError(f"'{name}' is ambiguous: {[m.name for m in matches]}")
    return matches[0]


def header_block(text: str) -> str:
    return text.split("\n## ", 1)[0]


def status_line(text: str) -> str:
    for line in header_block(text).splitlines():
        if line.startswith("**Status**"):
            return line
    return ""


def batch_table(readme: Path) -> list[dict]:
    rows = []
    for line in readme.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 5 and re.search(r"`wp-[^`]+\.md`", cells[1]):
            rows.append(
                {
                    "batch": cells[0] or None,
                    "package": cells[1].strip("`"),
                    "owner": cells[2],
                    "gate": cells[3],
                    "status": cells[4],
                }
            )
    return rows


def roadmap_sections(roadmap: Path) -> dict:
    """The standing rules and the build order, with changelog notes left out."""
    if not roadmap.exists():
        return {}
    text = roadmap.read_text(encoding="utf-8")
    sections = {}
    for title in ("Standing placement rules", "Build order"):
        match = re.search(rf"^##+ {re.escape(title)}[^\n]*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
        if not match:
            continue
        body = match.group(1)
        body = re.split(r"^### Changelog", body, maxsplit=1, flags=re.M)[0]
        sections[title] = body.strip()
    return sections


def in_flight_specs(repo_root: Path) -> list[dict]:
    features = repo_root / "docs" / "features"
    specs = []
    for path in sorted(features.glob("spec-*.md")):
        number = path.name[5:8]
        text = path.read_text(encoding="utf-8")
        specs.append(
            {
                "path": str(path.relative_to(repo_root)),
                "number": number,
                "status": status_line(text),
                "areas": next(
                    (l.split(":", 1)[1].strip() for l in header_block(text).splitlines() if l.startswith("**Areas**")),
                    "",
                ),
                "spec_kit_directory": next(
                    (str(d.relative_to(repo_root)) for d in (repo_root / "specs").glob(f"{number}-*") if d.is_dir()),
                    None,
                ),
            }
        )
    return specs


def homing_epics(repo_root: Path, feature: Path) -> list[dict]:
    epics = []
    for path in sorted((repo_root / "docs" / "epics").glob("epic-*.md")):
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            if feature.name in line and line.startswith("|"):
                epics.append({"epic": str(path.relative_to(repo_root)), "row": line.strip()})
                break
    return epics


def principles(constitution: Path) -> list[dict]:
    text = constitution.read_text(encoding="utf-8")
    core = re.search(r"^## Core Principles\n(.*?)(?=^## )", text, re.S | re.M)
    if not core:
        raise ContextError(f"{constitution}: no Core Principles section")
    found = []
    for match in re.finditer(r"^### ([^\n]+)\n(.*?)(?=^### |\Z)", core.group(1), re.S | re.M):
        found.append({"title": match.group(1).strip(), "text": match.group(2).strip()})
    return found


def build(repo_root: Path, name: str) -> dict:
    feature = find_feature(repo_root, name)
    text = feature.read_text(encoding="utf-8")
    return {
        "feature": {
            "path": str(feature.relative_to(repo_root)),
            "status": status_line(text),
            "text": text,
        },
        "areas": json.loads((repo_root / "docs" / "features" / "areas.json").read_text(encoding="utf-8"))["areas"],
        "batches": batch_table(repo_root / "docs" / "work-packages" / "README.md"),
        "roadmap": roadmap_sections(repo_root / "docs" / "features" / "roadmap.md"),
        "in_flight_specs": in_flight_specs(repo_root),
        "epics": homing_epics(repo_root, feature),
        "principles": principles(repo_root / ".specify" / "memory" / "constitution.md"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("feature", help="backlog item, by slug or filename")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args(argv)
    try:
        bundle = build(args.repo_root, args.feature)
    except ContextError as problem:
        print(f"FAIL {problem}", file=sys.stderr)
        return 1
    json.dump(bundle, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
