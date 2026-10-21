---
name: tpl-promote-wp
description: Promote one work package from docs/work-packages/backlog/ into the live folder because work on it is about to begin, cutting and pushing its feature/wp-slug branch from main and writing the Target branch line. Optionally gives it a batch number the operator names. One package per invocation; leaves the document change staged for the operator to review and commit.
compatibility: Requires the docs/work-packages/ layout and conventions described in docs/work-packages/README.md
model: haiku
metadata:
  author: laravel-template
---

# Promote a Work Package Out of the Backlog

Move one work package out of `docs/work-packages/backlog/` and into `docs/work-packages/`, and give it the feature branch its work will collect on. This is the work package sibling of `tpl-promote-backlog-spec`, and it exists for the same reason: under the feature-branch model the folder a document sits in says whether anyone is working on it, and promotion is the moment its branch is cut.

`docs/work-packages/backlog/` holds packages nobody is working on yet. `docs/work-packages/` holds packages in flight. `done/` holds delivered ones, reached through `tpl-archive-wp`.

**Input**: one package, by slug or filename. `wp-` and `.md` are optional. Optionally a batch number, `NNN` or `NNNx`, if the operator names one; never choose one.

**One package per invocation.** Which packages get promoted is the operator's call, made per package when they invoke this skill. Never suggest or perform a promotion unprompted.

## 1. Preconditions

Check all of these before touching anything. If any fails, stop, say which and why, and change nothing.

1. **Clean working tree**: `git status --porcelain` is empty.
2. **The package is in the backlog**: exactly one `docs/work-packages/backlog/wp-*<slug>*.md`. If the slug matches several, list them and stop.
3. **No collision**: no `docs/work-packages/wp-*<slug>.md` at the live root or in `done/`, and no `feature/wp-<slug>` branch locally or on `origin` (`git ls-remote --heads origin "feature/wp-<slug>"`).
4. **Its gate is clear, or the operator says to go anyway.** Read the `**Gate**` line. If it names something not yet true, say so and ask; a package promoted behind an open gate is a branch nobody can work on.

## 2. Move

```bash
git mv docs/work-packages/backlog/wp-<slug>.md docs/work-packages/wp-<slug>.md
# or, with a batch number the operator named:
git mv docs/work-packages/backlog/wp-<slug>.md docs/work-packages/wp-NNN-<slug>.md
```

## 3. Restate the header

Change only the header block, never the substance:

- **Status line**: prefix it with `In flight from <today>, promoted from the backlog.` and keep the rest of the line as history.
- **Target branch line**: add `**Target branch**: \`feature/wp-<slug>\`` directly below the `**Gate**` line. This is the one piece of data the model threads through: every task PR for this package targets it, and `tpl-merge` checks a task PR's base against it.

Then move the package's row in `docs/work-packages/README.md`: change its Package cell from `` `backlog/wp-<slug>.md` `` to the new filename, and its batch cell to the number if one was given. Rows stay in the folder's existing order.

## 4. Cut the feature branch

The branch name never carries the batch number, since batch numbers are reused and branches outlive a batch.

```bash
git fetch origin main --quiet
git branch "feature/wp-<slug>" origin/main
git push -u origin "feature/wp-<slug>"
```

Pushing fires no workflow. **Ask the operator before the push**, since it is the one step that reaches `origin`; if they decline, keep the local branch and say the push is outstanding.

The move and header edits stay staged on the branch the operator ran this from and reach `main` through their own PR. The feature branch picks them up the next time `main` is merged into it.

## 5. Rewrite references

Repository-rooted paths only, by exact string replacement:

- `docs/work-packages/backlog/wp-<slug>.md` becomes `docs/work-packages/<new filename>`.
- A relative Markdown link to the old location is recomputed from the linking file's own folder.
- A batch number added in step 2 changes the bare filename too, so `wp-<slug>.md` written alone becomes the new name.

Skip `CHANGELOG.md`, `docs/reference.md`, `docs/roadmap/` and `docs/claude-transfer/`: all generated or symlinked, and fixed by regenerating rather than editing. Rerun the sweep afterwards; anything left is a deliberate skip or a bug.

## 6. Stage and report

Stage everything and **do not commit**. Report:

- The move, old path to new path, and the batch number if one was given.
- The header edits, before and after.
- The feature branch, the `origin/main` commit it was cut from, and whether it was pushed.
- Every file with rewritten references and a count per file.
- That `docs/reference.md` and the roadmap are now stale; `tpl-merge` regenerates both after the promotion PR merges.

## Out of scope

- Choosing which package to promote, or a batch number.
- Demoting a package back to the backlog, or archiving one (`tpl-archive-wp`).
- Editing anything below the header block.
- Committing, or pushing anything other than the new feature branch.
- Packages already in flight on `main` from before the model. They carry no target branch and finish the old way; promotion applies to what is promoted from now on.
