# Ceremonies

**Location**: `docs/ceremonies/`

Dated records of ceremonies run against the project. One file per run, named `YYYY-MM-DD-<ceremony>.md`.

## What a ceremony is

A ceremony is a skill that runs a defined process, knows where the project currently stands, **surfaces decisions for the operator rather than making them**, and leaves a dated record of what was decided.

The record is what separates a ceremony from a tool. A ceremony's output is the decision trail: what was considered, what was chosen, what was deliberately deferred and why. A deliberate deferral is a decision, and it reads very differently from an item nobody reached.

## The ceremonies

| Ceremony | Skill | What it decides |
| --- | --- | --- |
| Backlog review | `{{SKILL_PREFIX}}-review-backlog` | What enters a phase. Walks `docs/features/backlog/` against a named phase, one item at a time, and promotes the accepted items into numbered specs. |
| Product owner check | `{{SKILL_PREFIX}}-po-check`, and inside `{{SKILL_PREFIX}}-promote-backlog-spec` | Whether promoting one item now is consistent with the roadmap, the live batches and the constitution. Pushes back, never refuses; a `proceed` over a challenge needs the operator's written reason and lands in `po-overrides.md`, the one append-only record in this folder that spans runs. |

## Reading a record

Each record names the mode it ran in, the phase it ran against, every item considered with the decision taken, the spec numbers allocated, and any coherence findings with how they were resolved. Anything left unresolved is stated as unresolved rather than quietly dropped.

The phase document a ceremony edited carries a one-line pointer back to the record, so the history is findable from the thing it changed.
