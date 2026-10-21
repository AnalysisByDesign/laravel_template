---
name: "{{SKILL_PREFIX}}-merge"
description: "Run the merge for one pull request, a task PR into its feature/* branch or a feature branch into main, with the gates each kind needs: check the gates with definite questions rather than inference, squash-merge on the operator's confirmation, reconcile the local machine, regenerate the documentation indexes from post-merge main, and carry them in a documentation-only follow-up PR. Never merges over a red or pending check, never launches /code-review, never bounces the dev stack."
compatibility: Requires gh authenticated against this repository's GitHub remote, the Makefile Sail targets, and the conventions in CLAUDE.md
model: sonnet
metadata:
  author: "{{GITHUB_OWNER}}"
---

# Merge a Branch and Reconcile What Follows It

Merge is the moment several bookkeeping jobs fall due at once: gates checked, the work moved to `done/`, indexes regenerated, duplicates checked, sessions renamed. Done from memory they get done unevenly. This skill runs them as five phases in a fixed order, and it is also where the two-machine problem is handled, because branch drift and local schema drift both show up here and nowhere else.

**Input**: a pull request number, or nothing to resolve the PR from the current branch.

## The three kinds of merge

Under the feature-branch model, not every merge lands on `main`. Phase 0 decides the kind from the PR's head and base, and the kind decides which gates apply and which phases run:

| Kind | Head, base | Pest | Archive | Phases |
| --- | --- | --- | --- | --- |
| **Task merge** | any branch into `feature/*` | The operator's choice, as below | never | 0 to 3, onto the feature branch |
| **Feature merge** | `feature/*` into `main` | mandatory; `ci.yml` runs it without a label | when the work is finished | all five |
| **Direct merge** | any other branch into `main`: a production fix with no owning feature, generated docs | mandatory for a `fix/*` branch, the operator's choice otherwise | when the work is finished | all five |

A production fix that goes straight to `main` has no later safety net, which is why pest is mandatory for it, and a fix for a feature in flight goes to that feature branch instead (`{{SKILL_PREFIX}}-fix-branch`). The release gate for everything inside a feature branch is the feature merge.

## Rules that hold in every phase

Five, and none of them bends for a hurry:

- **Never merge over a red or pending check.** Pending is not green. A check that has not reported yet is a question nobody has answered.
- **Never launch `/code-review`.** It consumes the operator's entire session token budget, so an unprompted run costs them the session rather than a few thousand tokens. Report it as outstanding and give the operator the command. This holds even though `CLAUDE.md` lists it as a merge gate: naming an outstanding gate is the job, running it is not.
- **Never start, stop or bounce the dev stack.** Say a bounce is needed and give the command for the machine you are on.
- **Never rebase the branch.** Conflicts are resolved by merging `main` in. A rebase forces a force-push, which breaks the other machine's copy of the branch, and squash-merge flattens the history anyway so the tidiness it buys is discarded seconds later.
- **Never run a destructive database command.** Plain `migrate` is permitted in Phase 3 on the operator's explicit yes, and nothing else is. `migrate:fresh`, `migrate:refresh`, `migrate:reset`, `db:wipe` and any `TRUNCATE` or unscoped `DELETE` stay forbidden, on both machines, whatever the schema looks like.

## Phase 0: establish the facts

Three questions, each answered by a command rather than by reading the repository and inferring.

**Which branch and which PR.**

```bash
git rev-parse --abbrev-ref HEAD
gh pr view --json number,title,state,isDraft,mergeable,mergeStateStatus,reviewDecision,headRefName,baseRefName,url,body,labels,files
```

Stop if you are on `main`: there is no branch to merge and `.githooks/pre-push` would block the push anyway. Stop if no PR exists for the branch, and say so plainly rather than offering to open one; opening the PR is the end of the work, not the start of the merge.

**Which machine.** This decides the Phase 3 bounce wording and nothing else, so ask rather than assume:

```bash
hostname
```

If `docs/runbooks/dev-stack.md` records how the stack runs on this host (a service manager rather than a terminal), use its bounce command. Otherwise the stack is `make dev` run by the operator in their own terminal. **Checkouts on different machines can sit at the same path and the `.env` that distinguishes them is gitignored**, which is why this is a command and not a guess.

**Which kind of merge.** `headRefName` and `baseRefName` from the PR view above, against the table at the top.

**What the branch completes.** Read the PR body and the changed file list for a work package, a spec, or GitHub issues. **A task merge never completes anything**: the work is done when its feature branch merges into `main`, so skip the question. Then **ask the operator** whether the work package or spec is finished. Do not infer it from ticked checkboxes, from a merged PR, or from the work looking done; `{{SKILL_PREFIX}}-archive-wp` makes the same refusal for the same reason, and the answer determines whether Phase 1 has an archive to carry.

## Phase 1: the pre-merge gate

Ask each question with a command. Collect every answer before reporting, so the operator sees one list rather than a trickle.

```bash
BASE=$(gh pr view "$PR" --json baseRefName -q .baseRefName)
git fetch origin
gh pr checks "$PR"
git rev-list --left-right --count "origin/$BASE"...HEAD
```

### The checks, and what each one is actually asking

**Base branch is the right one.** The base must be `main` or a `feature/*` branch that exists on `origin`. Where the work belongs to a spec or work package, its document's `**Target branch**` line names the feature branch, and a task PR's base must match it; a fix's target was chosen by `{{SKILL_PREFIX}}-fix-branch` and is recorded in the PR body. Any other base is the stacked-branch shape that duplicates work packages: stop and ask.

**Draft state.** The every-push CI jobs skip on a draft, so **a draft PR has no green to read, it has an absence of red**. If the PR is a draft, mark it ready and wait for the run that starts:

```bash
gh pr ready "$PR"
```

Then poll `gh pr checks "$PR"` until nothing is pending. Do not read the pre-draft run as the answer.

**Every check.** Each must be green or a deliberate skip:

- `checks` runs on every non-draft push. It holds `pint`, `larastan`, `audit`, `docs-guard` and `shell-lint` as one job (one job avoids per-job minute rounding), and its per-check results are in a single PR comment it keeps updated. Any failure stops the merge.
- `checks` on a task PR runs its task tier: only the per-file checks, on the changed files, with larastan deferred. It is a full run on any PR into `main`, so the feature merge is where larastan answers for everything the feature branch collected.
- **`pest` depends on the kind of merge.** On a task merge, and a direct merge that is not a fix, it is chosen at merge time by the operator and gated on the head commit; see the next section. On a feature merge, and a `fix/*` branch into `main`, it is mandatory: a completed green `pest` on the head commit is required, and the choice in step 2 below is not offered. `ci.yml` runs it without a label on both, so step 3's labelling is skipped and the gate is waiting for that run.

- A check that failed on billing or a runner rather than on the code is a different thing from a failing test. Read the failure before reporting it; a billing failure means the Actions allowance or payment arrangement has changed and is worth saying out loud. **Where CI genuinely cannot run at all**, the local `make test` that preceded every commit is the only evidence, and the report must say the gate was local. That is an outage exception rather than the cadence: it never stands in for a `pest` the operator chose not to run.

### The pest gate

`run-pest` costs a full-suite run of Actions time, and a label left on a branch reruns the suite on every push. So the suite runs only when deliberately chosen, here, and the label comes off again once it has answered. Sequential and in the foreground of this session throughout: no background agent.

**The answer is the `pest` job's conclusion for the head commit, never the label.** A label says a run was asked for; only a completed job on the commit being merged says what it found. Find it from the runs for the head SHA, newest first (the checks API is not reachable with this token):

```bash
SHA=$(gh pr view "$PR" --json headRefOid -q .headRefOid)
HEAD=$(gh pr view "$PR" --json headRefName -q .headRefName)
runs() {
  gh run list --workflow ci.yml --branch "$HEAD" --event pull_request --json databaseId,headSha,createdAt \
    -q "[.[] | select(.headSha == \"$SHA\")] | sort_by(.createdAt) | reverse | .[].databaseId"
}
for id in $(runs); do
  echo "$id $(gh run view "$id" --json jobs -q '.jobs[] | select(.name=="pest") | "\(.status) \(.conclusion)"')"
done
```

A `skipped` pest answers nothing, and a `cancelled` one is a run a newer one superseded. Read the newest pest that is neither.

1. **A completed green `pest` exists for the head SHA**: proceed without prompting.
2. **Otherwise, where pest is optional, ask the operator**, once: merge without pest, or run pest. Where it is mandatory, wait for the run `ci.yml` started; no label is needed. Merging without it is a legitimate answer; report it as their choice in the Phase 1 line, not as a gap.
3. **On run**: add the label, find the run it fires on the current head SHA, and wait for it to complete.

   ```bash
   gh pr edit "$PR" --add-label run-pest
   RUN=$(runs | head -1)   # repeat until it is not the run that was newest before labelling
   gh run watch "$RUN" --interval 60 --exit-status
   ```

   **Filter by branch and match the SHA in the query, not with `--commit`.** `gh run list --commit` can go on returning only the earlier run for a while after the label has fired a new one, while a branch listing shows the new run at once.

   Adding the label fires a fresh run of the whole workflow, and `ci.yml`'s concurrency group cancels any run already in progress on the PR, so the cheap checks report again too. If a single foreground call cannot outlast the run, call `gh run watch` again; do not hand the wait to a background task. Then read the conclusion with the loop above, against the same `SHA`.
4. **On red**: leave the label on while the failures are diagnosed and fixed, so each fix push reruns the suite, and come back to step 3 for each new head SHA. Report the failing tests as the thing to fix outside this skill (see Stopping). Loop until green; never merge on a red.
5. **On cancelled, or still pending after about forty-five minutes**: stop and report the run and its state. Never merge.
6. **On green**: remove the label, then continue.

   ```bash
   gh pr edit "$PR" --remove-label run-pest
   ```

   Removing it fires nothing: `ci.yml` triggers on `labeled` but not `unlabeled`, so it can neither start a run nor cancel one, and a completed `pest` keeps its conclusion. Recheck that if the trigger list in `ci.yml` changes. Removing it only after a green conclusion means the question never arises for a run in flight.

Phase 2 merges with `--match-head-commit "$SHA"`, so a push after the gate answered cannot slip in under its answer. A push that does land restarts this phase.

The release-please PR still runs `pest` by its head branch, whatever this gate decided for the PRs inside it, and this skill does not merge that PR anyway (see Out of scope).

**Mergeability.** `mergeable: CONFLICTING` or a `mergeStateStatus` of `DIRTY` means conflicts against the current base. The fix is to merge the base into the branch, never to rebase it:

```bash
git merge "origin/$BASE"
```

Migrations conflicting on ordering and the lock files are the two that actually happen, and `docs/features/README.md`, the roadmap, `docs/reference.md` and `CLAUDE.md` are the documents almost every branch touches. The merge commit then needs a push, which restarts CI, so re-run this phase afterwards rather than carrying the earlier green forward.

**Migration ordering, on a feature merge.** A feature branch lives long enough for `main` to gain migrations dated after the feature's own. Laravel runs pending migrations in filename order, so on production a feature migration dated before migrations already run there is applied after them, in an order no machine has tested. List the feature's migrations dated earlier than the newest migration on `main`:

```bash
NEWEST=$(git ls-tree --name-only origin/main laravel/database/migrations/ | sort | tail -1 | xargs basename)
git diff --name-only --diff-filter=A origin/main...HEAD -- laravel/database/migrations/ \
  | xargs -n1 basename | awk -v n="$NEWEST" '$0 < n'
```

Any listed are reported for the operator to confirm they are independent of the newer ones on `main`, or to be renamed to a current timestamp on the feature branch. Never rename one without their yes.

**Divergence from the base.** `git rev-list --left-right --count "origin/$BASE"...HEAD` gives behind and ahead. On a feature merge, `main` has usually moved a long way: merge it into the feature branch first, which is the final-testing reason, so pest and the full `checks` run answer for the combined code. Apply the branch sync rule: merge `main` in only with a reason. A merge about to happen **is** the final-testing reason, so where the branch is materially behind, merge `main` in, push, and let CI answer the question again. Where it is behind by a commit or two with no conflict, leave it: not pulling is a deliberate trade, not an oversight, and every extra merge commit is noise in a history that is about to be squashed flat.

**PR title is Conventional Commits.** The squash subject is what release-please parses, so a malformed title does not fail CI, it silently produces the wrong version bump or no changelog entry. Check the shape `type(scope): summary` against the types in use (`feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `ci`, `perf`, `build`, `style`), and fix it with `gh pr edit --title` rather than at merge time, so what the operator approves is what lands.

**Issue closing keywords.** If the branch resolves GitHub issues, the PR body needs `Fixes #N` or `Closes #N` so the merge closes them. Without it the issues stay open and the housekeeping falls to memory, which is the thing this skill exists to stop.

**Housekeeping that belongs on the branch.** Feature and direct merges only. If Phase 0 established that the branch finishes a work package or a spec, the archive belongs **in this PR**, not after it, so `main` is consistent at every commit. Run `{{SKILL_PREFIX}}-archive-wp` or `{{SKILL_PREFIX}}-archive-spec`, which need a clean tree and leave the change staged; commit it with a Conventional Commits subject, push, and re-run this phase because the push restarted CI. Also tick off completed tasks in `tasks.md` if the branch closed user stories.

**No regenerated indexes on the branch.** `docs/reference.md` and the roadmap belong in the Phase 5 follow-up PR, built from post-merge `main`. If they are in this branch's diff, say so: they are correct only when generated after the merge, and a copy built on a feature branch collides with every other branch's copy. Offer to drop them from the branch and let Phase 4 produce them.

### The two gates this skill reports and does not run

- **`/code-review`.** Give the operator the command and say it is outstanding. Saying it is outstanding is right; launching it is not, and quietly dropping it from the list is not either.
- **The `spec-reviewer` conformance pass**, for spec-kit implementation work. Report it as outstanding. It is a read-only in-session subagent rather than a cloud review, so offer to run it, and run it only on a yes.

### Stopping

On any red, stop and split the findings into two lists, because the difference decides what the operator does next:

- **What this skill can walk them through**: a conflict to resolve by merging `main` in, a draft to mark ready, a malformed PR title, a stale run to restart, an archive to carry, a pest run to wait on.
- **What has to be fixed outside it**: failing tests, a `larastan` or `pint` failure, a runtime dependency advisory, a review the operator has to read.

## Phase 2: merge

Everything green, and the two reported gates stated. Show the operator the exact squash subject and body, then ask once.

**The question is the operator's read-through, and it must be asked as that question**, not as "shall I proceed". `CLAUDE.md` requires their own read-through before a merge; this prompt is where that requirement is met, so it names the PR, its title, its file count, and the two outstanding gates, and waits.

On an explicit yes:

```bash
gh pr merge "$PR" --squash --delete-branch \
  --match-head-commit "$SHA" \
  --subject "<the Conventional Commits PR title>" \
  --body "<the squash body>"
```

- **Pass `--subject` explicitly.** Letting GitHub default it is what produces a subject with a `(#NNN)` already attached or a commit list in the wrong place, and release-please parses that subject.
- **The body carries the substance of the PR body**, trailers included, not the commit list.
- **`--match-head-commit` pins the merge to the commit the gate answered for.** If the head moved, the merge refuses; go back to Phase 1.
- **`--delete-branch` removes the remote branch.** The other machine may still hold a local copy of it; that is harmless and Phase 3's note tells the operator to prune it there.

On anything other than an explicit yes, stop. Report the state as ready to merge and leave the command, and do not ask a second time.

## Phase 3: reconcile this machine

**Run the `{{SKILL_PREFIX}}-sync-local` skill**, passing the branch just merged. On a task merge it lands on the feature branch rather than `main`, since that is the PR's base. It holds this phase's rules in one place, so the other machine runs the same thing: it switches to `main`, pulls fast-forward only, deletes the branch once the squash commit is verified on `main`, reports pending migrations and runs plain `migrate` only on the operator's yes in the moment, says whether a bounce is needed with the command for this machine, and runs the duplicate work package check.

**If it cannot find the squash commit on `main`, stop**: something went wrong in Phase 2, and nothing after this phase should run on a `main` that does not hold the merge.

Fold its output into this skill's Phase 3 line and the operator's actions. A migration it reported and the operator declined is still outstanding, which withholds the `DONE` heading at the end.

**The other machine.** Say explicitly that it needs `{{SKILL_PREFIX}}-sync-local` when it next picks up work. **This skill cannot see that machine and must not reason about its branch, database or running processes.** Naming the skill to run there is the whole of what can be done about it from here.

## Phase 4: regenerate from post-merge `main`

**Feature and direct merges only.** A task merge changed nothing on `main`, so there is nothing to regenerate: the run ends after Phase 3, and the session is not renamed `DONE`, because the feature it belongs to is still in flight.

On `main`, up to date, clean. Take a branch for the generated output:

```bash
git checkout -b "docs/regenerate-after-${PR}"
```

**Run `{{SKILL_PREFIX}}-prepare-docs-reference no-subset`**, which skips its subset step. It runs forked, in a clean context, so the argument is what tells it. Steps 1 to 4 only: regenerate `docs/reference.md` and run its pre-sync check (broken links, stale status lines, unresolved cited paths, uncovered files). **Do not run `subset.py` or touch `docs/claude-transfer/`**: the mobile upload subset rarely changes between merges, rebuilding it every time costs tokens for a date line, and a re-upload is the operator's call anyway. The operator rebuilds it by running the skill by hand on `main` when they want to refresh the mobile upload. Carry the pre-sync findings forward.

**Never place or remove a `docs/claude-transfer/` symlink by hand.** Edit `members.txt` and re-run the skill. A write through a symlink edits the real file a second time and can replace the link with a regular file.

**Run the roadmap generation first**, because `{{SKILL_PREFIX}}-prepare-docs-reference` indexes `docs/` and the roadmap documents live there:

```bash
python3 tools/roadmap/build.py
```

It rewrites `docs/roadmap/upcoming.md`, `docs/roadmap/completed.md` and the two roadmap diagrams (rendering their PNGs when PlantUML is installed) from the epics, the feature documents, the work packages, `git log` and the open issues, and says `unchanged` where nothing moved. Carry its warnings into the report rather than dropping them: items homed in no epic are invisible to a gate review, and items homed in more than one are double counted. Neither fails the run, because both describe the repository rather than the generator.

**Never hand-edit either file.** Correct the document a row points at and run the generator again. See `docs/roadmap/README.md`.

If the regeneration changed nothing, there is no follow-up PR. Say so and skip Phase 5.

## Phase 5: the documentation-only follow-up PR

```bash
git add <the generated paths>
git commit -m "docs: regenerate the documentation indexes after #${PR}"
git push -u origin "docs/regenerate-after-${PR}"
gh pr create --title "docs: regenerate the documentation indexes after #${PR}" --body "..."
```

**Check the diff holds nothing but generated output before going further.** The permitted set is `docs/reference.md`, `docs/claude-transfer/`, `docs/roadmap/upcoming.md`, `docs/roadmap/completed.md`, and the two roadmap diagrams with their renders (`docs/roadmap/roadmap-overview.puml`, `roadmap-gates.puml` and the `.png` beside each). Anything else in the diff means the branch is not documentation-only, and then it waits for the operator like any other PR:

```bash
git diff --name-only origin/main...HEAD
```

This check is what makes the next step safe, so it is not optional and its result goes in the report.

**Then mark it ready, wait for its checks, and squash-merge it through the guard script.** The content is generated, nothing in it is hand-written, so the skill merges it in the same run rather than leaving the indexes stale on `main`.

```bash
tools/merge-docs-pr.sh "<the new PR number>"
```

**Not `gh pr merge` directly, which the permission layer refuses here**, and rightly, because a Bash permission rule matches a command prefix and `gh pr merge 457 --squash` carries a pull request NUMBER rather than a branch name. Any rule permitting the Phase 5 merge would therefore also have permitted merging a feature pull request with no read-through, which `CLAUDE.md` requires as a merge gate.

`tools/merge-docs-pr.sh` is the narrow thing a rule can name, and `.claude/settings.json` allows exactly it. It re-checks every condition in code before merging, so the guard no longer rests on whoever runs this skill having read the paragraph above: the pull request must be open, not a draft, targeting `main`, on a `docs/regenerate-after-*` head branch, changing nothing outside the generated paths listed above, with a completed successful run **for the head commit** and every job successful or skipped. It refuses with a reason on any of those, and `--dry-run` checks without merging.

The diff check above is therefore run twice, once by hand for the report and once by the script. That is deliberate: the report needs the answer, and the merge needs it to be unskippable.

Then pull `main` again, so the machine ends the run on the real tip.

## Housekeeping, and the last step

Threaded through the phases above rather than collected at the end, except for these:

- **The claude.ai planning session.** Where this merge completed the transfer of a session brief, that brief is `processed` in `docs/sessions/` and the claude.ai session's name should be prefixed `DONE` ready for the weekly sweep. Prompt the operator; the rename is theirs, in that app.
- **Rename this session, last.** Call `{{SKILL_PREFIX}}-session-name done`, passing the session's existing heading if it has one, otherwise this session's start date and the merged branch. It runs forked and cannot see this conversation, so whatever it needs goes in the argument. It produces the `/rename` line for the operator and **cannot perform the rename itself**, so never report the session as renamed.
- **No `DONE` on a partial merge.** If the follow-up PR is still open, a gate is outstanding, or the migration was not run, the work is not complete and the heading waits. `{{SKILL_PREFIX}}-session-name` trusts the caller on this, which makes it this skill's judgement to get right.

## Output shape

Fixed and compact. One line per phase with its verdict, only the findings that matter underneath, then the two closing lists. No preamble, no recap.

```
Kind             feature merge, feature/052-user-export into main
Phase 1 gate     PASS   checks green (full tier), pest green on 3e1d9b0 (mandatory), main merged in, no out-of-order migrations
Phase 2 merge    DONE   #441 squashed to main as 9f2a1c4
Phase 3 local    DONE   pulled, 2 migrations run, bounce needed
Phase 4 regen    DONE   roadmap rebuilt (2 items now homed in no epic), reference rebuilt
Phase 5 docs PR  DONE   #442 opened and merged, generated paths only

The operator's actions
- /code-review 441 outstanding
- Bounce the dev stack: stop and restart make dev
- Click Sync in the claude.ai desktop app.

Session name: /rename DONE 2026-10-05 spec-052 user export
```

A stop reports the phase it stopped in, what is red, and the two lists from Phase 1. It does not report the phases it never reached.

## Out of scope

- **Launching `/code-review`.** the operator triggers that one, always.
- **Starting, stopping or bouncing the dev stack**, on either machine.
- **Any destructive database command.** Plain `migrate` on the operator's explicit yes in Phase 3 is the whole of the permission.
- **Cutting a feature branch.** `{{SKILL_PREFIX}}-promote-backlog-spec` and `{{SKILL_PREFIX}}-promote-wp` cut them at promotion, and `{{SKILL_PREFIX}}-fix-branch` cuts fix branches.
- **Opening the feature PR**, writing its description, or doing the work in it. The merge starts from a PR that is already ready.
- **Rebasing, force-pushing, or any history rewrite.**
- **Cutting a release.** The release-please PR is a different thing merged for a different reason, and merging it publishes a release and fires the deploy. If the PR handed to this skill is `release-please--branches--main`, stop and say so.
- **Acting on the other machine**, or inferring anything about its state.
- **Hand-editing a generated document.** `docs/reference.md`, `docs/claude-transfer/` and `docs/roadmap/` are all output. Fix the source and regenerate.
