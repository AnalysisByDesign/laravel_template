---
name: "{{SKILL_PREFIX}}-promote-backlog-spec"
description: Promote one backlog item into the live spec view, allocating a spec number confirmed against the repository, renaming ft- to spec-NNN-, restating the document's identity block, cutting and pushing the spec's feature/NNN-slug branch from main, and rewriting every reference. One item per invocation; leaves the document change staged for the operator to review and commit.
compatibility: Requires the docs/features/ layout described in CLAUDE.md and the convention in docs/features/backlog/README.md
model: sonnet
metadata:
  author: "{{GITHUB_OWNER}}"
---

# Promote a Backlog Item into the Live Spec View

Move one captured item out of `docs/features/backlog/` and into the live working view as a numbered spec, because work on it is about to begin.

`docs/features/` root holds live and in-flight work, `done/` holds shipped work, and `backlog/` holds captured intent nobody is working on yet. This skill crosses that boundary in one direction only. **The opposite move is `{{SKILL_PREFIX}}-demote-active-spec`**, and archiving a shipped spec is `{{SKILL_PREFIX}}-archive-spec`.

The filename prefix states what a document is: `ft-` a feature capture, `wp-` a work package, `spec-` something ready for action. Crossing this boundary therefore changes the prefix, not just the folder.

**A number claims a position in the build order, so backlog items do not have one.** This is the convention set in `docs/features/backlog/README.md`: backlog filenames are descriptive and carry an `ft-` prefix, a number is allocated only at promotion time, and it is confirmed against the repository rather than against a manifest. Allocating that number is the load-bearing half of this skill, and section 2 exists because getting it wrong is easy and expensive.

**Input**: one backlog item, named by slug or filename. `ft-` and the `.md` extension are both optional.

**One item per invocation.** If asked to promote several, refuse and do them one at a time across separate invocations, each with its own reviewable diff. The exception is a `{{SKILL_PREFIX}}-review-backlog` ceremony, which promotes a batch deliberately and manages the clean-tree precondition itself; see the note at the end of section 1.

## 1. Preconditions

Check all of these before touching anything. If any fails, stop, report which one and why, and make no changes at all.

1. **Clean working tree**: `git status --porcelain` is empty. The move must land as its own reviewable change, not mixed into unrelated edits.
2. **The item exists in the backlog**: exactly one matching `docs/features/backlog/ft-<slug>.md`, `docs/features/backlog/ft-NNN-<slug>.md` (a batch number) or the older `docs/features/backlog/NNN-ft-<slug>.md`. A leading `NNN-` is a **priority prefix**, documented in that folder's README: it is the operator's sort key for prioritising the backlog, not a spec number, and it is dropped at promotion. Match on the slug, tolerate the prefix. An item that carries a number with no `ft-` after it predates a convention change; report it and ask before proceeding.
3. **A number is allocated** per section 2.
4. **Not a split parent**: an item carrying a `**Slices**` list is the parent of a split and is never promoted itself. Stop and name its slices; promote those, in order.
5. **No collision**: nothing named `spec-NNN-*` exists at the `docs/features/` root, in `done/`, or in `dropped/`, and no `specs/NNN-*/` directory, `NNN-*` branch or `feature/NNN-*` branch exists, locally or on `origin`.

Which items get promoted is the operator's judgement call, made per item when they invoke this skill. Never suggest or perform a promotion unprompted.

**When run inside the `{{SKILL_PREFIX}}-review-backlog` ceremony**, precondition 1 cannot hold from the second item onwards, because the ceremony promotes several items back to back and leaves each staged. That is expected: the clean-tree check belongs to the ceremony as a whole, run once at the start. Say in the report that the deviation was deliberate, so it is visible rather than silent.

## 1a. Right-size it first

Before the product owner check, run the `{{SKILL_PREFIX}}-split-feature` skill against the item, unless it already ran on this item earlier in the same ceremony or session. A capture is right-sized before it gets a number, never at `/speckit.clarify` (`CLAUDE.md`, "Spec grain and timing").

- **Keep whole**: continue with the same item.
- **Split approved**: stop this promotion. The original is now a parent and is not promotable. Report the slices and that the next promotion, when the operator asks for it, is slice 1.
- **The item is itself a slice** (it carries a `**Parent**` line): the split already happened, so skip the skill. If an earlier slice of the same parent is still in the backlog, say so before going on, since slices are built in order. Surface it; do not refuse.

## 1b. The product owner check

Before allocating a number, run the product owner node against the item, exactly as the `{{SKILL_PREFIX}}-po-check` skill describes: assemble the bundle with `tools/po-check/context.py`, launch the `product-owner` agent, validate the verdict with `tools/po-check/verdict.py check`. Then branch on the verdict, in plain steps rather than judgement:

- **`promote`**: continue to section 2.
- **`challenge`** or **`defer`**: show the operator the node's reason, what it displaces, the principle conflicts, and on a defer the recommended batch. Ask them to choose `proceed` or `withdraw`. Nothing else is accepted.
  - **`withdraw`**: stop. Report the verdict and that nothing changed.
  - **`proceed`**: ask for their reason, in their words. An empty reason is not a reason; ask again. Then append the override entry, which the node itself can never do:

    ```bash
    python3 tools/po-check/verdict.py override <scratch>/po-verdict.json \
      --feature docs/features/backlog/<file> --reason "<the operator's reason>" --date <today>
    ```

    That appends to `docs/ceremonies/po-overrides.md`, creating it with its header on the first entry. Stage it with the rest of the promotion. Then continue to section 2.

The node does not refuse and this skill does not refuse on its behalf. It makes the cost visible and requires the reason to be written down. Inside a `{{SKILL_PREFIX}}-review-backlog` ceremony the check runs per item, the same way, and each override entry cites the ceremony's record.

## 2. Allocating a number

Numbers are confirmed against the repository on `main`, **never against `docs/reference.md`**. A manifest or generated index can lag the repository and promise free numbers that are already in use.

Enumerate what is genuinely taken:

```bash
git fetch origin main --quiet
git ls-tree -r --name-only origin/main | grep -oE 'spec-[0-9]{3}|specs/[0-9]{3}' | sort -u
git branch --all | grep -oE '[0-9]{3}-' | sort -u
```

Cross-check the working tree too, since an unstaged new spec will not be on `main` yet. Report the full taken set and the number chosen.

**A number released by `{{SKILL_PREFIX}}-demote-active-spec` returns to the pool and may be reused, but reuse is the hazardous option**: for a period, the same identifier means two different specs in prose written on either side of the change, so documents citing "spec-NNN" can silently mean the previous holder.

**Prefer the next unused number.** If the operator asks for a released number specifically, first confirm that no bare `spec-NNN` reference anywhere still means the previous holder, and say so in the report.

## 3. Move and restate the document

Move with git so history follows, swapping `ft-` for the allocated number and dropping any batch number or priority prefix, since the allocated number now carries the ordering:

```bash
git mv docs/features/backlog/ft-<slug>.md docs/features/spec-NNN-<slug>.md
# or, when the item carried a batch number:
git mv docs/features/backlog/ft-BBB-<slug>.md docs/features/spec-NNN-<slug>.md
```

Unlike `{{SKILL_PREFIX}}-archive-spec`, this skill **does** edit the document, because the file no longer carries its scheduling state in the filename alone. Change only the identity block, never the substance:

- **Heading**: `# Backlog: Title` becomes `# Spec-NNN: Title`.
- **Status line**: state the number and the date it was allocated.
- **Target branch line**: add `**Target branch**: \`feature/NNN-<slug>\``. This is the one piece of data the feature-branch model threads through: every task PR for this spec targets it, and `{{SKILL_PREFIX}}-merge` checks a task PR's base against it.
- **A status comment recording a previously released number**, if the document carries one from an earlier demotion, stays as history. Say the number was released and when, rather than deleting the fact.

Everything below the identity block is untouched. Never reword, reorder, or update the substance of a document or of a historical record inside it.

Also update `docs/features/backlog/README.md`, whose "Current contents" table is the index for that folder: remove the item's row.

## 3a. Cut the feature branch

Every spec gets its own long-lived feature branch, cut from `main` at promotion. Task branches are cut from it and their PRs target it; it merges into `main` once, as the spec's release gate.

Cut it from `origin/main` without leaving the current branch, then push it:

```bash
git fetch origin main --quiet
git branch "feature/NNN-<slug>" origin/main
git push -u origin "feature/NNN-<slug>"
```

Pushing the branch fires no workflow: `ci.yml` runs on pull requests only, and `release-please.yml` on pushes to `main`. **Ask the operator before the push**, since it is the one step here that reaches `origin`, and if they decline, leave the local branch and say the push is outstanding.

The promotion itself (the move, the identity block, the rewritten references) stays staged on the branch the operator ran this skill from and reaches `main` through its own PR, as before, so the number is claimed on `main` quickly. The feature branch does not carry the promotion commit until `main` is next merged into it, which is harmless.

`/speckit.specify` is then run **from the feature branch**. Its `before_specify` hook cuts a branch named `NNN-<short-name>` from wherever it runs, so run from the feature branch it creates the first task branch, and the document phases reach the feature branch as its first task PR.

## 4. Rewrite references

**Only genuine file paths are rewritten.** A reference qualifies if it names a location on disk: it contains a path separator, or a `.md` extension, or otherwise identifies a directory.

- `docs/features/backlog/ft-some-slug.md` becomes `docs/features/spec-NNN-some-slug.md`

```bash
grep -rn --exclude-dir=.git --exclude-dir=vendor --exclude-dir=node_modules \
  --exclude-dir=storage --exclude-dir=claude-transfer --exclude=CHANGELOG.md \
  -e "backlog/ft-<slug>" -e "ft-<slug>" .
```

- Skip `CHANGELOG.md`: release-please generates and owns it, and its entries quote historical commit messages.
- Skip `docs/reference.md`: it is generated by the `{{SKILL_PREFIX}}-prepare-docs-reference` skill, so a match there is a copy of one already found at the real path, and editing it by hand is undone by the next regeneration.
- Skip `docs/claude-transfer/`: every entry there is a file-level symlink rebuilt from `members.txt` by the same skill, so a match inside it is the same match already found at the real path, and editing through one writes the real file twice and risks replacing the link with a regular file. Its `reference.md` is generated too.
- Skip matches already pointing at the destination path.
- Apply each rewrite with an exact string replacement of the path, changing nothing else on the line.

### Adding the number to prose, conservatively

The item now has an identifier it did not have before, so some prose reads better with it. **This is the only interpretive edit in this skill, and the bar is high.**

Run the same sweep against the descriptive name and add the number **only where a document genuinely benefits**: a build-order discussion, a dependency statement, a roadmap line. Prose that reads correctly without a number does not need one, and a document written before the number existed is not wrong for lacking it.

**Never add a number to a historical record.** A dated note or close-out describing the item before it was numbered is correct as written.

After rewriting, rerun the sweep. Any remaining match must be either a deliberate skip, explained in the report, or a bug in the sweep.

## 5. Stage and report

Stage everything (`git add` the move, the edited document, the backlog README, and the rewritten files) but **do not commit**. The operator reviews the diff and commits themselves.

Report so the diff can be checked rather than trusted:

- The product owner verdict, and if the operator overrode it, that the entry was appended to `docs/ceremonies/po-overrides.md`.
- The move, old path to new path.
- **The number allocated, and the full taken set it was chosen against.** If it was a reused number, say so explicitly and say what was checked.
- The identity block edits, before and after.
- The feature branch: cut from which `origin/main` commit, and whether it was pushed.
- Every file that had references rewritten, with a count per file, separating path rewrites from prose additions.
- Every match deliberately left alone, and why.
- Whether the clean-tree precondition was waived for a ceremony run.
- A reminder that `docs/reference.md` is now stale, since `docs/features/` is in the synced set, and that the mobile subset picks up numbered feature documents by glob, so `docs/claude-transfer/` needs rebuilding. Suggest rerunning the `{{SKILL_PREFIX}}-prepare-docs-reference` skill, which does both.

## Out of scope

- **Demoting a spec to the backlog.** That is `{{SKILL_PREFIX}}-demote-active-spec`.
- **Archiving a shipped spec.** That is `{{SKILL_PREFIX}}-archive-spec`.
- Renumbering a spec that is staying where it is. Numbers change here only as a consequence of crossing the backlog boundary.
- Deleting anything. Nothing is removed, only relocated.
- Editing any part of a document other than its identity block.
- Touching `specs/` at all. A backlog item has no spec-kit directory, and if one exists under the allocated number the precondition already failed.
- Choosing which items to promote, and choosing whether to reuse a released number.
- Batch or scheduled promotion, outside a `{{SKILL_PREFIX}}-review-backlog` ceremony.
- Committing, or pushing anything other than the new feature branch.
