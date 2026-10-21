#!/usr/bin/env python3
"""Validate a product owner verdict, and append an override entry.

Two commands:

  verdict.py check <verdict.json> [--batches <readme>]
      Exit 0 when the verdict has the contract's shape; exit 1 and say
      what is wrong otherwise. Every field is required and the closed
      sets are enforced, so a node that drifts is caught before the
      promotion skill branches on it.

  verdict.py override <verdict.json> --feature <path> --reason "<text>" --date YYYY-MM-DD
      Append one entry to docs/ceremonies/po-overrides.md. The reason
      must be non-empty: a proceed without a reason is not recorded, and
      the skill must not promote without recording it.

Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OVERRIDE_LOG = REPO_ROOT / "docs" / "ceremonies" / "po-overrides.md"
VERDICTS = ("promote", "challenge", "defer")
REQUIRED = ("verdict", "reason", "displaces", "principle_conflicts", "spec_exists")

LOG_HEADER = """# Product owner overrides

**Location**: `docs/ceremonies/po-overrides.md`

Append-only. One dated entry per promotion that the product owner node challenged or deferred and the operator chose to proceed with anyway, written by the `tpl-promote-backlog-spec` skill and never by the node itself. After twenty entries this is evidence about which departures from the plan paid off. Never edit or remove an entry; a later correction is a new entry that cites the old one.

"""


def check(verdict: dict) -> list[str]:
    problems = []
    for key in REQUIRED:
        if key not in verdict:
            problems.append(f"missing field '{key}'")
    if problems:
        return problems
    if verdict["verdict"] not in VERDICTS:
        problems.append(f"verdict '{verdict['verdict']}' is not one of {VERDICTS}")
    if not str(verdict["reason"]).strip():
        problems.append("reason is empty")
    for key in ("displaces", "principle_conflicts"):
        value = verdict[key]
        if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
            problems.append(f"{key} must be a list of non-empty strings")
    if not isinstance(verdict["spec_exists"], bool):
        problems.append("spec_exists must be true or false")
    if verdict["verdict"] == "defer" and not str(verdict.get("recommended_batch", "")).strip():
        problems.append("a defer verdict names a recommended_batch")
    if verdict["verdict"] == "promote" and (verdict["principle_conflicts"] or verdict["displaces"]):
        problems.append("a promote verdict cannot list principle conflicts or displaced work")
    return problems


def override_entry(verdict: dict, feature: str, reason: str, date: str) -> str:
    if not reason.strip():
        raise ValueError("an override needs a reason")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        raise ValueError("date must be YYYY-MM-DD")
    lines = [
        f"## {date}: {feature}",
        "",
        f"- **Node's verdict**: {verdict['verdict']}",
        f"- **Node's reason**: {verdict['reason']}",
    ]
    if verdict["displaces"]:
        lines.append(f"- **Displaces**: {', '.join(verdict['displaces'])}")
    if verdict["principle_conflicts"]:
        lines.append(f"- **Principle conflicts**: {', '.join(verdict['principle_conflicts'])}")
    if verdict.get("recommended_batch"):
        lines.append(f"- **Node recommended**: {verdict['recommended_batch']}")
    lines += [f"- **Operator's reason to proceed**: {reason.strip()}", ""]
    return "\n".join(lines) + "\n"


def append_override(log: Path, entry: str) -> None:
    if not log.exists():
        log.write_text(LOG_HEADER, encoding="utf-8")
    with log.open("a", encoding="utf-8") as handle:
        handle.write(entry)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p_check = sub.add_parser("check")
    p_check.add_argument("verdict", type=Path)
    p_over = sub.add_parser("override")
    p_over.add_argument("verdict", type=Path)
    p_over.add_argument("--feature", required=True)
    p_over.add_argument("--reason", required=True)
    p_over.add_argument("--date", required=True)
    p_over.add_argument("--log", type=Path, default=OVERRIDE_LOG)
    args = parser.parse_args(argv)

    try:
        verdict = json.loads(args.verdict.read_text(encoding="utf-8"))
    except (OSError, ValueError) as problem:
        print(f"FAIL cannot read verdict: {problem}", file=sys.stderr)
        return 1
    problems = check(verdict) if isinstance(verdict, dict) else ["verdict is not an object"]
    if problems:
        for problem in problems:
            print(f"FAIL {problem}", file=sys.stderr)
        return 1
    if args.command == "check":
        print(f"OK verdict={verdict['verdict']}")
        return 0
    if verdict["verdict"] == "promote":
        print("FAIL a promote verdict needs no override", file=sys.stderr)
        return 1
    try:
        append_override(args.log, override_entry(verdict, args.feature, args.reason, args.date))
    except ValueError as problem:
        print(f"FAIL {problem}", file=sys.stderr)
        return 1
    print(f"OK appended to {args.log}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
