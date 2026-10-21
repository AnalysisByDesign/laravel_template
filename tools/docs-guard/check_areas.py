#!/usr/bin/env python3
"""Area tag guard for feature documents .

Every feature document carries a line of the form

    **Areas**: accounts, billing

before its first second-level heading, and every value on it must be a
key of docs/features/areas.json. This runs on the host and in CI, not
in Pest, because the Sail container mounts only two subfolders of docs/.

Exit status is 1 on any unknown tag or malformed line. A document with
no Areas line is reported, and fails the run only with --require-tags.


Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FEATURES_DIR = REPO_ROOT / "docs" / "features"
VOCABULARY = FEATURES_DIR / "areas.json"

# Folder, relative to docs/features, and the filename pattern that marks
# a document as a spec, seed or capture rather than an index or roadmap.
TAGGED_SETS = (
    ("", re.compile(r"^spec-\d{3}-.+\.md$")),
    ("done", re.compile(r"^(spec-\d{3}|ft)-.+\.md$")),
    ("backlog", re.compile(r"^(\d{3}-)?ft-.+\.md$")),
)

AREAS_LINE = re.compile(r"^\*\*Areas\*\*:[ \t]*(.*)$")
TAG_SHAPE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")


def load_vocabulary(path: Path) -> set[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data.get("version"), int):
        raise ValueError(f"{path}: top-level integer 'version' is required")
    areas = data.get("areas")
    if not isinstance(areas, dict) or not areas:
        raise ValueError(f"{path}: 'areas' must be a non-empty object")
    for tag, entry in areas.items():
        if not TAG_SHAPE.match(tag):
            raise ValueError(f"{path}: tag '{tag}' is not lower-case kebab-case")
        if not str(entry.get("description", "")).strip():
            raise ValueError(f"{path}: tag '{tag}' has no description")
        for neighbour in entry.get("related", []):
            if neighbour not in areas:
                raise ValueError(
                    f"{path}: tag '{tag}' names unknown related tag '{neighbour}'"
                )
    return set(areas)


def tagged_documents(features_dir: Path) -> list[Path]:
    documents = []
    for folder, pattern in TAGGED_SETS:
        root = features_dir / folder if folder else features_dir
        if not root.is_dir():
            continue
        documents.extend(
            path
            for path in sorted(root.iterdir())
            if path.is_file() and pattern.match(path.name)
        )
    return documents


def read_areas(text: str) -> tuple[list[str] | None, int]:
    """Return the tags on the Areas line and how many such lines exist.

    Only the header block counts: everything before the first second-level
    heading, which is where the other bold key-value lines live.
    """
    found = None
    count = 0
    for line in text.splitlines():
        if line.startswith("## "):
            break
        match = AREAS_LINE.match(line.strip())
        if match:
            count += 1
            if found is None:
                found = [tag.strip() for tag in match.group(1).split(",")]
    return found, count


def check_document(path: Path, vocabulary: set[str]) -> tuple[list[str], bool]:
    """Return the errors for one document and whether it is untagged."""
    tags, count = read_areas(path.read_text(encoding="utf-8"))
    if tags is None:
        return [], True
    errors = []
    if count > 1:
        errors.append(f"{count} Areas lines, expected one")
    if tags == [""]:
        errors.append("Areas line is empty")
        return errors, False
    seen = set()
    for tag in tags:
        if not tag:
            errors.append("empty value on the Areas line (stray comma)")
        elif tag not in vocabulary:
            errors.append(f"unknown area '{tag}'")
        elif tag in seen:
            errors.append(f"area '{tag}' listed twice")
        seen.add(tag)
    return errors, False


def run(features_dir: Path, vocabulary_path: Path, require_tags: bool) -> int:
    try:
        vocabulary = load_vocabulary(vocabulary_path)
    except (OSError, ValueError) as problem:
        print(f"FAIL vocabulary: {problem}")
        return 1

    documents = tagged_documents(features_dir)
    failures = 0
    untagged = []
    for path in documents:
        errors, missing = check_document(path, vocabulary)
        relative = path.relative_to(features_dir.parent.parent)
        if missing:
            untagged.append(relative)
        for error in errors:
            failures += 1
            print(f"FAIL {relative}: {error}")

    label = "FAIL" if require_tags else "WARN"
    for relative in untagged:
        print(f"{label} {relative}: no Areas line")
    if require_tags:
        failures += len(untagged)

    print(
        f"{len(documents)} documents, {len(documents) - len(untagged)} tagged, "
        f"{len(untagged)} untagged, {len(vocabulary)} areas in the vocabulary"
    )
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--require-tags",
        action="store_true",
        help="fail on a document with no Areas line, not only on a bad one",
    )
    parser.add_argument("--features-dir", type=Path, default=FEATURES_DIR)
    parser.add_argument("--vocabulary", type=Path, default=None)
    args = parser.parse_args(argv)
    vocabulary = args.vocabulary or args.features_dir / "areas.json"
    return run(args.features_dir, vocabulary, args.require_tags)


if __name__ == "__main__":
    sys.exit(main())
