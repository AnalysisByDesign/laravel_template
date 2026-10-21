"""Read the repository's real artefacts into a roadmap model.

The rule this module obeys: every fact comes from an artefact that is maintained for its own sake, never
from a hand-maintained roadmap source. A roadmap nobody has to update by hand
is the only kind that stays true.

What it reads:

- `docs/epics/README.md` for the epic sequence, and each `epic-*.md` for the
  items it homes. The epics folder is already the repository's answer to "what
  is left", so this reads it rather than competing with it.
- `docs/features/` (live seeds, `backlog/`, `done/`, `dropped/`) and
  `docs/work-packages/` (live, `backlog/`, `done/`) for every item and its header block.
- `git log` for the merge that archived each finished document.
- `gh` for open issues, which is optional and degrades to nothing.
- `docs/epics/roadmap.json`, optional, for the issue labels that place an issue
  in an epic (`issue_labels`) and the epics drawn alongside the main path
  (`alongside`). Absent, both are empty.

What it does not read: any hand-maintained build-order document. Parsing one
would couple this generator to a source that stops being current.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

FEATURES = REPO / "docs" / "features"
WORK_PACKAGES = REPO / "docs" / "work-packages"
EPICS = REPO / "docs" / "epics"

# Headings in an epic that describe the epic rather than home an item. Anything
# else is read as an item section. Inverted deliberately: an epic such as
# `epic-uncategorised.md` may use "Section A" to "Section E" instead of "Items",
# and an allow list would silently home none of its items.
NON_ITEM_SECTIONS = (
    "related, homed elsewhere",
    "needs the operator's ruling",
    "gaps",
    "why this epic exists",
    "why this is a candidate",
    "done when",
    "what the roadmap currently rules",
    "what this file says",
)

DOC_REFERENCE = re.compile(r"\b((?:ft|wp|spec|epic)-[a-z0-9][a-z0-9-]*\.md)\b")
ISSUE_REFERENCE = re.compile(r"(?<![\w/#])#(\d{1,5})\b")
HEADER_FIELD = re.compile(r"^\*\*(.+?)\*\*\s*:?\s*(.*)$")
# The shape `{{SKILL_PREFIX}}-split-feature` writes into a slice capture, and the shape
# `tools/docs-guard/check_splits.py` enforces:
#     **Parent**: `ft-the-parent.md`, slice 1 of 2.
# That skill and its guard are the source of the shape, so this reader matches
# them rather than the other way round. The fallback accepts a bare filename so a
# hand-written link is not silently ignored.
PARENT_FIELD = re.compile(r"`?([a-z0-9][a-z0-9-]*\.md)`?(?:\s*,\s*slice\s+(\d+)\s+of\s+(\d+))?", re.I)
BATCH_PREFIX = re.compile(r"^(wp|ft)-\d{3}[a-z]?-")
PRIORITY_PREFIX = re.compile(r"^\d{3}-(ft-)")

DONE = "done"
DROPPED = "dropped"
IN_PROGRESS = "in progress"
WAITING = "waiting"
OPEN = "open"

STATE_ORDER = {IN_PROGRESS: 0, OPEN: 1, WAITING: 2, DONE: 3, DROPPED: 4}

_DONE_WORDS = (
    "shipped", "delivered", "implemented", "built", "complete", "closed",
    "archived", "merged", "released", "done.", "done,", "done ",
)
_PROGRESS_WORDS = ("in progress", "in flight", "partially", "part built", "under way")
_WAITING_WORDS = (
    "deferred", "parked", "blocked", "waits on", "waiting on", "gated",
    "awaiting", "on hold", "not yet",
)
_DROPPED_WORDS = ("dropped", "superseded", "abandoned", "declined", "withdrawn")


DASH_RANGE = re.compile(r"(\d)\s*[\u2013\u2014]\s*(\d)")
DASH_CLAUSE = re.compile(r"\s*[\u2013\u2014]\s*")


def no_dashes(text: str) -> str:
    """Remove em and en dashes from generated text.

    The house style rule is that they read as AI-written prose and are not
    the house tone. It applies to new writing, and a generated document is new
    writing however old the sentence it quotes, so this is where an inherited one
    is caught rather than in the document it came from. A range between numbers
    becomes "to", anything else becomes a comma.
    """
    text = DASH_RANGE.sub(r"\1 to \2", text)
    return DASH_CLAUSE.sub(", ", text)


def canonical(name: str) -> str:
    """A filename reduced to its identity, so a reference survives a renumbering.

    A work package's batch number is reused and stripped when it is archived, so
    `wp-000-rollup.md` and `wp-rollup.md` are the same package and must compare
    equal. A backlog capture's priority prefix behaves the same way. A spec
    number is identity rather than scheduling, so it is kept.
    """
    name = PRIORITY_PREFIX.sub(r"\1", name)
    return BATCH_PREFIX.sub(r"\1-", name)


def parse_header(text: str) -> tuple[str, dict[str, str]]:
    """The H1 title and the bold-label fields of a document's header block.

    Two shapes occur in the repository and both are read: `**Status**: value`,
    and `**Status (2026-09-29 assessment): SHIPPED**`, where the colon sits
    inside the bold. Only the first value for a label is kept, since several
    documents carry a later dated restatement below the original.
    """
    title = ""
    fields: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not title and stripped.startswith("# "):
            title = stripped[2:].strip()
            continue
        if stripped.startswith("## "):
            break
        match = HEADER_FIELD.match(stripped)
        if not match:
            continue
        label, value = match.group(1), match.group(2)
        if ":" in label:
            label, inner = label.split(":", 1)
            inner = inner.strip()
            # No space before a comma: the shape being read is
            # `**Status (...): SHIPPED**, by spec-024`, and a blind join put one
            # in front of every continuation that starts with punctuation.
            joiner = "" if value[:1] in ",.;:!?)" else " "
            value = (inner + joiner + value).strip() if inner else value.strip()
        label = re.sub(r"\(.*?\)", "", label).strip().lower().rstrip(":")
        if label and label not in fields:
            fields[label] = value.strip()
    return title, fields


# Opening clauses that say nothing a reader did not already know from the
# column the item is sitting in. Skipped so the summary shows the next clause,
# which is usually the one carrying the news.
BOILERPLATE_OPENERS = (
    "unnumbered backlog item",
    "backlog",
    "backlog item",
    "captured",
    "proposed",
    "draft",
)


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<!\bNo)(?<!\bSt)(?<=\.)\s+(?=[A-Z(\[])", text)
    return [p.strip() for p in parts if p.strip()]


def first_sentence(text: str, limit: int = 150) -> str:
    """One readable line of a status field, for the detail under an item.

    Skips a purely formal opening clause. A backlog capture whose status begins
    "Unnumbered backlog item." tells a reader nothing they cannot see from the
    lane it is in, and the sentence after it is the one worth the width.
    """
    text = re.sub(r"[*`\[\]]", "", text).strip()
    if not text:
        return ""
    parts = _sentences(text)
    while len(parts) > 1:
        head = parts[0].rstrip(".").strip().lower()
        if head in BOILERPLATE_OPENERS or head.startswith("unnumbered backlog item"):
            parts.pop(0)
            continue
        break
    out = parts[0] if parts else text
    if len(out) > limit:
        out = out[: limit - 3].rsplit(" ", 1)[0] + "..."
    return out


def real_gate(gate: str) -> str:
    """A gate line, or empty where it says there is no gate.

    A gate beginning "none" is an absence however the sentence continues, and
    several read "none. The policy is decided...", so an exact match on the word
    would have printed most of them.
    """
    cleaned = re.sub(r"[*`]", "", gate).strip()
    if not cleaned or re.match(r"^none\b", cleaned, re.IGNORECASE):
        return ""
    return cleaned


def classify(status: str, folder_state: str | None) -> str:
    """Where an item stands.

    The folder wins where it says anything, because a document's location is
    maintained by the archive skills and its prose is maintained by whoever last
    edited it. Keyword matching on prose is a fallback, not a source of truth,
    which is why the status line itself is also printed on the page: a
    misclassification is then visible rather than hidden.
    """
    if folder_state:
        return folder_state
    lowered = " " + status.lower()
    for words, state in (
        (_DROPPED_WORDS, DROPPED),
        (_PROGRESS_WORDS, IN_PROGRESS),
        (_WAITING_WORDS, WAITING),
        (_DONE_WORDS, DONE),
    ):
        if any(word in lowered for word in words):
            return state
    return OPEN


@dataclass
class Item:
    key: str
    kind: str
    title: str
    path: Path | None = None
    status_text: str = ""
    owner: str = ""
    gate: str = ""
    areas: list[str] = field(default_factory=list)
    marker: str = ""
    parent: str | None = None
    slice_of: tuple[int, int] | None = None
    state: str = OPEN
    epics: list[str] = field(default_factory=list)
    merged_pr: int | None = None
    merged_at: str = ""
    slices: list["Item"] = field(default_factory=list)

    @property
    def label(self) -> str:
        return self.title or self.key

    @property
    def filename(self) -> str:
        """What to print so the operator can see which file a row came from.

        The real name on disk, not the canonical one, since the point is to be
        able to open it. An issue prints its number.
        """
        return self.path.name if self.path is not None else self.key

    @property
    def summary(self) -> str:
        return first_sentence(self.status_text)

    @property
    def sort_key(self) -> tuple:
        return (STATE_ORDER.get(self.state, 9), self.key)


@dataclass
class Epic:
    key: str
    title: str
    sequence: int
    completes: str
    status_text: str
    gate: str
    members: list[str] = field(default_factory=list)
    issues: list[int] = field(default_factory=list)

    @property
    def is_gate(self) -> bool:
        return self.key.startswith("epic-gate-")


KIND_PREFIX = re.compile(
    r"^(?:backlog|feature|work package|epic|spec-\d+|fix|chore)\s*:\s*", re.IGNORECASE
)


def strip_kind_prefix(title: str) -> str:
    """Drop the "Feature:" or "Backlog:" that an H1 carries.

    The prefixes are not consistent across the folders (`Feature:`, `FEATURE:`,
    `Backlog:`, `Work package:`, `Spec-048:`), and in a lane already headed
    Features they are noise three ways at once.
    """
    return KIND_PREFIX.sub("", title.strip()).strip()


def parse_parent(value: str) -> tuple[str | None, tuple[int, int] | None]:
    """The parent filename and this slice's position, from a `**Parent**` line.

    Both come from the one line, because that is where `{{SKILL_PREFIX}}-split-feature` puts
    them. Reading a separate `**Slice**` field would have been a second contract
    nothing writes.
    """
    if not value:
        return None, None
    match = PARENT_FIELD.search(value)
    if not match:
        return None, None
    position = (
        (int(match.group(2)), int(match.group(3))) if match.group(2) else None
    )
    return canonical(match.group(1)), position


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _item_from_path(path: Path, kind: str, folder_state: str | None) -> Item:
    title, fields = parse_header(_read(path))
    status = fields.get("status", "")
    parent, slice_of = parse_parent(fields.get("parent", ""))
    return Item(
        key=canonical(path.name),
        kind=kind,
        title=strip_kind_prefix(title) or path.stem,
        path=path,
        status_text=status,
        owner=fields.get("owner", ""),
        gate=fields.get("gate", ""),
        areas=[a.strip() for a in fields.get("areas", "").split(",") if a.strip()],
        marker=fields.get("marker", ""),
        parent=parent,
        slice_of=slice_of,
        state=classify(status, folder_state),
    )


def load_items() -> dict[str, Item]:
    """Every feature document and work package, keyed by canonical filename."""
    items: dict[str, Item] = {}
    sources = (
        (FEATURES.glob("spec-*.md"), "feature", None),
        (FEATURES.glob("backlog/*.md"), "feature", None),
        (FEATURES.glob("done/*.md"), "feature", DONE),
        (FEATURES.glob("dropped/*.md"), "feature", DROPPED),
        (WORK_PACKAGES.glob("wp-*.md"), "work-package", None),
        (WORK_PACKAGES.glob("backlog/wp-*.md"), "work-package", None),
        (WORK_PACKAGES.glob("done/*.md"), "work-package", DONE),
    )
    for paths, kind, folder_state in sources:
        for path in sorted(paths):
            if path.name == "README.md":
                continue
            item = _item_from_path(path, kind, folder_state)
            items.setdefault(item.key, item)
    _attach_slices(items)
    return items


def _attach_slices(items: dict[str, Item]) -> None:
    """Hang each slice capture under its parent, in build order.

    The `**Parent**` and `**Slice**` fields are written by `{{SKILL_PREFIX}}-split-feature`.
    Until that skill has
    split something there are no slices, and this does nothing.
    """
    for item in items.values():
        if not item.parent:
            continue
        parent = items.get(item.parent)
        if parent is not None and parent is not item:
            parent.slices.append(item)
    for item in items.values():
        if item.slices:
            item.slices.sort(key=lambda s: (s.slice_of[0] if s.slice_of else 99, s.key))


def load_epics(items: dict[str, Item]) -> list[Epic]:
    """The epic sequence, and which items each one homes."""
    sequence = _epic_sequence()
    epics: list[Epic] = []
    for path in sorted(EPICS.glob("epic-*.md")):
        text = _read(path)
        title, fields = parse_header(text)
        members, issues = _epic_members(text)
        epic = Epic(
            key=path.name,
            title=re.sub(r"^Epic:\s*", "", title).strip() or path.stem,
            sequence=sequence.get(path.name, (99, ""))[0],
            completes=sequence.get(path.name, (99, ""))[1],
            status_text=fields.get("status", ""),
            gate=fields.get("gate", ""),
            members=[m for m in members if m in items],
            issues=issues,
        )
        epics.append(epic)
    epics.sort(key=lambda e: (e.sequence, e.key))
    for epic in epics:
        for key in epic.members:
            items[key].epics.append(epic.key)
    return epics


def _epic_sequence() -> dict[str, tuple[int, str]]:
    """Sequence number and the "completes" sentence, from the epics README table."""
    out: dict[str, tuple[int, str]] = {}
    readme = EPICS / "README.md"
    if not readme.exists():
        return out
    for line in _read(readme).splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or not cells[0].isdigit():
            continue
        match = DOC_REFERENCE.search(cells[1])
        if match:
            out[match.group(1)] = (int(cells[0]), cells[2])
    return out


def _epic_members(text: str) -> tuple[list[str], list[int]]:
    """References inside an epic's item sections, in the order the epic puts them.

    **Order is first appearance scanning the document top to bottom**, which is
    what makes this build order rather than an alphabetical accident. A gate
    epic's `## Sequence` section sits above its `## Items` table and says in
    terms that it is authoritative on ordering, so scanning in document order
    picks it up without this needing to know the section by name. An epic with
    no sequence section falls back to the order of its items table, which is
    also curated by a person.

    Sorting by state then filename instead would put items at the top of a
    gate that its sequence places last.
    """
    members: list[str] = []
    issues: list[int] = []
    collecting = False
    for line in text.splitlines():
        if line.startswith("## "):
            heading = line[3:].strip().lower()
            collecting = not any(heading.startswith(skip) for skip in NON_ITEM_SECTIONS)
            continue
        if not collecting:
            continue
        for match in DOC_REFERENCE.finditer(line):
            name = canonical(match.group(1))
            if not match.group(1).startswith("epic-") and name not in members:
                members.append(name)
        for match in ISSUE_REFERENCE.finditer(line):
            number = int(match.group(1))
            if number not in issues:
                issues.append(number)
    return members, issues


def attach_merges(items: dict[str, Item]) -> None:
    """The merge date and PR for each archived document, from git history.

    One `git log` over both archive folders rather than one per file. Rename
    detection is switched off deliberately: a `git mv` from the live folder to
    `done/` is the event being looked for, and with renames detected it would be
    reported as a modification at a path that no longer matters.
    """
    try:
        raw = subprocess.run(
            [
                "git", "-C", str(REPO), "log", "--diff-filter=A", "--no-renames",
                "--name-only", "--date=short", "--format=%x00%ad%x09%s",
                "--", "docs/features/done", "docs/work-packages/done",
            ],
            capture_output=True, text=True, check=True, timeout=60,
        ).stdout
    except (subprocess.SubprocessError, OSError):
        return

    for block in raw.split("\x00"):
        if not block.strip():
            continue
        head, _, body = block.partition("\n")
        date, _, subject = head.partition("\t")
        pr_match = re.search(r"\(#(\d+)\)\s*$", subject)
        for line in body.splitlines():
            key = canonical(Path(line.strip()).name)
            item = items.get(key)
            # git log runs newest first, so the first add seen is the live one.
            if item is not None and not item.merged_at:
                item.merged_at = date.strip()
                item.merged_pr = int(pr_match.group(1)) if pr_match else None


def load_issues(include: bool = True, limit: int = 300) -> list[Item]:
    """Open GitHub issues as the fix lane. Optional, and silent when gh cannot run."""
    if not include:
        return []
    try:
        raw = subprocess.run(
            [
                "gh", "issue", "list", "--state", "open", "--limit", str(limit),
                "--json", "number,title,labels,createdAt",
            ],
            capture_output=True, text=True, check=True, timeout=60, cwd=str(REPO),
        ).stdout
        payload = json.loads(raw)
    except (subprocess.SubprocessError, OSError, ValueError):
        return []

    issues = []
    for row in payload:
        labels = [label.get("name", "") for label in row.get("labels", [])]
        issues.append(
            Item(
                key="#%d" % row["number"],
                kind="issue",
                title=strip_kind_prefix(row.get("title", "")),
                status_text=", ".join(labels),
                areas=labels,
                state=IN_PROGRESS if "queue-for-agent" in labels else OPEN,
            )
        )
    issues.sort(key=lambda i: int(i.key[1:]))
    return issues


def _config() -> dict:
    """Optional project settings from `docs/epics/roadmap.json`."""
    try:
        return json.loads((EPICS / "roadmap.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


CONFIG = _config()

# Issue labels that place an issue in an epic, e.g. a batch label `wp-000` for
# the first gate, or `epic: <slug>`. Project data, so it lives in roadmap.json.
ISSUE_LABEL_EPIC: dict[str, str] = dict(CONFIG.get("issue_labels", {}))

# Epics drawn beside the main path rather than on it.
ALONGSIDE: set[str] = set(CONFIG.get("alongside", []))


def issue_epic(issue: "Item") -> str | None:
    for label in issue.areas:
        if label in ISSUE_LABEL_EPIC:
            return ISSUE_LABEL_EPIC[label]
    return None


@dataclass
class Roadmap:
    items: dict[str, Item]
    epics: list[Epic]
    issues: list[Item]

    def homed(self, epic: Epic) -> list[Item]:
        """The epic's items in the order the epic declares, not alphabetically."""
        return [self.items[k] for k in epic.members]

    def unhomed(self) -> list[Item]:
        return sorted(
            (i for i in self.items.values() if not i.epics and i.state not in (DONE, DROPPED)),
            key=lambda i: i.sort_key,
        )

    def multiply_homed(self) -> list[Item]:
        return sorted((i for i in self.items.values() if len(i.epics) > 1), key=lambda i: i.key)

    def completed(self) -> list[Item]:
        done = [i for i in self.items.values() if i.state == DONE]
        done.sort(key=lambda i: (i.merged_at or "0000-00-00", i.key), reverse=True)
        return done

    def issues_for(self, epic: Epic) -> list[Item]:
        """The open issues belonging to an epic.

        An issue's label decides its epic where it has one (from
        `issue_labels` in roadmap.json), so an
        issue mentioned in two epics' prose is still listed once. An issue with
        no such label falls back to the epics that mention it.
        """
        by_number = {int(i.key[1:]): i for i in self.issues}
        labelled = [i for i in self.issues if issue_epic(i) == epic.key]
        mentioned = [
            by_number[n] for n in epic.issues
            if n in by_number and issue_epic(by_number[n]) is None
        ]
        return mentioned + [i for i in labelled if i not in mentioned]


def load(include_issues: bool = True) -> Roadmap:
    items = load_items()
    epics = load_epics(items)
    attach_merges(items)
    return Roadmap(items=items, epics=epics, issues=load_issues(include_issues))
