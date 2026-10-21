---
name: tpl-fix-branch
description: Cut one branch for fixing one or several GitHub issues, asking once which branch they belong to by listing the open feature/* branches with main as the last option. A fix for a feature in flight branches from that feature and is tested when the feature merges; a production fix with no owning feature branches from main and must pass pest before it merges, so batching several production fixes costs one pest run instead of one each. Records the target on every issue. Never writes the fix itself.
compatibility: Requires gh authenticated against this repository's GitHub remote
model: haiku
metadata:
  author: laravel-template
---

# Cut a Fix Branch

Fixes have no backlog and no promotion, so nothing records where a fix belongs until something asks. This skill asks, once, at the start, and records the answer where `tpl-merge` will look for it. It is the fix lane's half of the feature-branch model.

**Input**: one or more GitHub issue numbers, with or without `#`, separated by spaces or commas: `701`, `#701 #702 #705`.

## Why the target matters

- **A fix for a feature in flight** belongs on that feature's branch. It is cut from it, its PR targets it, and it runs no pest on its own branch: the feature's merge into `main` runs pest over everything the feature collected, the fix included.
- **A fix to something already live**, with no feature branch that owns it, targets `main`. There is no later merge to catch a regression, so pest is mandatory on it before it merges, and `tpl-merge` enforces that for any `fix/*` branch into `main`.

Choosing wrong in the first direction costs a pest run. Choosing wrong in the second ships an untested change, which is why the choice is the operator's and is asked rather than inferred.

## Several issues on one branch

Several issues share a branch when they share a target and are worth reviewing together. **The minutes are the reason it exists**: each production fix into `main` must pass pest, a full-suite run of Actions time, so five separate fixes cost five runs and one branch carrying all five costs one. The trade is a larger PR and a single merge, so one failing fix holds back the others.

**One branch has one target.** If the operator says the issues belong to different features, or some to a feature and some to `main`, do not split them yourself: say which go where and run the skill once per target.

## 1. Preconditions

Check every issue before changing anything. If any fails, stop, name the issue and the reason, and change nothing for any of them; a branch cut for some of the batch is a half-applied state the operator did not ask for.

1. **Clean working tree**: `git status --porcelain` is empty, because the skill switches branch.
2. **Each issue exists and is open**: `gh issue view <N> --json number,title,state,labels,body`.
3. **No fix branch for any of them already**: no local or remote branch whose name carries the issue number as a segment (`fix/<N>-*`, or `fix/*-<N>-*` from an earlier batch), and no open PR whose body says `Fixes #<N>` or `Closes #<N>` (`gh pr list --search "<N> in:body" --state open`). Parallel sessions take the same issues; if one exists, stop and name it.
4. **No more than eight issues.** Past that a PR stops being something the operator can read through in one sitting, which `CLAUDE.md` requires before a merge. Ask them to split the list.

**Flag, do not refuse, an issue that asks for operator review** (the areas `CLAUDE.md` "Sensitive areas" and the constitution reserve for operator review). Batching one with ordinary fixes puts the whole PR behind that review. Name it in the question in step 2 so the choice is made knowingly.

## 2. Ask which branch they belong to

```bash
git fetch --prune origin
git ls-remote --heads origin 'feature/*' | sed 's|.*refs/heads/||'
```

For each feature branch, read the document that names it: the spec in `docs/features/` or the work package in `docs/work-packages/` whose `**Target branch**` line matches. Show the operator each one with that document's title, and every issue's title and first lines, then ask **once** with `AskUserQuestion`. List the feature branches first and `main` last, labelled as a production fix with mandatory pest, then a last option to stop because the issues belong to different targets. Recommend nothing: the issue text rarely says which feature introduced the defect, and guessing is the failure this skill exists to stop.

When no feature branch exists the question still runs, with `main` and stop as its options. A target is never assumed.

## 3. Cut and push

The branch name carries the issue numbers, so this skill and parallel sessions can find it from any one of them:

- **One issue**: `fix/<N>-<slug>`.
- **Two or three**: `fix/<N1>-<N2>-<N3>-<slug>`, numbers in ascending order.
- **Four to eight**: `fix/<lowest>-and-<count minus one>-more-<slug>`, for example `fix/701-and-4-more-policy-gates`. The numbers are on the issues and in the PR body, so the name need not list them all.

The slug is two to four words: from the issue title for one issue, and from what the issues share for several. If they share nothing that fits in four words, use `batch` and the date, as in `fix/701-and-4-more-batch-1017`; a branch name claiming a theme the issues do not have misleads whoever picks it up.

```bash
git switch -c "fix/<name>" "origin/<target>"
git push -u origin "fix/<name>"
```

Pushing fires no workflow. Then record the target on every issue, so it survives this session. Pace the comments about ten seconds apart once there are more than two, since GitHub's secondary rate limit on rapid writes can stop a run after two issues:

```bash
gh issue comment <N> --body "Fix branch \`fix/<name>\`, targeting \`<target>\`, together with #<others>."
```

Leave out the "together with" clause for a single issue. If a comment fails, report the actual error and carry on with the rest: the branch already exists, and stopping halfway leaves some issues recorded and some not.

## 4. Report

```
Issues      #701 Admin export skips the policy check
            #702 ...
Branch      fix/701-702-policy-gates, cut from origin/<target> at <sha>, pushed
Target      <target>   (pest: on the feature merge | mandatory before merge, once for the batch)
Review      #701 needs operator review before implementation   <- only when flagged in step 1
Recorded    on #701, #702

When the fixes are done, open one PR with:
  gh pr create --base <target> --title "fix(<scope>): <summary>" \
    --body "Fixes #701
Fixes #702
...
Target branch: <target>"
```

**One closing keyword per issue, each on its own line.** `Fixes #701, #702` closes only #701; GitHub needs the keyword repeated. The PR body carries `Target branch: <target>` because `tpl-merge` checks the PR's base against it.

For a fix into a feature branch, the keywords close the issues only when the feature reaches `main`, since GitHub closes issues on merges to the default branch; say so, so issues left open after the task merge are not read as a mistake.

Work the issues as separate commits on the branch, one Conventional Commits subject per issue, so the PR reads as a list and one fix can be reverted alone before the squash.

## Out of scope

- Writing the fixes, opening the PR, or merging it.
- Choosing the target branch, or deciding which issues belong together.
- Splitting a mixed batch across targets; it reports the split and the operator runs the skill per target.
- Fixes with no issue. Raise the issue first; it is where the target is recorded.
- Cutting feature branches, which `tpl-promote-backlog-spec` and `tpl-promote-wp` do at promotion.
