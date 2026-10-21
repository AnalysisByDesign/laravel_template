# Features

**Location**: `docs/features/`

Feature specifications. This folder is the live working view: numbered specs that are ready for action, in flight, or awaiting their turn.

## The four states a feature can be in

| Folder | What it holds | Filename |
| --- | --- | --- |
| `docs/features/backlog/` | Captured intent, no committed position in the build order | `ft-<slug>.md` |
| `docs/features/` (this folder) | Numbered, ready for action or in flight | `spec-NNN-<slug>.md` |
| `docs/features/done/` | Shipped | `spec-NNN-<slug>.md` |
| `docs/features/dropped/` | Abandoned, kept for the reasoning | `spec-NNN-<slug>.md` or a descriptive name |

Movement between them is not a bare `git mv`. Three skills cross these boundaries, one direction each: `{{SKILL_PREFIX}}-promote-backlog-spec` brings a captured item into the live view and allocates its number, `{{SKILL_PREFIX}}-demote-active-spec` sends an unstarted spec back to the backlog and releases its number, and `{{SKILL_PREFIX}}-archive-spec` moves a shipped spec into `done/`. All three rewrite every reference across the repository, which is the part that is tedious to do by hand and easy to do incompletely.

The demotion direction is the one to read before using: taking a number away means every bare `spec-NNN` in the repository has to be classified rather than swept, which is why it is a skill of its own rather than a flag on the promotion one.

## Header block

Every spec, seed and backlog capture carries these lines near the top, before the first second-level heading:

- `**Status**:` where it stands.
- `**Areas**: tag, tag` from the closed vocabulary in `areas.json`. A tag not in it, or a document with no line, fails the `docs-guard` CI job (`python3 tools/docs-guard/check_areas.py --require-tags`).
- `**Target branch**:` written by the promotion skill once a feature branch exists.

## Epics

Each numbered spec here, and each backlog item, is homed in exactly one epic under `docs/epics/`: the releasable outcome it serves. See `docs/epics/README.md`.

## Numbering

**A number claims a position in the build order.** That is the whole reason backlog items do not carry one, and the reason a number is not a permanent name.

**Allocate against the repository, never against a manifest.** Confirm the number is free in this folder, in `done/`, in `dropped/`, and against `specs/NNN-*/` directories and branch names. `docs/reference.md` is generated and can lag, so it is not an authority for this.

**A released number returns to the pool, and reusing one is the hazardous option.** When an item moves to the backlog its number is released, but prose written before the move still says `spec-NNN` and still means the previous holder. Prefer the next unused number. If you do reuse one, sweep for bare `spec-NNN` references first and rewrite them to name the item rather than the number.

### Currently free

`001` and upward.

### Reserved

| Number | Reserved for | Recorded |
| --- | --- | --- |

A reservation that lives only in a work package or a conversation is how numbers get allocated twice in good faith. This table is where a reservation becomes real, and it is the second thing to check after the repository sweep.
