# Laravel foundation

**Status**: Backlog. Seeded by the template; the first package to promote after init.
**Owner**: Mixed: section A is the operator's, sections B and C are Claude Code's.
**Gate**: none (init done, `make doctor` passing).

Read `CLAUDE.md` and `docs/initialisation.md` before starting. Survey `laravel/` as it stands: the template ships a Laravel scaffold that may be several releases behind, so check the current state rather than assuming it.

## Goal

{{APP_NAME}} runs on the latest Laravel release under Sail, with Breeze authentication, every Makefile target working against it, the Pest suite green locally and in CI, and the Actions test-and-deploy path proven end to end.

## Section A: the operator's decisions and actions (not Claude Code tasks)

1. **Breeze stack.** Choose Blade (the default), Livewire, React or Vue, and whether to enable dark mode. Claude Code installs whichever is chosen, with `--pest`.
2. **GitHub configuration** for `{{GITHUB_OWNER}}/{{GITHUB_REPO}}`:
   - the `production` environment;
   - the `run-pest` label;
   - import `.github/rulesets/main.json`;
   - the secret `AWS_DEPLOY_ROLE_ARN`;
   - the variables `AWS_REGION`, `DEPLOY_TAG_KEY`, `DEPLOY_TAG_VALUE`, `DEPLOY_COMMAND`, `DEPLOY_CHECKOUT_PATH` and `PRODUCTION_URL` (`https://{{PRODUCTION_DOMAIN}}`).
3. **AWS**: the GitHub OIDC deploy role, the tagged target instances and the on-instance deploy command `DEPLOY_COMMAND` points at. Through Terraform, outside this repository.
4. **Run `make up` and `make doctor`** on each development machine, after this package's dependency changes land.

## Section B: blocked behind section A

5. **Test and deploy workflow.** Once section A step 2 is done, open this package's feature branch PR into `main`, so that `ci.yml` runs the full `checks` and `pest` without a label. Then:
   - confirm the release-please PR appears after the merge;
   - after step 3 as well, confirm that merging it publishes a release and that `deploy.yml` deploys and verifies it.

   Record the run links in this package's status line.

## Section C: no gate, can start immediately

6. **Latest Laravel.**
   - Bring `laravel/` to the current Laravel release by following the official upgrade guide, rather than reinstalling over it.
   - Keep this repository's overlay files: `compose.yaml`, `docker/`, `.env.example`, `pint.json`, `phpstan.neon`, `phpunit.xml` and `tests/Arch/`.
   - If `.env.example` changes, run `make env-sync`.
7. **Sail.**
   - Update `laravel/sail` and reconcile `compose.yaml` with the current Sail stubs, keeping the Caddy service, the separate root password and the `docker/mysql/` read-only user script.
   - Confirm `make up` builds and `make doctor` passes.
8. **Breeze authentication.** Run `composer require laravel/breeze --dev`, then `php artisan breeze:install <stack> --pest`, through `make artisan`. Then:
   - route every Breeze string through `lang/`, per the constitution;
   - keep `routes/web.php` and the tests Pest-only.
9. **Makefile targets.** Check each target against the new app and fix any that drifted: `dev`, `test`, `logs`, `env-sync`, `doctor`, `backup`, `restore` and `fresh`.
   - Prove `make backup`, then `make restore` of that dump, on a scratch database. These are the operator's to run; Claude Code prepares and reports.
   - `make fresh` takes its backup first.
10. **Pest passing.** Breeze's auth tests run under Pest against MySQL, both with `make test` and in CI. `make lint` and `make stan` are clean, and coverage is above the 70% floor.

## Build order

6, 7, 8, 9, 10 in sequence, each committed with `make test` green. Then 5 once section A is done.

## Out of scope

- Any product feature: those go through `docs/features/backlog/` and spec-kit.
- Production infrastructure code. That's section A step 3, and belongs outside this repository.
- Replacing Breeze with a different auth stack.
