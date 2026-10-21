# Epics

**Location**: `docs/epics/`

## What an epic is

An epic is an index: a short document naming, by filename or issue number, every feature capture, spec, work package and issue that together complete one releasable outcome, with a status per line and no detail of its own. The detail lives in the named documents, once. An epic exists so "what is left before this is releasable" has one answer, not a search across four folders.

| Level | Held in | Example |
| --- | --- | --- |
| Epic | `docs/epics/epic-<slug>.md` | The first release |
| Feature or spec | `docs/features/backlog/ft-*.md`, `docs/features/spec-NNN-*.md` | `ft-example.md` |
| Story or task | `specs/NNN-*/tasks.md`, GitHub issues | T012 |
| Work package | `docs/work-packages/wp-*.md` | `wp-example.md` |

A work package is not below a feature; it sits beside one, because plenty of an epic's work never becomes a spec. Both hang off the epic.

**Each epic ends in a releasable product.** An item belongs in an epic if the epic is not releasable without it; an item that merely improves the same area goes in the "Related, homed elsewhere" list instead.

**Every item has exactly one home.** An item may be mentioned in several epics but is listed in the item sections of only one. That is what makes the folder countable.

## The epics, in sequence

The sequence is the intended order of completion. It is not encoded in the filenames, because a sequence changes and a filename should not. `tools/roadmap/build.py` reads this table: keep the first column a bare number and the second a backticked filename.

| Sequence | Epic | Completes | Items homed here |
| --- | --- | --- | --- |
| 1 | `epic-uncategorised.md` | What fits no other epic. Kept short on purpose. | 0 |

## Conventions

- Filename `epic-<slug>.md`, no number. A gate epic is named `epic-gate-<slug>.md`.
- Status, owner and gate lines near the top, before the first heading, as `docs/work-packages/README.md` requires of every work package.
- The items table has four columns: item, kind, where it stands, why it is here. "Where it stands" repeats what the item's own document declares, nothing more.
- Sections that describe the epic rather than home items use these headings, which the roadmap generator skips: "Why this epic exists", "Related, homed elsewhere", "Gaps", "Done when". Every other `##` section is read as holding items.
- No em dashes or en dashes anywhere in this folder.

## Keeping it current

- When a backlog item is promoted, archived, demoted or dropped, edit its row in the one epic that homes it. The skills that move feature documents rewrite the filename; the status column they do not.
- When a new capture is added to the backlog, give it a row somewhere, even if that is `epic-uncategorised.md`.
- Before a release review, count: every backlog file, every live `wp-*.md`, every numbered spec and every open issue should match exactly one row across the folder. The roadmap generator reports items homed in none or in more than one.
