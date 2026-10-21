<!-- Template constitution. Generic engineering principles are carried over as working drafts;
     product principles are placeholders to fill in during /speckit.constitution for the project
     created from this template. Nothing here is ratified until the version header says so. -->

# {{APP_NAME}}: Constitution

**Version**: 0.1.0 | **Ratified**: UNRATIFIED | **Last Amended**: 2026-10-21

## Product Summary

{{APP_DESCRIPTION}}

[PRODUCT_SUMMARY: expand into one paragraph on what the product is, who it serves, and the first customer or reference user it is proved against.]

Full background and commercial rationale: `[project-description-and-context.md]`. Feature build order: `docs/roadmap/`. Component-level rationale for every principle below: `docs/decisions/`.

## Core Principles

Principles marked **(PRODUCT)** are placeholders. Replace each with the product's own non-negotiable rules, or delete it, before ratifying. The generic principles are working drafts carried from the source project; keep, amend or strike each one at ratification.

### I. [PRODUCT PRINCIPLE: data isolation / ownership boundary] (PRODUCT)

[State the hierarchy or ownership boundary every query must respect, how it is enforced (for example a global Eloquent scope rather than manual `where()` clauses), and the test every feature must carry to prove it. Breaching it should be a P0 defect.]

### II. Test-First (NON-NEGOTIABLE)

TDD mandatory: Red-Green-Refactor, Pest only, never PHPUnit syntax. A test is written, confirmed failing, then the implementation follows.

Priority order (highest first): [PRIORITY_ORDER, for example money movement > core user journey > state transitions > isolation > admin experience > everything else].

Coverage targets (CI-enforced): [TIERED_TARGETS, for example ~100% for money/transactional logic, ~90% for state and isolation, ~80% for user-facing features, ~70% baseline]. The coverage gate blocks merge below threshold but is overridable by the repository owner only, and the override is logged.

### III. [PRODUCT PRINCIPLE: single source of truth for core state] (PRODUCT)

[If the product has a lifecycle or state machine, state that every transition goes through one service class, is logged with actor and timestamp, and that side effects hang off transition events rather than controllers or components. A side-effect failure never rolls back the transition. Delete if not applicable.]

### IV. Business Logic in Service Classes

Calculation, pricing, validation-beyond-shape, and state-transition logic lives in plain PHP service classes, server-side. Livewire components and controllers render and delegate; they contain no business logic.

Limits, defaults, tier rules and pricing live in `config/` or settings tables, never hardcoded in components. Secrets never live in settings tables. Caching is deliberately conservative: no speculative business-data caching without a recorded decision.

### V. [PRODUCT PRINCIPLE: money safety] (PRODUCT)

[If the product handles money: storage unit (for example integer minor units), currency scope, payment provider model, idempotent webhook handling by event ID, refund authority and audit trail. Delete if not applicable.]

### VI. Degrade Gracefully

A failing dependency (mail, queue, third-party API, device) never blocks the primary user journey. Side effects are queued jobs with retry and are independently retriable. Failures are surfaced to the person who can act on them, not swallowed.

### VII. Internationalisation and Prose Style (NON-NEGOTIABLE)

All UI display strings go through Laravel localisation (`lang/`, `__()`) from day 1, never hardcoded. English is the default; adding a locale is a lang-file change.

Zero em dashes or en dashes in anything user-facing (lang files, views, emails, marketing copy), enforced by a Pest guard test that scans `lang/` and `resources/views/`. Applies to all new writing, including docs and code comments.

### VIII. Data Architecture and Sensitive Data

[Working draft, keep or strike at ratification.] Every table has its own primary key: a UUID v7 generated in PHP before insert, never an auto-increment, never a foreign key doubling as a primary key. Every table carries `created_at`, `updated_at`, `deleted_at`. Referential integrity is enforced at the database level.

Sensitive data (credentials, secrets, PII) lives in a dedicated `<entity>_sensitive` companion table, reached only through the Eloquent relationship, encrypted application-side, and never appears in any export or log.

### IX. Security by Process

Security posture follows published guidance ([AUTHORITY, for example NCSC or OWASP ASVS]) checked at implementation time, never invented in-house or hardcoded from memory. Every change gets a security review before merge; input safety is enforced by tests rather than by reviewer attention; secrets scanning runs on every commit (gitleaks) and in CI. Dependencies are kept current by Dependabot and reviewed, not auto-merged.

## Governance

This constitution supersedes ad-hoc practice and agent improvisation. Where a spec, plan, or code conflicts with a principle, the principle wins until formally amended.

**Amendment procedure.** An amendment requires, together: a version bump (semver-style, `0.x.0` pre-ratification, `1.0.0` at ratification), a dated entry in `.specify/memory/constitution-changelog.md`, a drift check confirming `docs/features/`, `docs/decisions/`, and `CLAUDE.md` don't silently violate the change (reconcile in the same pass or log explicitly as "downstream to reconcile"), and this document's version header updated.

**Compliance checks.** All plans and PRs must verify compliance explicitly with every NON-NEGOTIABLE principle and with [LIST the product principles every feature is most likely to touch]. Anything touching [HIGH_RISK_AREAS, for example payments, isolation middleware, the state machine, or a database migration] requires operator review of the plan before implementation begins. Complexity beyond what a feature's spec demands must be justified in the plan or removed.

**Scope discipline.** The deferred and out-of-scope list in the roadmap is binding, not advisory: deferred items get no code paths or speculative schema beyond stated "must not preclude" allowances. Build order must always leave a functional, deployable product at the end of each phase.

**Document structure.** This file holds only binding principles and governance. Component-level rationale lives in `docs/decisions/` (ADRs, one per component). Feature-level build content lives in `docs/features/`. Terminology reference: `glossary.md`.

## Amendment Log

From ratification onward each amendment is listed here, newest first, per the amendment procedure.

**0.1.0, 2026-10-21: Template baseline.** Generic engineering principles carried from the source project as working drafts; product principles left as placeholders. Not ratified.
