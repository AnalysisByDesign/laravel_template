#!/usr/bin/env python3
"""Line this machine's laravel/.env up with laravel/.env.example.

The example is the layout: every line, comment and key order comes from it.
The values come from the current .env:

  - a key set in .env is written set, with its .env value, even where the
    example has it commented out (an override this machine opted into);
  - a key commented out in .env is written commented out, with the example's
    value, even where the example sets it (not needed on this machine);
  - a key .env does not mention at all is new, and is written exactly as the
    example has it;
  - a key set in .env but absent from the example is local only, and is kept
    in a section appended at the end so nothing is lost.

The result is verified before anything is written. The set variables of the
backup and of the replacement are extracted, sorted and diffed: the only
permitted difference is a new key the example sets. The replacement must also
carry every key line of the example, in order, and its set count must
reconcile with the example's. A failed check writes nothing.

Values are copied as raw text, quotes and all, and never printed: output
names keys only.

Usage:
  python3 tools/env-sync/sync_env.py            # back up, rebuild, verify
  python3 tools/env-sync/sync_env.py --check    # report only, write nothing
  python3 tools/env-sync/sync_env.py --check --strict   # ...and exit 3 if out of line
  python3 tools/env-sync/sync_env.py --env PATH --example PATH
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SET = re.compile(r"^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
# One optional space after the hash, so prose such as "#   KEY=value  means..."
# in the example's header is not mistaken for a commented-out key.
COMMENTED = re.compile(r"^#\s?([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
LOCAL_HEADER = "# Local only: set on this machine, not in .env.example (kept by tools/env-sync)"


@dataclass
class EnvFile:
    lines: list[str]
    values: dict[str, str] = field(default_factory=dict)
    commented: set[str] = field(default_factory=set)
    duplicates: list[str] = field(default_factory=list)


def parse(path: Path) -> EnvFile:
    env = EnvFile(path.read_text().splitlines())
    for line in env.lines:
        if m := SET.match(line):
            key, value = m.groups()
            if key in env.values:
                # phpdotenv loads immutably, so the first definition wins.
                env.duplicates.append(key)
                continue
            env.values[key] = value
        elif m := COMMENTED.match(line):
            env.commented.add(m.group(1))
    return env


def build(example: EnvFile, current: EnvFile):
    out: list[str] = []
    placed: set[str] = set()
    report = {"new": [], "commented_here": [], "uncommented_here": [], "local_only": []}
    example_keys: set[str] = set()

    for line in example.lines:
        if m := SET.match(line):
            key, _ = m.groups()
            example_keys.add(key)
            if key in current.values and key not in placed:
                out.append(f"{key}={current.values[key]}")
                placed.add(key)
            elif key in current.values:
                out.append(f"# {line}")  # a second definition would be dead
            elif key in current.commented:
                out.append(f"# {line}")
                report["commented_here"].append(key)
            else:
                out.append(line)
                report["new"].append(key)
        elif m := COMMENTED.match(line):
            key = m.group(1)
            example_keys.add(key)
            if key in example.values:
                # The example sets this key elsewhere, so this line is prose
                # or an alternative value, not the key's slot. Keep it as text.
                out.append(line)
            elif key in current.values and key not in placed:
                out.append(f"{key}={current.values[key]}")
                placed.add(key)
                report["uncommented_here"].append(key)
            else:
                out.append(line)
        else:
            out.append(line)

    local = [k for k in current.values if k not in example_keys]
    if local:
        out += ["", LOCAL_HEADER] + [f"{k}={current.values[k]}" for k in local]
        report["local_only"] = local
    report["dropped_comments"] = sorted(current.commented - example_keys - set(current.values))
    return out, report


def key_sequence(lines: list[str]) -> list[str]:
    keys = []
    for line in lines:
        if line == LOCAL_HEADER:
            break
        if m := SET.match(line):
            keys.append(m.group(1))
        elif m := COMMENTED.match(line):
            keys.append(m.group(1))
    return keys


def verify(example: EnvFile, backup: EnvFile, new_lines: list[str], report):
    new = EnvFile(new_lines)
    for line in new_lines:
        if (m := SET.match(line)) and m.group(1) not in new.values:
            new.values[m.group(1)] = m.group(2)
    failures = []

    # 1. Sorted set variables, backup against replacement.
    before = sorted(f"{k}={v}" for k, v in backup.values.items())
    after = sorted(f"{k}={v}" for k, v in new.values.items())
    removed = sorted(set(before) - set(after))
    added = sorted(set(after) - set(before))
    if removed:
        failures.append("set in backup but lost or changed: " + ", ".join(e.split("=", 1)[0] for e in removed))
    unexpected = [e.split("=", 1)[0] for e in added if e.split("=", 1)[0] not in report["new"]]
    if unexpected:
        failures.append("set in replacement but not from backup or a new example key: " + ", ".join(unexpected))

    # 2. Every key line of the example is present, in order.
    if key_sequence(new_lines) != key_sequence(example.lines):
        failures.append("replacement key lines do not follow .env.example one for one")

    # 3. Set counts reconcile with the example.
    expected = (len(example.values) - len(report["commented_here"]) + len(report["uncommented_here"])
                + len(report["local_only"]))
    if len(new.values) != expected:
        failures.append(f"set count {len(new.values)}, expected {expected}")
    return failures, added


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--env", type=Path, default=REPO / "laravel/.env")
    ap.add_argument("--example", type=Path, default=REPO / "laravel/.env.example")
    ap.add_argument("--check", action="store_true", help="report only, write nothing")
    ap.add_argument("--strict", action="store_true", help="with --check, exit 3 when .env is out of line")
    args = ap.parse_args()

    for p in (args.env, args.example):
        if not p.is_file():
            print(f"missing: {p}", file=sys.stderr)
            return 2

    example, current = parse(args.example), parse(args.env)
    new_lines, report = build(example, current)
    failures, added = verify(example, current, new_lines, report)
    changed = "\n".join(new_lines) + "\n" != args.env.read_text()

    def show(label, keys):
        print(f"{label:<20}{len(keys)}" + (f"  {', '.join(keys)}" if keys else ""))

    show("New from example", report["new"])
    show("Commented here", report["commented_here"])
    show("Uncommented here", report["uncommented_here"])
    show("Local only, kept", report["local_only"])
    show("Stale comments", report["dropped_comments"])
    show("Duplicates in .env", current.duplicates)
    print(f"{'Set counts':<20}example {len(example.values)}, backup {len(current.values)}, "
          f"replacement {len(current.values) + len(added)}")
    print(f"{'Set diff':<20}" + ("none" if not added else
          "only new example keys: " + ", ".join(e.split('=', 1)[0] for e in added)))

    if failures:
        print("\nVERIFY FAILED, nothing written:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    if not changed:
        print("\nAlready in line with .env.example, nothing written.")
        return 0
    if args.check:
        print("\nVerified. --check given, nothing written.")
        return 3 if args.strict else 0

    backup = args.env.with_name(f".env.backup-{datetime.now():%Y%m%d-%H%M%S}")
    shutil.copy2(args.env, backup)
    tmp = args.env.with_name(".env.sync-tmp")
    tmp.write_text("\n".join(new_lines) + "\n")
    shutil.copymode(args.env, tmp)
    tmp.replace(args.env)
    print(f"\nVerified and written. Backup: {backup}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
