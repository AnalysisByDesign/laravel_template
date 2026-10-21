<!-- TEMPLATE-ONLY:START -->
# Laravel application template

A Laravel 13 / PHP 8.5 starting point with the delivery process built in: Sail with MySQL, Redis and Caddy; Pest, Pint and Larastan; spec-kit; a feature-branch model enforced by hooks and CI; release-please; release-gated SSM deploys; and Claude Code agents and skills that run the lifecycle. Each tag names the Laravel version it carries.

## Creating an application from it

1. On GitHub, choose **Use this template**, then clone the new repository.
2. Open it in Claude Code and run `/init-laravel-app`. It asks for:
   - the app name, slug, skill prefix, port suffix and domains;
   - whether to generate the database passwords.

   It then replaces every `{{PLACEHOLDER}}`, writes `laravel/.env` with a new `APP_KEY` and saves a summary to `docs/initialisation.md`. Init can only run once.
3. Review and commit the diff, then follow the next steps in `docs/initialisation.md`.

Everything below this section is the new application's README, and init fills it in.
<!-- TEMPLATE-ONLY:END -->

# {{APP_NAME}}

{{APP_DESCRIPTION}}

The values this repository was initialised with are in `docs/initialisation.md`. `CLAUDE.md` describes how the pieces fit together.

## Prerequisites

- PHP `^8.5` and Composer
- Docker, for Laravel Sail
- Node.js LTS and npm
- PlantUML (`brew install plantuml`), used by the pre-commit hook to render `.puml` diagrams
- gitleaks, run from your global `~/.git-hooks`
- Python 3, for `tools/`

## Getting started

1. `git clone git@github.com:{{GITHUB_OWNER}}/{{GITHUB_REPO}}.git`
2. If this machine has no `laravel/.env` yet, create one from `laravel/.env.example` and fill in `APP_KEY` and the three database passwords.
3. `make up`. The first run builds the PHP 8.5 image, and MySQL creates the `{{APP_SLUG}}_rw` and `{{APP_SLUG}}_ro` users.
4. `git config core.hooksPath .githooks`
5. `make doctor`

## Common commands

| Target | Effect |
| --- | --- |
| `make doctor` | Read-only check of tools, `.env`, hooks and the stack |
| `make up` / `make down` | Start or stop Sail (app, MySQL, Redis, Caddy) |
| `make dev` | Vite and the queue listener |
| `make logs` | Tail the container logs |
| `make test` | The whole Pest suite in parallel; `ARGS="..."` for one file or filter |
| `make lint` / `make stan` | Pint check and Larastan |
| `make env-sync` | Line `laravel/.env` up with `.env.example` |
| `make backup` / `make restore` | Dump to `backups/`, or restore the newest or `DUMP=<file>` |
| `make fresh` | Back up, then re-migrate and re-seed (asks for `yes`) |

The app is at http://localhost:8{{PORT_SUFFIX}}. Caddy serves https://{{LOCAL_DOMAIN}}, which needs an `/etc/hosts` entry.

## CI and deploys

GitHub Actions workflows: [`ci.yml`](https://github.com/{{GITHUB_OWNER}}/{{GITHUB_REPO}}/actions/workflows/ci.yml), `release-please.yml` and `deploy.yml`. The secrets and variables each one needs are listed at the top of each workflow file.
