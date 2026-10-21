# Runbook: coverage floor override

Reference: `.github/workflows/ci.yml` and constitution Principle II.

## When to use this

The `pest` job in `ci.yml` blocks a PR if coverage falls below the floor. Principle II allows an **owner-only, logged** override for the rare case where merging without meeting the floor is the right call: a trivial, low-risk change where full coverage is not proportionate, or an urgent fix that cannot wait. It is an escape hatch, not a normal path.

## What it does not do

The override does not change the `pest` job's result on the PR, which still runs and may still show red. It is a **separate, manually triggered run** (the `coverage-override` job) against the same commit, which reports coverage without enforcing the floor. Merging despite the red `pest` job is the operator's procedural decision, with the override run as the recorded justification.

## How to dispatch it

Only a collaborator with write access can do this; GitHub does not offer `workflow_dispatch` to anyone else.

```bash
gh workflow run ci.yml --ref <branch-name> -f reason="<why this override is needed>"
gh run watch --exit-status
```

Or in the UI: Actions, CI, Run workflow, choose the PR's branch, fill in **reason** (required), Run workflow.

## What gets logged

The `coverage-override` job's run summary records who dispatched it (`github.actor`), when (UTC), the ref, and the required reason. The override is never silent and is identifiable afterwards from the Actions run history.
