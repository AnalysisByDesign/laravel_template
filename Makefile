# Development targets
# Usage: make <target>
#
# All targets run against laravel/ (the Laravel app lives at /laravel, never
# the repo root). Each recipe line runs in its own shell, so the `cd laravel`
# inside $(SAIL) applies per-invocation.

SAIL = cd laravel && ./vendor/bin/sail

.PHONY: help up down restart logs shell mysql tinker dev-clean \
        caddy-logs caddy-reload caddy-rebuild \
        migrate seed fresh rollback \
        npm-install dev dev-vite dev-queue build \
        test test-parallel test-serial test-db-grant test-branch test-coverage \
        lint pint stan artisan db-snapshot \
        composer-install composer-update env-sync

help:
	@echo ""
	@echo "  FIRST TIME SETUP (new machine):"
	@echo "    See README.md"
	@echo ""
	@echo "  DAILY COMMANDS:"
	@echo "    make up               Start all containers"
	@echo "    make down             Stop all containers"
	@echo "    make restart          Stop then start all containers"
	@echo "    make logs             Tail container logs"
	@echo "    make shell            Shell into the app container"
	@echo "    make npm-install      Install JS dependencies (run once after clone)"
	@echo "    make dev              Start Vite + queue listener (hot reload, runs npm install)"
	@echo "    make build            Production Vite build"
	@echo ""
	@echo "  LOCAL HTTPS (Caddy):"
	@echo "    make caddy-logs       Tail the proxy (cert issuance shows here)"
	@echo "    make caddy-reload     Reload Caddyfile without re-issuing certs"
	@echo "    make caddy-rebuild    Rebuild the Caddy image"
	@echo ""
	@echo "  DATABASE:"
	@echo "    make migrate          Run pending migrations"
	@echo "    make seed             Run seeders"
	@echo "    make fresh            Drop all tables, re-migrate, re-seed"
	@echo "    make rollback         Roll back last migration batch"
	@echo "    make mysql            MySQL CLI"
	@echo "    make tinker           Laravel Tinker REPL"
	@echo "    make db-snapshot      Dump dev DB to laravel/storage/backups (gitignored)"
	@echo ""
	@echo "  TESTING & QUALITY:"
	@echo "    make test             Whole Pest suite in parallel; with ARGS, one process"
	@echo "    make test-serial      Whole Pest suite in one process (order-dependence debugging)"
	@echo "    make test-branch      Run the test files this branch adds or changes"
	@echo "    make test-coverage    Suite with coverage and the CI floor"
	@echo "    make lint             Pint code style check (no changes)"
	@echo "    make pint             Pint code style fix"
	@echo "    make stan             Larastan/PHPStan static analysis"
	@echo ""
	@echo "  MISC:"
	@echo "    make artisan cmd=\"db:show\"   Run an arbitrary artisan command"
	@echo "    make composer-install         composer install"
	@echo "    make composer-update          composer update"
	@echo "    make env-sync                 Line laravel/.env up with .env.example (ARGS=--check to preview)"
	@echo ""
	@echo "  URLS (ports from laravel/.env):"
	@echo "    App:    http://localhost:APP_PORT"
	@echo "    Vite:   http://localhost:VITE_PORT (when make dev is running)"
	@echo "    HTTPS:  https://CADDY_BASE_DOMAIN (via Caddy)"
	@echo ""

# ── Containers ────────────────────────────────────────────────────────────────

up:
	$(SAIL) up -d

down:
	$(SAIL) down

restart: down up

logs:
	$(SAIL) logs -f

shell:
	$(SAIL) shell

# ── Local HTTPS (Caddy) ───────────────────────────────────────────────────────

# Tail just the proxy. Certificate issuance problems surface here and
# nowhere else, so this is the first place to look when an HTTPS hostname
# fails to load but http://localhost:APP_PORT is healthy.
caddy-logs:
	$(SAIL) logs -f caddy

# Reload the Caddyfile in place, without dropping connections or
# re-issuing certificates. Use after editing laravel/docker/caddy/*.
caddy-reload:
	$(SAIL) exec caddy caddy reload --config /etc/caddy/Caddyfile

# Rebuild the image. Needed after changing the Dockerfile, e.g. adding a
# Caddy module or pinning a new version.
caddy-rebuild:
	$(SAIL) build caddy
	$(SAIL) up -d caddy

# ── Database ──────────────────────────────────────────────────────────────────

migrate:
	$(SAIL) artisan migrate

seed:
	$(SAIL) artisan db:seed --force

fresh:
	$(SAIL) artisan migrate:fresh --seed --force

rollback:
	$(SAIL) artisan migrate:rollback

mysql:
	$(SAIL) mysql

tinker:
	$(SAIL) artisan tinker

# Snapshot the dev database to a gitignored, timestamped dump so an
# incident is a restore, not forensics. Run before risky sessions.
db-snapshot:
	@mkdir -p laravel/storage/backups
	$(SAIL) exec -T mysql sh -c 'mysqldump -uroot -p"$$MYSQL_ROOT_PASSWORD" --single-transaction "$$MYSQL_DATABASE"' | gzip > storage/backups/dev-$$(date +%Y%m%d-%H%M%S).sql.gz
	@ls -lh laravel/storage/backups/ | tail -3

# ── Frontend ──────────────────────────────────────────────────────────────────

npm-install:
	$(SAIL) npm install

# Local dev runs Vite and a queue listener side by side: anything queued on
# the database queue (mail, notifications) otherwise sits in the jobs table
# forever while sync work appears to succeed, a confusing half-working state.
# queue:listen (not queue:work) restarts the worker per job so code changes
# are picked up without bouncing it. Ctrl-C stops both.
#
# `-k` matters as much as `-j`: without it one child failing (Vite OOM, say)
# tears the others down for reasons that have nothing to do with them.
dev: npm-install dev-clean
	$(MAKE) -k -j2 dev-vite dev-queue

# Clear what a previous `make dev` left running INSIDE the container. Every
# dev process is started with `sail ...`, which is `docker compose exec`: the
# process lives in the container and only the exec client lives on the host.
# Killing the host side leaves the container process running, holding its
# port, and on exit laravel-vite-plugin deletes public/hot, so `@vite`
# silently falls back to the static build while the OLD Vite still runs.
# The leading `-` keeps a clean container (pkill exits 1 when nothing
# matches) from failing the target.
dev-clean:
	-$(SAIL) exec -T laravel.test pkill -f 'artisan queue:(listen|work)|npm run dev|sh -c vite|node .*/\.bin/vite'
	rm -f laravel/public/hot

dev-vite:
	$(SAIL) npm run dev

dev-queue:
	$(SAIL) artisan queue:listen database --tries=1

build: npm-install
	$(SAIL) npm run build

# ── Testing & quality ─────────────────────────────────────────────────────────

# Run the Pest suite inside Sail.
#
# Bare `make test` runs the whole suite in parallel: each worker process gets
# a database of its own (testing_test_1, testing_test_2, ...), so the workers
# never share a schema. The app and MySQL containers are each capped at 4
# CPUs (compose.yaml), so gains flatten past a handful of workers; raise
# TEST_PROCESSES only if those caps move.
#
# With ARGS it runs in one process on the base `testing` schema:
# make test ARGS="--filter=ExampleTest". A filtered run gains nothing from
# many workers, and staying on `testing` means it cannot collide with a full
# parallel run going on beside it.
#
# A fresh MySQL volume already lets the sail user create the worker
# databases. One created before Sail granted `testing%` needs
# `make test-db-grant` once, or every worker fails at CREATE DATABASE.
TEST_PROCESSES ?= 8
test:
ifeq ($(strip $(ARGS)),)
	$(SAIL) test --parallel --processes=$(TEST_PROCESSES)
else
	$(SAIL) test $(ARGS)
endif

# Explicitly parallel, for passing ARGS to a parallel run. Paratest takes one
# path, not several, and a parallel run narrowed by --filter can exit 1 with
# every test passing; a filtered run belongs in one process anyway.
test-parallel:
	$(SAIL) test --parallel --processes=$(TEST_PROCESSES) $(ARGS)

# Explicitly one process, for running the WHOLE suite serially: chasing an
# order-dependent failure, which a parallel run reshuffles on every attempt.
test-serial:
	$(SAIL) test $(ARGS)

# One-off, per MySQL volume: let the sail user create and drop the parallel
# workers' databases. Safe to repeat.
test-db-grant:
	$(SAIL) exec mysql sh -c 'mysql -uroot -p"$$MYSQL_ROOT_PASSWORD" -e "GRANT ALL PRIVILEGES ON \`testing%\`.* TO \"$$MYSQL_USER\"@\"%\";"'

# The feature's own subset: every test file added or changed on this branch
# since it left main, committed or not. The diff needs no upkeep, unlike a
# hand-labelled group. Runs nothing, successfully, when no test file changed.
BRANCH_BASE ?= $(shell git merge-base HEAD origin/main 2>/dev/null || git merge-base HEAD main)
test-branch:
	@files="$$( { git diff --name-only --diff-filter=AMR $(BRANCH_BASE) -- 'laravel/tests/*Test.php'; git ls-files --others --exclude-standard -- 'laravel/tests/*Test.php'; } | sort -u | sed 's#^laravel/##' | tr '\n' ' ')"; \
	if [ -z "$$files" ]; then echo "No test files changed since $(BRANCH_BASE)."; exit 0; fi; \
	echo "Running: $$files"; \
	cd laravel && ./vendor/bin/sail test $$files $(ARGS)

# Coverage against the constitution's baseline floor. The single --min here
# is the CI floor; per-area tiers are scrutinised at review time from the
# per-file report.
test-coverage:
	$(SAIL) test --coverage --min=70

# Code style check only: fails on violations, changes nothing.
lint:
	$(SAIL) php ./vendor/bin/pint --test

# Code style fix (Pint).
pint:
	$(SAIL) php ./vendor/bin/pint

# Static analysis (Larastan/PHPStan).
stan:
	$(SAIL) php ./vendor/bin/phpstan analyse

# Rebuild laravel/.env on the layout of .env.example, keeping this machine's
# values; backs up first and verifies before writing. ARGS="--check" previews.
env-sync:
	python3 tools/env-sync/sync_env.py $(ARGS)

# Run an arbitrary artisan command inside Sail, e.g.:
#   make artisan cmd="db:show"
#   make artisan cmd="make:model Order -m"
artisan:
	$(SAIL) artisan $(cmd)

# ── Dependencies ──────────────────────────────────────────────────────────────

composer-install:
	$(SAIL) composer install

composer-update:
	$(SAIL) composer update
