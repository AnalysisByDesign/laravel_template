# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A Laravel 13 / PHP 8.5 project template carrying a full delivery process: spec-kit for feature work, a feature-branch model enforced by hooks and CI, release-please releases, release-gated SSM deploys, and project skills (`tpl-*`) that run the lifecycle. It contains no product code. Placeholders still to fill when a project is created from it: the product summary and the `(PRODUCT)` principles in `.specify/memory/constitution.md`, `docs/features/roadmap.md`, the compose project name and port suffix (`laravel/compose.yaml`, `laravel/.env.example`), and the GitHub secrets and variables listed at the top of `.github/workflows/deploy.yml`.

## Read order for a new session

1. This file.
2. `.specify/memory/constitution.md`: principles; a violation is P0. Unratified at 0.1.0 until the product principles are written.
3. `docs/features/roadmap.md`: phased build order.
4. `docs/development/agent-orchestration.md`: which model and subagent runs each spec-kit phase. Read before running any phase.
5. The current codebase. Never assume structure from memory.

## Layout

The Laravel app lives only in `laravel/`, never at the repo root (`docs/decisions/0001-repository-layout.md`). Everything else is process tooling: `specs/` (spec-kit output, one directory per spec, `done/` when shipped), `docs/` (features, work packages, decisions, runbooks, ceremonies, sessions), `.specify/` (spec-kit config, templates, constitution), `.claude/` (agents, skills, permissions), `tools/` (Python and PHP helpers used by skills and CI), `scripts/deploy/`, `.githooks/`, `.github/`.

## Commands

All `make` targets run from the repo root and wrap `laravel/vendor/bin/sail`. Use them rather than calling Sail directly.

- Containers: `make up`, `make down`, `make restart`, `make logs`, `make shell`. `make dev` runs Vite and the queue listener. `make build` is the production asset build.
- Tests (Pest only, never PHPUnit syntax):
  - Single file or filter: `make test ARGS="tests/Feature/FooTest.php"` or `make test ARGS="--filter=name"` (one process, `testing` database).
  - Whole suite: `make test` (parallel, one database per worker; `make test-db-grant` once per MySQL volume first). Also `test-serial`, `test-branch` (files changed since `main`), `test-coverage` (70% floor).
- Quality: `make lint` (Pint check), `make pint` (fix), `make stan` (Larastan, level 6).
- Other: `make artisan cmd="..."`, `make migrate`, `make tinker`, `make mysql`, `make env-sync` (adds `.env.example` keys missing from `laravel/.env`).
- Docs guards (host, not Sail): `python3 tools/docs-guard/check_areas.py --require-tags` and the other `check_*.py` beside it; unit tests via `python3 -m unittest` in `tools/docs-guard`, `tools/po-check`, `tools/roadmap`.
- Production-side helpers are in `Makefile.ops`; every host and path in it is a placeholder.

**Local test running is narrow on purpose.** Locally, run only the single test file a task touches (red once, then green once) plus `make lint` and `make stan`. CI on the PR is the test gate. Do not run `make test`, `make test-branch` or a broad `--filter` on your own initiative; the exception is reproducing a CI failure in order to fix it.

**The dev stack is the operator's.** Never run `make up`, `make dev`, `make down` or `make restart`. If a change may have left it stale (merge, branch switch, dependency bump), say a bounce is needed, and whether a migration is needed with it.

**Never run a destructive database command** (`migrate:fresh`, `migrate:refresh`, `migrate:reset`, `db:wipe`, `make fresh`, `TRUNCATE`, unscoped `DELETE`) without the operator's explicit say-so for that command; most are also denied in `.claude/settings.json`. Plain `migrate` is the operator's too, except inside `tpl-sync-local` after an explicit yes.

## Process: spec-kit

Per feature: `/speckit.specify` → `clarify` → `plan` → `tasks` → `analyze` → `implement` → `checklist` → `converge`. The last two are mandatory; a spec is finished when `converge` finds nothing unbuilt. Specs say what and why, never the tech stack. Resolve every `[NEEDS CLARIFICATION]` before planning.

- Captured intent goes in `docs/features/backlog/ft-<slug>.md`, unnumbered. `tpl-split-feature` right-sizes it; `tpl-promote-backlog-spec` runs the product-owner check, allocates `spec-NNN`, and cuts and pushes `feature/NNN-<slug>` from `main`.
- The spec a command acts on is `.specify/feature.json` (gitignored, per machine), not the branch. Change it with `tpl-switch-feature`. Setting `SPECIFY_FEATURE_DIRECTORY` writes back into that file rather than overriding it once.
- `/speckit.implement` delegates each task to the `implementer` subagent; `spec-reviewer` does the read-only conformance review before a PR.
- The git extension (`.specify/extensions.yml`) cuts the first task branch in `before_specify` and auto-commits each phase's artefacts. Its `after_specify` hook runs `tpl-session-name`, which prints a `/rename` command for the operator (a skill cannot rename the session). `tools/docs-guard/check_spec_hooks.py` fails CI if that hook is dropped.
- Work packages (`docs/work-packages/wp-<slug>.md`) cover non-spec work, promoted with `tpl-promote-wp` onto `feature/wp-<slug>`. Session briefs in `docs/sessions/` become captures, packages and issues through `tpl-review-session-notes`.
- Every document in `docs/features/` carries an `**Areas**:` line using the closed vocabulary in `docs/features/areas.json`; CI enforces it.

## Branching, CI and merge

- No direct pushes to `main`. `.githooks/pre-push` blocks them; activate hooks with `git config core.hooksPath .githooks` after cloning. Never use `ALLOW_MAIN_PUSH=1` or `--no-verify`.
- A feature branch per spec or work package; task branches come off it, and their PRs target it. The feature branch merges into `main` once, as the release gate. Fixes use `tpl-fix-branch`, which asks which feature branch they belong to (or `main`).
- CI (`.github/workflows/ci.yml`): `checks` is the required status. On a PR into `feature/*` it runs only per-file checks on changed files (Pint, audits when a lockfile changed, docs-guard, shell-lint); any other PR gets the full set, including Larastan. It skips on draft PRs. `pest` is opt-in via the `run-pest` label, and mandatory with no label on `feature/*` → `main`, `fix/*` → `main` and the release PR; it has a 70% merged coverage floor.
- Open finished work as ready for review, not draft: a draft with no label runs nothing and looks green. Don't add `run-pest` when opening a PR; it reruns the full suite on every push.
- Merges go through `tpl-merge`: a command-checked gate, squash-merge on the operator's confirmation, `tpl-sync-local`, regeneration of `docs/roadmap/` and `docs/reference.md` from post-merge `main`, then a documentation-only follow-up PR. Never rebase or force-push a pushed branch; merge the target in only for a reason.
- **Never launch `/code-review`.** The operator triggers it. When preparing a PR, report it as an outstanding gate.

## Releases and deploys

Commit messages and PR titles follow Conventional Commits, because release-please parses the squash subject. Pre-1.0, `feat` and `fix` both bump patch and a breaking change bumps minor. Never hand-edit `CHANGELOG.md`. Merging the release-please PR publishes a release, and that publish triggers `deploy.yml` (SSM Run Command via `scripts/deploy/trigger.sh`, then `verify.sh`). Roll back by dispatching `deploy.yml` with the previous tag (`docs/runbooks/rollback.md`).

## Tech conventions

- Prefer Laravel built-ins over third-party packages.
- Business logic lives in plain PHP service classes; controllers and components render and delegate.
- Limits, defaults and rules live in `config/`, never hardcoded.
- All UI strings go through `__()` and `lang/`.
- No em or en dashes in user-facing text, and keep them to a minimum everywhere else.
- `tests/Arch/BaselineArchTest.php` forbids debug calls (`dd`, `dump`, `ray` and the like) and requires the `Controller` suffix.

## Security

- Review each code change for injection, unescaped output (`{!! !!}`), mass assignment, missing authorisation, and unvalidated input reaching a query or path. Scope the review to the changed files plus one hop of collaborators.
- CI audits (`composer audit`, `npm audit`) gate on runtime dependencies and only report on dev ones.
- Dependabot version updates point at `/laravel`, not the root.
- gitleaks runs from the global `~/.git-hooks` chain.

## Generated files: regenerate, never hand-edit

- `docs/reference.md` and `docs/claude-transfer/`: run `tpl-prepare-docs-reference` on `main`. `docs/claude-transfer/` holds symlinks built from `members.txt`; never edit through them, and leave them out of repo-wide sweeps.
- `docs/roadmap/`: run `python3 tools/roadmap/build.py`.
- `CHANGELOG.md`: written by release-please.
