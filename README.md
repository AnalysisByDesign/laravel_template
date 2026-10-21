# laravel-template

Laravel 13 / PHP 8.5 starter with the delivery process built in: spec-kit, a feature-branch model, tiered CI, release-please and release-gated deploys. See `CLAUDE.md` for how the pieces fit together.

## Prerequisites

- PHP `^8.5` and Composer
- Docker, for Laravel Sail
- Node.js LTS and npm
- PlantUML (`brew install plantuml`), used by the pre-commit hook to render `.puml` diagrams
- gitleaks, run from your global `~/.git-hooks`
- Python 3, for `tools/`

## Starting a project from this template

1. Rename the compose project in `laravel/compose.yaml` and choose a port suffix in `laravel/.env.example`, so several projects can run side by side.
2. `cp laravel/.env.example laravel/.env` (or `make env-sync`), then `make up`. The first run builds the PHP 8.5 image.
3. `git config core.hooksPath .githooks`.
4. Write the product summary and the `(PRODUCT)` principles in `.specify/memory/constitution.md`, and fill in `docs/features/roadmap.md`.
5. Set the GitHub secrets and variables listed at the top of `.github/workflows/deploy.yml` and the two Claude workflows. Also create the `production` environment and the `run-pest` label, and import `.github/rulesets/main.json`.
6. After the first commit, run `python3 tools/roadmap/build.py --no-github` once to generate `docs/roadmap/`.

## Common commands

| Target | Effect |
| --- | --- |
| `make up` / `make down` | Start or stop Sail (app, MySQL, Redis, Caddy) |
| `make dev` | Vite and the queue listener |
| `make test ARGS="..."` | Pest; with no `ARGS`, the full suite in parallel |
| `make lint` / `make stan` | Pint check and Larastan |
| `make migrate` | Run migrations in Sail |
| `make artisan cmd="..."` | Any artisan command |

The app is at `http://localhost:$APP_PORT`. Caddy serves `https://$CADDY_BASE_DOMAIN` (default `app.test`, which needs an `/etc/hosts` entry).
