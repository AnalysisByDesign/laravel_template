# Runbook: production rollback

Reference: `.github/workflows/deploy.yml` and `scripts/deploy/`.

## When to use this

A published release has deployed and something is visibly wrong in production (a failed post-deploy verify, the health endpoint misbehaving, a problem found afterwards), and the fastest fix is to restore the previous release rather than roll forward with another fix.

## One-command rollback

Find the previous release tag, then dispatch `deploy.yml` against it. This re-runs the same trigger and verify sequence as a normal deploy, with that tag as the ref deployed.

```bash
gh release list --limit 2                                   # identify the previous tag
gh workflow run deploy.yml --ref main -f ref=v0.2.1         # example
gh run watch --exit-status
```

`--ref main` selects which copy of the *workflow file* runs, always `main`; the `-f ref=...` input is what actually gets deployed.

Or in the UI: Actions, Deploy, Run workflow, branch stays `main`, set **ref** to the previous release tag, Run workflow.

## Verification after dispatch

- The run goes green only if every targeted instance's deploy succeeded and the post-deploy checks passed. A red run means the rollback did not complete cleanly and needs a person to look.
- Confirm the specific symptom that triggered the rollback is gone, not just that the workflow is green: the automated checks only prove the site is up and serving.

## Migrations are not rolled back

**A rollback returns the code. It does nothing to the database.** Afterwards the schema is ahead of the code. That is usually survivable, because most migrations add nullable columns older code ignores. It is not survivable for a migration that wrote or deleted data, and `down()` is no help there.

- **A code problem** (wrong behaviour, a bad release): dispatch this workflow at the previous release tag. The schema stays where it is.
- **A data problem** (a migration wrote or deleted the wrong thing): restore the database snapshot taken before the deploy. Not a code rollback, and not `migrate:rollback`, which is a second unattended write against a schema already in doubt.

**If a migration fails part way through a deploy**, the batch is left part-applied: Laravel runs each migration separately, so only a migration that wraps its own `up()` in a transaction rolls itself back. `php artisan migrate:status | grep -i pending` shows where it stopped. Correcting the migration and deploying forward is almost always better than rolling back.
