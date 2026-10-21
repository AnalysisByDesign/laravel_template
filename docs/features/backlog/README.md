# Backlog

**Location**: `docs/features/backlog/`

Unnumbered feature captures. Items here have been captured but not committed to a position in the build order.

## Why this folder exists

Allocating a spec number at capture time claims a position in the build order that has not been decided yet, and numbers handed out early get reassigned, collide and leave stale references behind. Capturing without a number removes the problem.

## Lifecycle

1. **`docs/features/backlog/`**: captured, unnumbered, no committed position in the build order. Filename is `ft-` plus a descriptive slug.
2. **`docs/features/`**: promoted by `{{SKILL_PREFIX}}-promote-backlog-spec`, which runs the product owner check first. A number is allocated at promotion (confirmed against the repository, not a manifest), the `ft-` prefix is swapped for it so the file becomes `spec-NNN-*.md`, a `feature/NNN-<slug>` branch is cut from `main`, and the spec goes through `/speckit.specify`.
3. **`docs/features/done/`**: shipped, archived by `{{SKILL_PREFIX}}-archive-spec`.

Backlog items have no matching `specs/NNN-*/` spec-kit directory. Only numbered items do.

## Conventions

- Filenames carry an `ft-` prefix and a descriptive slug, no number. The prefix states what the document is: `ft-` a feature capture, `wp-` a work package, `spec-` something ready for action, `epic-` an epic.
- **A batch number may follow the prefix**: `ft-NNN-<slug>.md`, matching the work package batches. A sequence letter may follow the number where the order is clear (`ft-002a-`). The number is scheduling, not identity: it comes off at promotion, and the duplicate guard and the roadmap strip it before comparing.
- Capture date lives in the status line, not the filename.
- **Every item carries a `**Single user-visible outcome**:` line** near the top, before the first heading. It is the field that catches a sprawling capture at the moment it is written.
- **If the outcome line needs an "and" joining two different things a different person would notice, the item is two items.** Combining two backlog items at promotion is trivial; splitting one that has grown is not.
- Status line reads `Unnumbered backlog item`, so a stale header can never imply a number that was never allocated.
- Every item carries an `**Areas**:` line from `docs/features/areas.json`, and a `blocker` or `candidate` marker.
- **An oversize item is split by the `{{SKILL_PREFIX}}-split-feature` skill, at promotion.** The original stays under its own filename as the **parent**, restated with a `**Slices** (build order):` numbered list of its slices' filenames, and is never promoted itself. Each slice is an ordinary `ft-` capture carrying `**Parent**: \`ft-<parent>.md\`, slice <n> of <m>.` The link lives in the files, so the roadmap reads real artefacts; `tools/docs-guard/check_splits.py` fails CI if the two sides disagree.

## Epics

Every item here is homed in exactly one epic under `docs/epics/`. When an item is added, promoted or dropped, its epic row moves with it.

## Current contents

0 items indexed. Keep the count and the table in step whenever a file is added, promoted or dropped.

Items with a batch number (`ft-NNN-`) sort together by it. Everything else is alphabetical and carries no implied priority. **The phase column repeats what each file declares, nothing more**; phase membership is decided at the `{{SKILL_PREFIX}}-review-backlog` ceremony.

| File | One line | Phase (as declared) | Origin |
| --- | --- | --- | --- |

### Pairs and chains worth knowing about

Items that only make sense read together. Each file states its own dependency; this is the map.

### Numbers released to the pool

None yet. Reuse rules are in `docs/features/README.md`.
