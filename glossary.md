# Glossary

Canonical terminology for this project. The constitution (`.specify/memory/constitution.md`) and every spec use these terms as defined here. When a term changes, amend it here in the same pass as the documents that use it.

Each entry gives the term, its definition, and where relevant the schema name or the term it must not be confused with.

## Domain terms

[Add product terms here as the constitution is written.]

## Process terms

**Capture**: an unnumbered feature document in `docs/features/backlog/`, named `ft-<slug>.md`.

**Spec**: a numbered feature, `spec-NNN-<slug>.md` in `docs/features/`, with a matching `specs/NNN-<slug>/` spec-kit directory once `/speckit.specify` has run.

**Work package**: a unit of work that is not a feature (infrastructure, research, tooling, documentation), `wp-<slug>.md` in `docs/work-packages/`.

**Epic**: an index of every item that together completes one releasable outcome, `epic-<slug>.md` in `docs/epics/`.

**Batch number**: the `NNN` inside `ft-NNN-` or `wp-NNN-`, saying which set of work an item belongs to. Scheduling, not identity; stripped at promotion or archiving.

**Feature branch**: `feature/NNN-<slug>` or `feature/wp-<slug>`, cut from `main` at promotion; task branches target it and it merges into `main` once, as the release gate.

**Operator**: the person who owns the repository and makes the decisions skills surface.
