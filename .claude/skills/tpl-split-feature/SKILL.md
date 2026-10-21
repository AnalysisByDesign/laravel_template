---
name: tpl-split-feature
description: Right-size one backlog feature capture before it is promoted. Lists the capabilities in it, tests each for whether it can ship on its own, and proposes either an ordered split into independently shippable slices or keeping it whole, with reasons. Writes nothing until the operator approves; on approval writes each slice as its own linked ft- capture and restates the original as their parent. Never runs spec-kit.
compatibility: Requires docs/features/backlog/ and the conventions in its README; the split links are checked by tools/docs-guard/check_splits.py
metadata:
  author: laravel-template
---

# Split a Feature Capture

A narrated capture often arrives as one large piece of work. Handed to spec-kit as it is, it becomes a spec of five or six interlocked stories with no partial progress, which cannot be held in working memory across two machines. This skill right-sizes a capture before `/speckit.specify` ever sees it.



**It proposes and never acts.** Every split is the operator's call, made on the proposal. **Keeping a feature whole is a first-class outcome**, not a failure to find a split: an honest "these parts are welded" is worth as much as a clean cut.

**Input**: one backlog item, by slug or filename. `ft-`, a batch number and `.md` are all optional.

**It is standalone and does not know who called it.** It runs at promotion: from `tpl-promote-backlog-spec` before an item gets a number, and from `tpl-review-backlog` when the operator accepts an item into a phase. Called directly, it behaves the same.

## 1. Preconditions

Stop and change nothing if any fails.

1. **Clean working tree**, unless the caller is the backlog ceremony, which manages that itself.
2. **Exactly one backlog item matches** in `docs/features/backlog/`.
3. **It is not already a parent** (it carries a `**Slices**` list). A parent is never split again or promoted; its slices are.
4. **A slice may be split further.** Say so in the proposal, since it makes the parent's list longer, and treat the slice's own parent as the parent of the new pieces rather than nesting a second level.

## 2. The test

Read the whole capture. List every distinct capability in it: something an end user, a customer or the operator would notice is there or not. Then put one question to each:

**Can this ship to a customer on its own, or does it only make sense alongside the others?**

A capability can stand alone when it could be released in a different order from the others without being useless. Three things look like splits and are not, and the proposal says so when it meets one:

- **A chain where each link is worthless alone.** A VAT receipt without VAT rates prints nothing.
- **A feature and its own test obligation.** A role and the permission matrix tests that prove it are one piece of work (Principle X).
- **A capability and its fallback.** The fallback is what makes the capability safe to ship.

Group the capabilities into the smallest independently shippable features, and order them so each slice builds on only those before it. If that grouping leaves one group, the outcome is **keep whole**.

## 3. Propose

Output exactly this shape and nothing before it:

```
Capabilities in ft-<slug>.md
  1. <capability>: stands alone | only with <n>
  2. ...

Proposal: split into <k> | keep whole
  1. ft-<new-slug>.md  (capabilities 1, 3)  <why this is one slice, one line>
  2. ft-<new-slug>.md  (capabilities 2)     <why, and what it builds on>
  Ties: <what holds the slices together, one line>

  (or, for keep whole)
  Welded because: <why the parts cannot ship apart, one or two lines>
```

Then ask with `AskUserQuestion`: **approve**, **adjust** (the operator says what to change; re-propose), or **keep whole**. On keep whole, or on a keep whole proposal accepted, write nothing and stop.

On approval, also confirm two things the files will carry, offering the parent's values as the default: each slice's **marker** (a blocker parent's slices are not all automatically blockers) and **areas** (from the closed vocabulary in `docs/features/areas.json`, never coined).

## 4. Write, on approval only

### Each slice: `docs/features/backlog/ft-<new-slug>.md`

A slice takes its parent's batch number (`ft-NNN-`) if the parent has one; otherwise none, since that is the operator's to add. The identity block follows `docs/features/backlog/README.md`, plus the parent line:

```markdown
# Backlog: <slice title>

**Status**: Unnumbered backlog item. Split out of `ft-<parent>.md` on <today> by `tpl-split-feature`. Originally captured <parent's capture date> (<the parent's originating session brief path, or "no session brief recorded">).

**Areas**: <tags>

**Marker**: <as confirmed>

**Parent**: `ft-<parent>.md`, slice <n> of <m>.

**Single user-visible outcome**: <one thing, no "and" joining two different things>

**Epic**: <the parent's epic line, if it has one>
```

The body is the parent's substance for these capabilities, **moved, not rewritten**. Keep the operator's phrasing; change only what separating the parts requires, such as a sentence that named the other half. Each slice states what it builds on (the earlier slice by filename) and what builds on it, on both sides, as the brief template requires of any dependency. Open questions and out of scope items go with the capability they concern.

### The parent: restated in place

Keep the filename, the H1, the areas, the marker, the epic line and the single user-visible outcome, which is still true of the whole. Replace the status line and the body:

```markdown
**Status**: Unnumbered backlog item, parent of a split made <today> by `tpl-split-feature`. **Not promotable**: promote its slices, in order. Originally captured <date> (<brief path, or none recorded>).

**Slices** (build order):
1. `ft-<slice-one>.md`
2. `ft-<slice-two>.md`

## What ties the slices together

<the Ties line, expanded only as far as the proposal did>

## Build order

<why this order, one line per slice>
```

The original body is not kept: its substance now lives in the slices, and the text before the split is in git history. Two copies of one capture is the shadow-archive problem.

**The link format is load-bearing.** `**Slices** (build order):` followed by a numbered list of backticked filenames, and `**Parent**: \`<file>\`, slice <n> of <m>.` on each slice, are what the roadmap generator (`tools/roadmap/build.py`) reads and what `tools/docs-guard/check_splits.py` holds consistent in CI. Filenames, never item numbers or titles. When a slice is later promoted, `tpl-promote-backlog-spec` rewrites the filename in the parent's list like any other reference, and the guard resolves both forms.

### Indexes

- **`docs/features/backlog/README.md`**, "Current contents": restate the parent's row (`Parent of <m> slices, not promotable.` plus its outcome), add a row per slice in the usual alphabetical place, and update the item count.
- **The parent's epic** (find it with `grep -rln "ft-<parent>" docs/epics`): add each slice to the same epic's items table directly beneath the parent's row. Every backlog file has exactly one epic home, and slices inherit the parent's.

Then run `python3 tools/docs-guard/check_splits.py` and `python3 tools/docs-guard/check_areas.py --require-tags` from the repository root. Both must pass before reporting.

## 5. Stage and report

Stage, do not commit. Report, briefly:

- The outcome: split into which files, in what order, or kept whole and why.
- Each file written or restated, and each index row touched.
- The markers and areas chosen, if they differ from the parent's.
- That `docs/reference.md` is now stale; suggest the `tpl-prepare-docs-reference` skill.

## A false seam is ordinary development

Slices are built in sequence by one developer. A slice task that depends on something out of sequence is the signal the seam was drawn in the wrong place. **Resolve it in development**: refactor the earlier slice with the new information, or pull a task or two forward from the next slice. No re-split, no machinery; both are acceptable by the operator's ruling of 2026-10-05.

## Out of scope

- Running any spec-kit command, or allocating a spec number.
- Recombining slices after spec-kit has run.
- Splitting a numbered spec, a work package or an issue. Backlog captures only.
- Changing how captures are written during sessions.
- Deciding the phase any slice belongs to.
- Retiring a parent whose slices have all shipped. That is a later decision, not yet made.
- Committing, pushing or opening a pull request.
