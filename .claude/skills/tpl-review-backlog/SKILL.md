---
name: tpl-review-backlog
description: Run the backlog review ceremony. Walks docs/features/backlog/ against a named phase one item at a time, asks where each belongs, promotes the accepted ones into numbered specs, and writes a dated record. Full mode for phase planning, blockers-only for a quick post-merge sweep. Surfaces decisions rather than making them.
compatibility: Requires docs/features/backlog/, the phase documents in docs/features/, and the tpl-promote-backlog-spec skill for the promotion mechanics
metadata:
  author: laravel-template
---

# Backlog Review Ceremony

Phases are defined and features are captured, but nothing connects them. Features arrive whenever the idea does rather than when the phase they belong to is being planned, so the pool of unattached features grows and the phase documents drift. This ceremony is the missing intake step: the defined moment where the backlog meets the phase structure.


**This is a ceremony, not a tool.** A ceremony runs a defined process, knows where the project currently stands, surfaces decisions for the operator rather than making them, and leaves a dated record. The record is what makes the difference: if the project ever grows beyond one person, a ceremony can be run live in a call and its output is the minutes.

**The load-bearing constraint: never assign a feature to a phase.** Present each item alongside the phase scope and ask. That judgement is the operator's, and automating it is precisely how a backlog silently fills a phase nobody agreed to.

## Modes

- `tpl-review-backlog` runs a **full review**: every item in `docs/features/backlog/`. This is the phase planning mode and it takes as long as it takes.
- `tpl-review-backlog blockers` runs **blockers-only**: just the items marked `blocker`, asking where each attaches. Meant to run after a merge and finish in a couple of minutes. This is what gives a security concern dictated on a walk a home: captured as a blocker, picked up on the next sweep rather than lost.

Both modes run the same six steps and differ only in which items step 3 presents.

## 1. Orientation

Read `docs/features/roadmap.md` (its standing placement rules and build order) and any phase documents it names (`docs/features/phase-*.md`). Report where each phase stands: what has shipped, what is outstanding, and whether anything is in flight.

Propose a target phase, normally the next in sequence. The operator confirms or overrides. Do not proceed on the proposal alone.

## 2. Phase scope recap

Restate what the target phase currently commits to, taken from its own `## Scope` section rather than from memory or from the roadmap summary. The walk has to happen against what is written, because that is what will be edited at the end.

## 3. Backlog walk

Present items **one at a time**, in filename order, which groups batched items (`ft-NNN-<slug>.md`) by their gate. For each, give a one-line summary, its marker, and any dependency it declares (backlog files cross-reference each other by `ft-` filename).

Ask where it belongs, with four options:

1. **The current phase**, the one already in flight.
2. **The target phase** being planned.
3. **A later phase**, naming which.
4. **Stay in the backlog.**

Four rather than three, because a feature may belong in the phase already in flight rather than the one being planned. Use `AskUserQuestion` so each answer is a deliberate choice rather than an inference from a conversational reply.

**Most items carry no marker.** As at 2026-09-02 only two of twenty-three do; the rest were captured before the blocker and candidate distinction existed. Treat an unmarked item as a candidate for filtering purposes, since nothing can be a blocker unless someone said so, but surface the absence during a full review so markers get backfilled as the walk goes. Blockers-only mode therefore sees only explicitly marked blockers, which is correct but worth stating in the report so a thin sweep is not mistaken for a clean one.

**When the operator places an item in the current or target phase, right-size it before moving on**: run the `tpl-split-feature` skill on it. If they approve a split, the parent leaves the walk and its slices take its place, each asked about in order, starting with slice 1. A kept-whole item goes forward as it is. Promotion then skips the split step for anything that has been through it here. A slice task that later turns out to depend on something out of sequence marks a false seam: refactor or pull the task forward in development, not by re-splitting.

Record every answer as you go. A ceremony interrupted halfway should still be able to say what was decided.

## 4. Coherence check

With the selections made, and before anything moves, flag what does not hold together:

- **A feature depending on something assigned to a later phase.** Read the dependencies declared in each promoted item and check them against where their dependencies landed. The image safety and prompt refinement pair is the worked example: the classifier blocks the refinement, so refinement cannot land in an earlier phase than its blocker.
- **A phase that no longer leaves a deployable product at its end.** The constitution requires this, so a phase that has grown past it is a finding, not a detail.
- **A blocker whose target phase has already shipped.** It should not silently become a candidate, and it is not still blocking anything. Surface it and ask: re-attach to a later phase, promote it now as urgent, or reclassify with the reason recorded. Never resolve this one by inference.

Report findings and let the operator adjust before promotion. Nothing has moved yet at this point, which is the whole reason the check sits here.

## 5. Promotion

For each accepted item, follow the `tpl-promote-backlog-spec` skill rather than reimplementing it, including its product owner check (section 1b of that skill), which runs per item and records any override with a citation of this ceremony's record: allocate a number confirmed against the repository (never against `docs/reference.md`, which is generated and can lag), swap the `ft-` prefix, and any priority prefix ahead of it, for `spec-NNN-`, restate the document's identity block, and rewrite every reference across the repository.

Numbers are allocated **strictly sequentially**, in the order the operator accepted the items. Do not group related features onto adjacent numbers: a number is a position in the build order, not a grouping, and treating it as semantic is what produced the churn the unnumbered backlog exists to end.

**One caveat on reuse.** The `tpl-promote-backlog-spec` skill checks for a clean working tree, and it leaves its changes staged rather than committed. Promoting several items in one ceremony therefore cannot satisfy that precondition on every invocation. The clean-tree check belongs to the ceremony as a whole, run once at the start; the per-item promotions then run back to back against a deliberately dirty tree. Say so in the report so the deviation is visible rather than silent.

Then update the target phase document's `## Scope` section with the promoted items, and remove them from the "Current contents" table in `docs/features/backlog/README.md`.

Promotion stops at the feature document. It does not run `/speckit.specify` or create a `specs/NNN-*/` directory; that stays the operator's deliberate act.

## 6. Report

Write a dated record to `docs/ceremonies/YYYY-MM-DD-backlog-review.md`, and add a one-line pointer to it in the phase document that was edited, so the history sits next to what it describes without cluttering it.

The record states:

- The mode, the target phase, and who confirmed it.
- Every item walked, with the decision taken and, where one was given, the reason.
- The numbers allocated and to what.
- What stayed in the backlog, since a deliberate deferral is a decision and reads very differently from an item nobody reached.
- Every coherence finding and how it was resolved.
- Anything left unresolved.

Then stage everything (`git add`) but **do not commit**. The operator reviews the diff and commits themselves.

## Decisions settled when this was built

Five design questions and how they are resolved, kept here so the reasoning stays next to the behaviour:

- **The record lives in `docs/ceremonies/`**, dated, with a pointer line added to the phase document. The folder keeps phase documents clean, and the pointer keeps the history findable from what it describes. Ceremonies are a set rather than a one-off, so they need a home of their own.
- **Promotion stops at the feature document.** The conservative default the work package named.
- **Numbers are allocated strictly sequentially**, for the reason given in section 5.
- **A phase cannot be closed by this ceremony.** Closing a phase is a separate deliberate act, and folding it in here would mean a routine sweep could end a phase as a side effect.
- **A blocker whose phase has shipped is surfaced, never auto-resolved**, per section 4.

## Out of scope

- **Assigning a feature to a phase.** The ceremony asks. This is the constraint everything else protects.
- Editing the substance of a backlog feature. Promotion moves and renumbers; it does not rewrite. Elaboration is a separate ceremony.
- Creating backlog features. Capture happens through the `tpl-review-session-notes` skill or by hand.
- Deciding or reordering phase order. The ceremony proposes the next phase and accepts an override.
- Closing a phase.
- Deleting or archiving anything. Items not selected stay in the backlog untouched.
- Running `/speckit.specify` or creating spec-kit directories.
- Committing, pushing, or opening a pull request.
- Hand-editing `docs/reference.md`, which is generated by the `tpl-prepare-docs-reference` skill.
- Touching `docs/claude-transfer/`, whose entries are symlinks rebuilt from `members.txt` by the same skill.
