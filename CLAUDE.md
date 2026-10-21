# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

<!-- TEMPLATE-ONLY:START -->
## This repository is still the template

This is the Laravel template, not an application yet: `.laravel-app-initialised.json` does not exist. **Before any other work, run the `init-laravel-app` skill.** It asks for the app's name, slug, skill prefix, ports and domains, then replaces every placeholder, renames the `.claude/skills/{{SKILL_PREFIX}}-*` directories and writes `laravel/.env`. This block, and the one in `README.md`, is removed by init.

When changing the template itself, rather than an app built from it:

- The `{{NAME}}` placeholders are intentional. Never fill them in by hand. A new one goes into `PLACEHOLDERS` in `tools/init/placeholders.py`, or `init_app.py` refuses to run.
- A YAML value that starts with a placeholder must be quoted (`name: "{{SKILL_PREFIX}}-merge"`). Bare `{{` begins a YAML flow mapping.
- Placeholders have no spaces inside the braces, which keeps Blade's `{{ $x }}` and Actions' `${{ github.sha }}` out of the pattern.
- `python3 tools/init/check_placeholders.py` reports the count while the repo is a template, and fails an initialised repo that still has any.
- Tag each template release with the Laravel version it carries.
<!-- TEMPLATE-ONLY:END -->

## What this project is

**{{APP_NAME}}**: {{APP_DESCRIPTION}}

Repository: `{{GITHUB_OWNER}}/{{GITHUB_REPO}}`. Created from the Laravel template; the values it was initialised with are in `docs/initialisation.md`. The project's own Claude skills are `/{{SKILL_PREFIX}}-*`.

## Read order for a new session

1. This file.
2. `.specify/memory/constitution.md`: principles; a violation is P0. It stays unratified until the `(PRODUCT)` principles are written.
3. `docs/features/roadmap.md`: phased build order.
4. `docs/development/agent-orchestration.md`: which model and subagent runs each spec-kit phase. Read it before running any phase.
5. The current codebase. Never assume structure from memory.

## Rules

- **Always run `make test` before committing.** The whole suite has to be green. While working, run the file you're changing (`make test ARGS="tests/Feature/FooTest.php"`); the full run comes before the commit. `make lint` and `make stan` must pass too.
- **Never edit `laravel/.env.example` without running `make env-sync` afterwards**, and say which keys were added or changed, so every machine's `.env` follows it.
- **New ideas go through the feature or work-package process, never straight into code.**
  - Product functionality goes in a feature capture, `docs/features/backlog/ft-<slug>.md`.
  - Work around the product (infrastructure, tooling, research, docs) goes in a work package, `docs/work-packages/backlog/wp-<slug>.md`.
  - Promote either with `/{{SKILL_PREFIX}}-promote-backlog-spec` or `/{{SKILL_PREFIX}}-promote-wp` before building it.
- **Never read `laravel/.env` or print a value from it.** It holds the generated database passwords and `APP_KEY`, and `.claude/settings.json` denies reading it.
- **The dev stack is the operator's.** Never run `make up`, `make dev`, `make down` or `make restart`. When a change may have left the stack stale (a merge, branch switch or dependency bump), say a bounce is needed, and whether a migration is needed with it.
- **Never run a destructive database command.** That means `make fresh`, `make restore`, `migrate:fresh`, `migrate:refresh`, `migrate:reset`, `db:wipe`, `TRUNCATE` or an unscoped `DELETE`. `make fresh` and `make restore` need a person to type `yes` at a terminal and are denied in `.claude/settings.json`. Plain `migrate` is the operator's too, except inside `/{{SKILL_PREFIX}}-sync-local` after an explicit yes.
- **Never launch `/code-review`.** The operator triggers it. When preparing a PR, report it as an outstanding gate.

## Layout

The Laravel app lives only in `laravel/`, never at the repo root (`docs/decisions/0001-repository-layout.md`). Everything else is process tooling:

- `specs/`: spec-kit output, one directory per spec, moved to `done/` when shipped.
- `docs/`: features, work packages, decisions, runbooks, ceremonies and sessions.
- `.specify/`: spec-kit config, templates and the constitution.
- `.claude/`: agents, skills and permissions.
- `tools/`: Python and PHP helpers used by the skills and CI.
- `scripts/`: `deploy/` for CI, `dev/` behind the Makefile.
- `.githooks/` and `.github/`.

## Commands

All `make` targets run from the repo root and wrap `laravel/vendor/bin/sail`. Use them rather than calling Sail directly. Run `make help` for the full list.

- **Health**: `make doctor`, a read-only check of the `Brewfile` tools, `laravel/.env`, git hooks, the containers and the read-only database user.
- **Host tools**: the root `Brewfile` (`brew bundle --file=Brewfile`) is the single list of what a Mac needs; `docs/runbooks/setup/mac-workstation.md` sets one up from nothing. A new required tool goes into both, in the same change.
- **Containers**: `make up`, `make down`, `make logs`, `make shell`.
  - `make dev` runs Vite and the queue listener. `make build` is the production asset build.
  - The app runs at http://localhost:8{{PORT_SUFFIX}}, and Caddy serves https://{{LOCAL_DOMAIN}}.
- **Tests** (Pest only, never PHPUnit syntax):
  - A single file or filter: `make test ARGS="tests/Feature/FooTest.php"` or `make test ARGS="--filter=name"` (one process, on the `testing` database).
  - The whole suite: `make test`, run in parallel with one database per worker. Run `make test-db-grant` once per MySQL volume first.
  - Also `test-serial`, `test-branch` (files changed since `main`) and `test-coverage` (70% floor).
- **Quality**: `make lint` (Pint check), `make pint` (fix), `make stan` (Larastan level 6).
- **Database**:
  - `make migrate`, `make tinker`, `make mysql`.
  - `make backup` writes a timestamped dump to `backups/`. `make restore` loads the newest, or `DUMP=<file>`.
  - `make fresh` takes a backup, then re-migrates and re-seeds. Restore and fresh both ask the operator for `yes`.
- **Environment**: `make env-sync` lines `laravel/.env` up with `.env.example`. `ARGS=--check` previews without writing.
- **Database accounts**:
  - `{{APP_SLUG}}_rw` is the application's user, with access to the `testing%` databases.
  - `{{APP_SLUG}}_ro` has `SELECT` on `{{APP_SLUG}}` only.
  - `root` is used only by backup, restore and `test-db-grant`.
  - The MySQL container creates all three on its first boot (`laravel/docker/mysql/`).
- **Docs guards**, run on the host rather than in Sail: `python3 tools/docs-guard/check_areas.py --require-tags`, the other `check_*.py` beside it, and `python3 tools/init/check_placeholders.py`. Unit tests: `python3 -m unittest` in `tools/docs-guard`, `tools/po-check`, `tools/roadmap` and `tools/init`.
- **Production helpers** are in `Makefile.ops`.

## Process: spec-kit

Each feature goes through `/speckit.specify`, then `clarify`, `plan`, `tasks`, `analyze`, `implement`, `checklist` and `converge`. The last two are mandatory, and a spec is finished only when `converge` finds nothing left unbuilt. Specs say what and why, never the tech stack. Resolve every `[NEEDS CLARIFICATION]` before planning.

- **Backlog**: captures are unnumbered. `/{{SKILL_PREFIX}}-split-feature` right-sizes one. `/{{SKILL_PREFIX}}-promote-backlog-spec` runs the product-owner check, allocates `spec-NNN`, and cuts and pushes `feature/NNN-<slug>` from `main`.
- **Which spec is active**: a command acts on `.specify/feature.json` (gitignored, per machine), not on the branch. Change it with `/{{SKILL_PREFIX}}-switch-feature`. Setting `SPECIFY_FEATURE_DIRECTORY` writes back into that file rather than overriding it once.
- **Implementation and review**: `/speckit.implement` delegates each task to the `implementer` subagent. `spec-reviewer` does the read-only conformance review before a PR.
- **Spec-kit hooks** (`.specify/extensions.yml`):
  - The git extension cuts the first task branch in `before_specify` and auto-commits each phase's artefacts.
  - The `after_specify` hook runs `/{{SKILL_PREFIX}}-session-name`, which prints a `/rename` command for the operator, since a skill cannot rename the session itself.
  - `tools/docs-guard/check_spec_hooks.py` fails CI if that hook is dropped.
- **Work packages and session briefs**: work packages are promoted with `/{{SKILL_PREFIX}}-promote-wp` onto `feature/wp-<slug>`. Session briefs in `docs/sessions/` become captures, work packages and issues through `/{{SKILL_PREFIX}}-review-session-notes`.
- **Areas**: every document in `docs/features/` carries an `**Areas**:` line from the closed vocabulary in `docs/features/areas.json`. CI enforces it.

## Branching, CI and merge

- **No direct pushes to `main`.** `.githooks/pre-push` blocks them. Activate the hooks after cloning with `git config core.hooksPath .githooks`. Never use `ALLOW_MAIN_PUSH=1` or `--no-verify`.
- **Branches**: each spec or work package gets a feature branch. Task branches come off it, and their PRs target it. The feature branch merges into `main` once, as the release gate. Fixes use `/{{SKILL_PREFIX}}-fix-branch`, which asks which feature branch they belong to, or `main`.
- **CI** (`.github/workflows/ci.yml`):
  - `checks` is the required status and skips on draft PRs.
  - On a PR into `feature/*` it runs only per-file checks on changed files: Pint, the audits when a lockfile changed, docs-guard and shell-lint.
  - Any other PR gets the full set, including Larastan.
  - `pest` is opt-in through the `run-pest` label. It's mandatory, with no label, on `feature/*` into `main`, `fix/*` into `main` and the release PR, and it has a 70% merged coverage floor.
- **Opening PRs**: open finished work as ready for review, not draft. A draft with no label runs nothing and looks green. Don't add `run-pest` when opening a PR; it reruns the full suite on every push.
- **Merging**: merges go through `/{{SKILL_PREFIX}}-merge`:
  1. A command-checked gate.
  2. A squash-merge on the operator's confirmation.
  3. `/{{SKILL_PREFIX}}-sync-local`.
  4. Regeneration of `docs/roadmap/` and `docs/reference.md` from post-merge `main`.
  5. A documentation-only follow-up PR.

  Never rebase or force-push a pushed branch. Merge the target in only for a reason.

## Releases and deploys

Commit messages and PR titles follow Conventional Commits, because release-please parses the squash subject. Before 1.0, `feat` and `fix` both bump the patch version, and a breaking change bumps the minor. Never hand-edit `CHANGELOG.md`.

Merging the release-please PR publishes a release, and that triggers `deploy.yml`: an SSM Run Command through `scripts/deploy/trigger.sh`, then `verify.sh` against https://{{PRODUCTION_DOMAIN}}. Roll back by dispatching `deploy.yml` with the previous tag (`docs/runbooks/rollback.md`).

## Tech conventions

- Prefer Laravel's built-in features over third-party packages.
- Business logic lives in plain PHP service classes. Controllers and components render and delegate.
- Limits, defaults and rules live in `config/`, never hardcoded.
- All UI strings go through `__()` and `lang/`.
- No em or en dashes in user-facing text, and keep them to a minimum everywhere else.
- `tests/Arch/BaselineArchTest.php` forbids debug calls (`dd`, `dump`, `ray` and the like) and requires the `Controller` suffix.

## Security

- **Per-change review**: check each code change for injection, unescaped output (`{!! !!}`), mass assignment, missing authorisation, and unvalidated input reaching a query or a file path. Scope the review to the changed files plus their direct collaborators.
- **Dependency audits**: the CI audits (`composer audit`, `npm audit`) gate on runtime dependencies and only report on development ones.
- **Dependabot**: version updates point at `/laravel`, not the repo root.
- **Secret scanning**: `.githooks/pre-commit` hands off to a global `~/.git-hooks/pre-commit` when one exists, and otherwise runs gitleaks itself. It fails closed if gitleaks is missing.

## Generated files: regenerate, never hand-edit

- **`docs/reference.md` and `docs/claude-transfer/`**: run `/{{SKILL_PREFIX}}-prepare-docs-reference` on `main`. `docs/claude-transfer/` holds symlinks built from `members.txt`, so never edit through them, and leave them out of repo-wide sweeps.
- **`docs/roadmap/`**: run `python3 tools/roadmap/build.py`.
- **`CHANGELOG.md`**: written by release-please.
- **`docs/initialisation.md` and `.laravel-app-initialised.json`**: written once by init.
