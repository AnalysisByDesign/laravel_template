#!/usr/bin/env python3
"""Generate the upcoming and completed roadmap documents.

    python3 tools/roadmap/build.py

Writes `docs/roadmap/upcoming.md` and `docs/roadmap/completed.md`, plus two
PlantUML diagrams of the same model (`roadmap-overview.puml` and
`roadmap-gates.puml`) with their PNG renders, all committed, all generated, none
ever edited by hand. The PNGs are rendered only when PlantUML is installed and
the diagram source changed. `{{SKILL_PREFIX}}-merge` runs this in
its fourth phase and carries the result in the documentation-only follow-up PR.

Markdown rather than PDF: other documents need to link to the roadmap, the
claude.ai project reads `docs/` and cannot read a binary, and a PDF can be made
from Markdown whenever one is wanted.

The two documents answer different questions and stay separate so the one read
daily does not grow without limit: upcoming is what is left, completed is what
landed and when.

Exit code is 0 even when the data-quality warnings fire. They describe the
repository, not this program, and failing a merge over an item nobody has filed
under an epic yet would be the wrong trade. `--strict` makes them fail instead.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import diagram  # noqa: E402
import model  # noqa: E402
import render  # noqa: E402


GENERATED_LINE = re.compile(
    r"^\*\*Status\*\*: Generated \d{4}-\d{2}-\d{2}.*$|\(generated \d{4}-\d{2}-\d{2}\)", re.MULTILINE
)


def comparable(text: str) -> str:
    """Content with the generated date removed, for comparing two builds.

    Without this, a file built yesterday differs from today's build in exactly
    one character run and reads as stale when nothing about the repository has
    moved. The date is still written into the file, because a reader wants to
    know how fresh it is.
    """
    return GENERATED_LINE.sub("", text)


def write(path: Path, text: str) -> tuple[bool, int]:
    """Write only when the substance differs, so an unchanged run leaves no diff.

    Comparing on `comparable` rather than the raw text means a regeneration on a
    day when nothing changed produces no commit, instead of a one-line date diff
    on every merge.
    """
    existing = path.read_text(encoding="utf-8") if path.exists() else None
    if existing is not None and comparable(existing) == comparable(text):
        return False, len(existing)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True, len(text)


def render_png(source: Path) -> str:
    """Render a diagram's PNG beside it. Never fails the build.

    PlantUML writes a PNG even on a syntax error, as a picture of the error, so
    the exit code is what decides whether the render is trusted (the same
    lesson the pre-commit hook records from spec-039's data model).
    """
    if not shutil.which("plantuml"):
        return "not rendered, plantuml is not installed"
    result = subprocess.run(["plantuml", "-tpng", str(source)], capture_output=True, text=True)
    if result.returncode != 0:
        return "RENDER FAILED: %s" % (result.stderr.strip() or result.stdout.strip())
    return "rendered"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out",
        default=str(render.ROADMAP_DIR),
        help="output directory (default: docs/roadmap)",
    )
    parser.add_argument(
        "--no-github",
        action="store_true",
        help="skip the open issues, for an offline or unauthenticated run",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="report whether the committed documents are current, writing nothing",
    )
    parser.add_argument(
        "--no-render",
        action="store_true",
        help="write the diagram sources but do not render their PNGs",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit non-zero if any data-quality warning fires",
    )
    args = parser.parse_args(argv)

    out = Path(args.out)
    roadmap = model.load(include_issues=not args.no_github)
    documents = {
        out / "upcoming.md": render.upcoming(roadmap),
        out / "completed.md": render.completed(roadmap),
        out / "roadmap-overview.puml": diagram.overview(roadmap),
        out / "roadmap-gates.puml": diagram.gates(roadmap),
    }

    stale = []
    for path, text in documents.items():
        if args.check:
            current = path.exists() and comparable(path.read_text(encoding="utf-8")) == comparable(text)
            if not current:
                stale.append(path)
            continue
        changed, size = write(path, text)
        shown = path.relative_to(model.REPO) if path.is_relative_to(model.REPO) else path
        print("%s  %s, %.0f KB" % (shown, "written" if changed else "unchanged", size / 1024))
        if path.suffix == ".puml" and not args.no_render and (changed or not path.with_suffix(".png").exists()):
            print("%s  %s" % (shown.with_suffix(".png"), render_png(path)))

    if args.check:
        for path in stale:
            print("stale: %s" % (path.relative_to(model.REPO) if path.is_relative_to(model.REPO) else path))
        if not stale:
            print("roadmap documents are current")
        return 1 if stale else 0

    outstanding = [i for i in roadmap.items.values() if i.state not in (model.DONE, model.DROPPED)]
    print(
        "%d items, %d epics, %d open issues, %d outstanding"
        % (len(roadmap.items), len(roadmap.epics), len(roadmap.issues), len(outstanding))
    )

    warnings = []
    if not roadmap.issues and not args.no_github:
        warnings.append("no issues read, so the fix lane is empty. Is gh authenticated?")
    unhomed, multiple = roadmap.unhomed(), roadmap.multiply_homed()
    if unhomed:
        warnings.append("%d outstanding items are homed in no epic" % len(unhomed))
    if multiple:
        warnings.append("%d items are homed in more than one epic" % len(multiple))
    missing = [i for i in roadmap.completed() if not i.merged_at]
    if missing:
        warnings.append("%d archived documents have no add commit in history" % len(missing))
    for warning in warnings:
        print("warn: %s" % warning)

    return 1 if (args.strict and warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
