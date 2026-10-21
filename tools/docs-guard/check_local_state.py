#!/usr/bin/env python3
"""Guard: machine-local state must not be tracked in git.

`.specify/feature.json` holds one key, `feature_directory`, naming the spec
every spec-kit command acts on. While it was tracked it was a single shared
slot for the whole repository, and with two checkouts working different specs
in parallel the failure was silent: each committed a diff to it, whichever
merged last became the pointer BOTH then used, and the other machine's next
spec-kit command resolved a spec nobody aimed it at.

Nothing errored, which is why this is a guard rather than a comment. It is also
why re-tracking it would go unnoticed: `git add -A` on a fresh clone, a merge
resolved the wrong way, or a well-meant "this should be in the repo" would each
put it back, and the next symptom would be a spec-kit phase writing into the
wrong directory weeks later.

Host-side stdlib Python rather than a Pest test, for the same reason
`check_areas.py` is: the Sail container mounts `laravel/` only, so `.specify/`
is not visible from inside it.

Run from the repository root:

    python3 tools/docs-guard/check_local_state.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Each entry: the path that must stay untracked, and the example that has to
# exist in its place so a fresh clone can see the shape.
LOCAL_STATE = [
    (".specify/feature.json", ".specify/feature.json.example"),
]


def tracked_files() -> set[str]:
    """Every path git has in the index, as repo-relative POSIX strings."""
    out = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return {entry for entry in out.split("\0") if entry}


def is_ignored(path: str) -> bool:
    """Whether git would ignore `path`.

    `check-ignore` exits 1 when the path is NOT ignored, which is a normal
    answer rather than a failure, so the return code is read instead of raising.
    """
    return (
        subprocess.run(
            ["git", "check-ignore", "-q", path],
            cwd=REPO_ROOT,
            capture_output=True,
        ).returncode
        == 0
    )


def main() -> int:
    problems: list[str] = []
    tracked = tracked_files()

    for path, example in LOCAL_STATE:
        if path in tracked:
            problems.append(
                f"{path} is tracked in git. It is machine-local state: one key "
                f"shared by every checkout, and a stale pointer fails silently "
                f"rather than erroring. Run: git rm --cached {path}"
            )

        if not is_ignored(path):
            problems.append(
                f"{path} is not ignored. Add it to .gitignore, or the next "
                f"`git add` puts it back."
            )

        example_path = REPO_ROOT / example
        if not example_path.exists():
            problems.append(
                f"{example} is missing. A fresh clone has no {path}, so the "
                f"example is the only thing showing its shape."
            )
            continue

        try:
            json.loads(example_path.read_text())
        except json.JSONDecodeError as error:
            problems.append(f"{example} is not valid JSON: {error}")

    if problems:
        print("Machine-local state is not local:\n", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    checked = ", ".join(path for path, _ in LOCAL_STATE)
    print(f"{len(LOCAL_STATE)} local-state path(s) untracked and ignored: {checked}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
