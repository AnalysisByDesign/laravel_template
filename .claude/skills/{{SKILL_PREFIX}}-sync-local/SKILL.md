---
name: "{{SKILL_PREFIX}}-sync-local"
description: Bring this machine up to date after a merge, here or on the other machine, onto the branch the merge landed in (main, or a feature/* branch for a task PR). Refuses to pull into unmerged work; switches off a merged branch and deletes it once the squash is verified on its target, pulls the target fast-forward only, runs plain migrate only on the operator's yes in the moment, says whether a dev stack bounce is needed and gives the command, and runs the duplicate work package check. Phase 3 of {{SKILL_PREFIX}}-merge, and runnable on its own. Never bounces the stack, never runs a destructive database command.
compatibility: Requires gh authenticated against this repository's GitHub remote, the Makefile Sail targets, and the conventions in CLAUDE.md
model: haiku
metadata:
  author: "{{GITHUB_OWNER}}"
---

# Sync This Machine with `main`

After a merge, every machine that works on this project has the same job: get onto `main`, pull it, apply any new migrations, bounce the stack if the merge needs it, and clear away the merged branch. `{{SKILL_PREFIX}}-merge` does this as its Phase 3 on the machine that merged. **This skill is that phase on its own**, so the other machine can do it when it next picks up work, and so the rules live in one place.

**Input**: nothing. When `{{SKILL_PREFIX}}-merge` calls it, it passes the branch it has just merged, and that branch is the one deleted in step 2.

**The target is the merged PR's base branch, not always `main`**. Under the feature-branch model a task branch merges into its `feature/*` branch, and only the feature branch merges into `main`. Read `baseRefName` from the merged PR and call it `$TARGET`; every mention of `main` in steps 2 and 3 means `$TARGET`. Run from a branch with no merged PR, `$TARGET` is `main` as before.

Syncing onto a feature branch applies that feature's migrations to this machine's database. That is intended: each dev machine works one feature at a time, which is the point of the model, so its database follows the feature it is on. Say so in the migration question, since the schema will be ahead of `main` until the feature merges.

## Rules

- **Never pull `main` into unmerged work.** the operator's two-machine sequencing (`CLAUDE.md`, "Branching & PR workflow") is that local work is not brought up to date with `main` until its own merge has landed. Migrations also run from the checked-out code, so syncing while on a feature branch would migrate a database to a schema neither `main` nor the branch describes.
- **Never run a destructive database command.** Plain `migrate`, on the operator's explicit yes in the moment, is the whole of the permission. `migrate:fresh`, `migrate:refresh`, `migrate:reset`, `db:wipe` and any `TRUNCATE` or unscoped `DELETE` stay forbidden on every machine. **An agent cannot tell from the repository which database it is about to touch, or whether it holds hand-built data nobody can recreate.**
- **Never start, stop or bounce the dev stack.** Say whether a bounce is needed and give the command.
- **Never rebase or force anything.** `main` is pulled fast-forward only.
- **Never reason about the other machine.** This skill sees one checkout.

## 1. Establish the facts

```bash
git rev-parse --abbrev-ref HEAD
git status --porcelain
hostname
```

If `docs/runbooks/dev-stack.md` records how the stack runs on this host (a service manager rather than a terminal), its bounce command is the one to give in step 5. Otherwise the stack is `make dev` in the operator's own terminal. Checkouts on different machines can sit at the same path, which is why this is a command and not a guess.

**A dirty working tree stops the run.** Report what is uncommitted and change nothing; switching branches with it in place either fails or carries it somewhere it does not belong.

## 2. Get onto `main`

- **On `main`**: go to step 3.
- **On a feature branch**, ask GitHub whether it has merged:

  ```bash
  gh pr list --head "$BRANCH" --state merged --json number,mergeCommit,baseRefName
  ```

  - **Not merged**: stop. Say the branch holds unmerged work and that syncing would pull `main` into it. Change nothing. If the operator wants `main` in the branch, that is a deliberate merge of `main` into the branch, by the branch sync rule in `CLAUDE.md`, and not this skill's job.
  - **Merged**: `TARGET=<baseRefName>`, `git switch "$TARGET"` (creating it to track `origin/$TARGET` if this machine has no copy), then continue to step 3. Delete the branch only after the pull, once the squash commit is on the local target:

    ```bash
    git merge-base --is-ancestor "$MERGE_COMMIT" "$TARGET" && git branch -D "$BRANCH"
    ```

    `git branch -d` refuses after a squash-merge, because the branch's own commits are not ancestors of `main`; the merge commit being on `main` is the proof that `-D` loses nothing. If it is not there, keep the branch and say so.

## 3. Pull

```bash
OLD_MAIN=$(git rev-parse "$TARGET")
git fetch --prune origin
git pull --ff-only origin "$TARGET"
```

**If the fast-forward fails, stop.** Local `main` holds commits `origin/main` does not, which should never happen given the pre-push hook, and is the operator's to look at before anything else runs.

Record what changed, for the bounce decision:

```bash
git diff --name-only "$OLD_MAIN" "$TARGET"
```

**Stale branches.** List local branches whose remote has gone (`git branch -vv | grep ': gone]'`). For each, check its PR is merged and its merge commit is on that PR's own base branch (fetched as `origin/<base>`), as in step 2. A `feature/*` branch whose remote has gone merged into `main` and is verified against `main`. Offer to delete the verified ones in one question; keep any that do not verify and name them. This is how the other machine clears its copy of a branch merged elsewhere.

## 4. Migrations

Read-only, and it needs Sail up:

```bash
make artisan cmd="migrate:status"
```

If the stack is down the command fails; report that as a fact, do not chase it, and say the check is outstanding.

If any are pending, **say how many and name them**, then ask the operator with `AskUserQuestion` whether to run them now. On a yes, and only then:

```bash
make migrate
```

Nothing else, and never with a flag. On a no, the migration is outstanding and goes in the operator's actions.

## 5. Bounce

A bounce is needed if the pull moved `composer.lock` or `package-lock.json`, changed `vite.config.js`, anything under `config/` or `.env.example`, or if a migration ran. A change to `.env.example` also means this machine's own `.env` may need the new keys; say which keys were added.

Give the command for this machine and never run it:

- **A host listed in `docs/runbooks/dev-stack.md`**: the bounce command recorded there. A service-managed stack runs no migrations, so if any are still outstanding, say so alongside.
- **Otherwise**: the operator bounces their own `make dev` session.

## 6. Duplicate work packages

```bash
for d in docs/work-packages docs/work-packages/backlog docs/work-packages/done; do
  ls "$d" | grep '\.md$' | grep -v '^README\.md$'
done | sed -E 's/^(wp)-[0-9]{3}[a-z]?-/\1-/' | sort | uniq -d
```

**The `README.md` exclusion is load-bearing**; there is one per directory. Silence means clean. A hit almost certainly means the rename half of a squash-merge did not remove the old name.

**Run the `sed` exactly as written.** It strips `wp-NNN-`, the batch number, which sits inside the name. An earlier version stripped a leading `NNN-`, matched nothing, and reported clean against the very duplicate it was written for.

## Output

Fixed and compact, nothing before it:

```
Machine     laptop
Branch      052-user-export merged as #441, switched to main, deleted
Pulled      a1b2c3d..9f2a1c4, 14 files
Branches    2 stale deleted, 0 kept
Migrations  2 pending, run on the operator's yes
Bounce      needed (migration ran, composer.lock moved)
Duplicates  none

The operator's actions
- Bounce the dev stack: stop and restart make dev
```

A stop reports the step it stopped at and why, and nothing after it.

## Out of scope

- Merging anything, or merging `main` into a branch.
- Starting, stopping or bouncing the dev stack.
- Any database command beyond `migrate:status` and plain `migrate` on a yes.
- Editing `.env`. It reports keys `.env.example` gained; filling them is the operator's.
- Regenerating the documentation indexes, which is `{{SKILL_PREFIX}}-merge` Phase 4 on the merging machine only.
- Anything about the other machine.
