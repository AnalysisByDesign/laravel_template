---
name: "{{SKILL_PREFIX}}-demote-active-spec"
description: Demote one not-yet-started spec from the live view into docs/features/backlog/, releasing its number, renaming spec-NNN- to ft-, restating the document's identity block and rewriting every reference including bare spec-NNN identifiers. One spec per invocation; leaves the change staged for the operator to review and commit.
compatibility: Requires the docs/features/ layout described in CLAUDE.md and the convention in docs/features/backlog/README.md
model: sonnet
metadata:
  author: "{{GITHUB_OWNER}}"
---

# Demote an Unstarted Spec to the Backlog

Move one numbered spec out of the live working view into `docs/features/backlog/`, because it is captured intent that nobody is going to work on yet.

`docs/features/` root holds live and in-flight work, `done/` holds shipped work, and `backlog/` holds captured intent nobody is working on yet. This skill crosses that boundary in one direction only. **The opposite move is `{{SKILL_PREFIX}}-promote-backlog-spec`**, and archiving a shipped spec is `{{SKILL_PREFIX}}-archive-spec`.

The filename prefix states what a document is: `ft-` a feature capture, `wp-` a work package, `spec-` something ready for action. Crossing this boundary therefore changes the prefix, not just the folder.

**This is the harder of the two directions, and section 3 is why.** Promotion gives a document an identifier it did not have. Demotion takes one away, so every bare `spec-NNN` in the repository has to be read and classified rather than swept. Do not start the sweep until that section has been read in full.

**Input**: one spec identifier, for example `041` or `spec-041`. Normalise to the three-digit number `NNN`.

**One spec per invocation.** If asked to demote several, refuse and do them one at a time across separate invocations, each with its own reviewable diff.

## 1. Preconditions

Check all of these before touching anything. If any fails, stop, report which one and why, and make no changes at all.

1. **Clean working tree**: `git status --porcelain` is empty. The move must land as its own reviewable change, not mixed into unrelated edits.
2. **The spec exists in the live location**: exactly one `docs/features/spec-NNN-*.md` at the `docs/features/` root, not in `done/`, not already in `backlog/`.
3. **The spec has genuinely not been started.** "Active" in this skill's name means it sits in the active folder, not that work has begun; a spec that has entered the pipeline does not belong in the backlog. All three must hold:
   - **No `specs/NNN-*/` directory exists**, in `specs/` or in `specs/done/`. A spec-kit directory means the spec has been through `/speckit.specify` at least.
   - **No local or remote branch named `NNN-*` exists** (`git branch --all --list "*NNN-*"`).
   - **The status line says captured, seed, proposed, or equivalent.** If it says shipped, merged, in progress, or anything ambiguous, stop and ask the operator rather than guessing.
4. **A spec that another live document depends on being live** is still eligible; dependency ordering is the operator's judgement, not a precondition. But if the sweep in section 3 reveals a reference that looks like an active dependency, for example a live spec's plan citing this document, **name it in the report**.

Which specs get demoted is the operator's judgement call, made per spec when they invoke this skill. Never suggest or perform a demotion unprompted.

## 2. Move and restate the document

Move with git so history follows, swapping the `spec-NNN-` prefix for `ft-` and keeping the rest of the slug unchanged:

```bash
mkdir -p docs/features/backlog
git mv docs/features/spec-NNN-<slug>.md docs/features/backlog/ft-<slug>.md
```

Unlike `{{SKILL_PREFIX}}-archive-spec`, this skill **does** edit the document, because the file no longer carries its scheduling state in the filename alone. Change only the identity block, never the substance:

- **Heading**: `# Spec-NNN: Title` becomes `# Backlog: Title`.
- **Status line**: `**Status**: Unnumbered backlog item.` followed by the existing capture detail, so a stale header can never imply a number that was never allocated.
- **Feature branch line**: remove it. An unnumbered item has no branch name.
- **Record the released number as history.** Add a status comment saying which number was released and on what date. Say the number was released, rather than deleting the fact that it existed; a reader meeting "spec-NNN" in older prose needs a way to find out what it meant.

Everything below the identity block is untouched. Never reword, reorder, or update the substance of a document or of a historical record inside it.

Also update `docs/features/backlog/README.md`, whose "Current contents" table is the index for that folder: add the item's row.

**The number is now back in the pool.** `{{SKILL_PREFIX}}-promote-backlog-spec` may hand it to a different spec later, and the sweep below is what makes that safe. A number released without the sweep leaves prose that silently means the wrong thing the moment it is reused.

## 3. Rewrite references

Two distinct kinds of reference change, and **only the first is mechanical**.

### Paths

**Only genuine file paths are rewritten.** A reference qualifies if it names a location on disk: it contains a path separator, or a `.md` extension, or otherwise identifies a directory.

- `docs/features/spec-NNN-some-slug.md` becomes `docs/features/backlog/ft-some-slug.md`

```bash
grep -rn --exclude-dir=.git --exclude-dir=vendor --exclude-dir=node_modules \
  --exclude-dir=storage --exclude-dir=claude-transfer --exclude=CHANGELOG.md \
  -e "docs/features/spec-NNN-" .
```

- Skip `CHANGELOG.md`: release-please generates and owns it, and its entries quote historical commit messages.
- Skip `docs/reference.md`: it is generated by the `{{SKILL_PREFIX}}-prepare-docs-reference` skill, so a match there is a copy of one already found at the real path, and editing it by hand is undone by the next regeneration.
- Skip `docs/claude-transfer/`: every entry there is a file-level symlink rebuilt from `members.txt` by the same skill, so a match inside it is the same match already found at the real path, and editing through one writes the real file twice and risks replacing the link with a regular file. Its `reference.md` is generated too.
- Skip matches already pointing at the destination path.
- **Skip series wildcards** such as `docs/features/spec-000-*.md` in `CLAUDE.md`. Single-file globs do get rewritten.
- Apply each rewrite with an exact string replacement of the path, changing nothing else on the line.

### Bare identifiers

The number stops existing, so bare `spec-NNN` references cannot be left alone the way they can when a spec is archived. **This is the interpretive half of the job and it must never be done with a blind substitution.**

```bash
grep -rni --exclude-dir=.git --exclude-dir=vendor --exclude-dir=node_modules \
  --exclude-dir=storage --exclude-dir=claude-transfer --exclude=CHANGELOG.md -e "spec-NNN" .
```

Classify **every** match before editing **any** of them:

1. **Names the spec being demoted.** Rewrite to name the item instead of the number, pointing at the new path where a reference is useful: "the example capture (`docs/features/backlog/ft-002-example-capture.md`)". Do not invent a new short identifier to replace the number.
2. **Names a different spec that happens to share the digits.** Leave it. Numbers recur in dates, version strings, and unrelated identifiers, so read the sentence rather than trusting the match.
3. **Is a historical record**: a changelog note, a work package close-out, a dated amendment block stating what was true at the time. Leave the number intact. "seeds renumbered spec-033 to spec-040" describes a past event correctly and must not be rewritten to match the present.

**Category 3 is the one most easily got wrong.** The test is whether the sentence asserts something about the past. If it does, the old number is part of the fact and changing it falsifies the record.

After rewriting, rerun both greps. Any remaining match must be either a deliberate skip, explained in the report, or a bug in the sweep.

## 4. Stage and report

Stage everything (`git add` the move, the edited document, the backlog README, and the rewritten files) but **do not commit**. The operator reviews the diff and commits themselves.

Report so the diff can be checked rather than trusted:

- The move, old path to new path.
- **The number released**, and the note that it is now available to `{{SKILL_PREFIX}}-promote-backlog-spec`.
- The identity block edits, before and after.
- Every file that had references rewritten, with a count per file, **separating path rewrites from bare identifier rewrites**.
- **Every bare identifier match deliberately left alone, grouped by which of the three categories it fell into.** This is the part of the diff a reviewer most needs help with, because a wrong call here is invisible.
- **Any reference that looked like an active dependency** on this spec.
- A reminder that `docs/reference.md` is now stale, since `docs/features/` is in the synced set, and that the mobile subset picks up numbered feature documents by glob, so the document drops out of it and `docs/claude-transfer/` needs rebuilding. Suggest rerunning the `{{SKILL_PREFIX}}-prepare-docs-reference` skill, which does both.

## Out of scope

- **Promoting a backlog item.** That is `{{SKILL_PREFIX}}-promote-backlog-spec`.
- **Archiving a shipped spec.** That is `{{SKILL_PREFIX}}-archive-spec`.
- **Demoting a spec that has been started.** Precondition 3 stops instead. A spec with a `specs/NNN-*/` directory or a branch is in the pipeline, and taking its number away would break spec-kit's branch-to-directory resolution.
- Assigning a batch number to the demoted item, unless the operator named one when invoking. The batch follows the item's epic.
- Renumbering a spec that is staying where it is. Numbers change here only as a consequence of crossing the backlog boundary.
- Deleting anything. Nothing is removed, only relocated.
- Editing any part of a document other than its identity block.
- Choosing which specs to demote.
- Batch or scheduled moves.
- Committing or pushing.
