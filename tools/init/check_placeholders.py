#!/usr/bin/env python3
"""Guard: an initialised repository has no `{{PLACEHOLDER}}` left in it.

The template itself is full of them, by design, so before init this reports
how many there are and passes. Once `.laravel-app-initialised.json` exists,
any placeholder in a tracked file or path fails: it means a file was added
from the template after init, or init missed something.

Run from the repository root:

    python3 tools/init/check_placeholders.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from placeholders import MARKER, REPO_ROOT, find  # noqa: E402


def main(root: Path = REPO_ROOT) -> int:
    hits = find(root)
    count = sum(len(v) for v in hits.values())

    if not (root / MARKER).exists():
        print(f"Template, not initialised: {count} placeholder(s) in {len(hits)} file(s). Run the init-laravel-app skill.")
        return 0

    if not hits:
        print("Initialised, no placeholders left.")
        return 0

    print(f"Initialised, but {count} placeholder(s) remain:", file=sys.stderr)
    for path, names in sorted(hits.items()):
        print(f"  {path}: {', '.join(sorted(set(names)))}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
