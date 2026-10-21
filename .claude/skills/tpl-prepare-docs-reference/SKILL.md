---
name: tpl-prepare-docs-reference
description: Regenerate docs/reference.md, the annotated index of every document the claude.ai project syncs from this repository, then rebuild docs/claude-transfer/ (the small subset uploaded as project files for mobile) and its own reference.md from the membership file, reporting anything that would make either set misleading. Run from post-merge main, as the fourth phase of the tpl-merge skill or by hand on main, never on a branch that has yet to merge.
compatibility: Reads docs/ and .specify/memory/ directly. Rebuilds the file-level symlinks in docs/claude-transfer/ from members.txt.
model: haiku
context: fork
metadata:
  author: laravel-template
---

# Regenerate the documentation reference

The claude.ai project syncs this repository directly through the GitHub connector, so documents arrive under their **real repository paths**. `docs/reference.md` is the index Claude in that project starts from: one line per document, giving its path and what it is for.

Because the connector keeps real paths, there is no filename flattening to undo. What is worth generating is the annotated index itself, plus a check that the synced set is not quietly misleading.

The connector does not reach the Claude mobile app, so a curated subset of about twenty live documents is uploaded to the project as files so it is in context on every surface, and because that upload does flatten paths, the subset carries its own index. The second half of this skill (step 5) keeps that folder and index honest. One invocation covers both halves so they cannot drift apart.

The output file is entirely generated. **Replace it wholesale on every run; never merge with previous content.**

## The synced set

Match this to the claude.ai project's Configure Files selection exactly, or the index describes something other than what the project holds:

- `docs/` in full, **except `docs/sessions/`** (see below)
- `.specify/memory/`
- Root files: `CLAUDE.md`, `CHANGELOG.md`, `README.md`
- **Not** `specs/`, excluded at first sync for size. Several feature documents defer to those directories as authoritative, so the index must say they are absent rather than let a reader assume otherwise.

`docs/sessions/` is excluded because session briefs are staging documents whose content is processed into other artefacts already in the set. **That exclusion has to be made in Configure Files as well**, because syncing `docs/` whole would otherwise bring them in and the index would understate what the project holds. If the ruling is ever reversed, add them here and say so.

## Procedure

### 1. Enumerate and gather candidates

```bash
python3 .claude/skills/tpl-prepare-docs-reference/build.py
```

That writes a candidate index to stdout, one tab-separated line per index entry: `state`, `path`, `section`, `text`.

**The state is what to act on.** Most lines come back already written:

- **`kept`**: the summary a person wrote into the current `docs/reference.md`, handed back with the section it sits under. Carry it across unchanged. Only revisit it if the document's purpose has genuinely changed, not because it is being regenerated.
- **`listed`**: the path appears in a compact listing rather than a summary table, which is how the `done/` folders are indexed. Keep it a bare path; do not promote it to a blank table row.
- **`new`**: not in the current index at all. The `text` column holds the mechanical extract, first heading and first line of prose, as a starting point rather than the answer.

**A path can appear twice, and both lines matter.** "Start here" carries a terse orientation line while the document's own section carries the full one. The `section` column says which is which, so both go back where they came from.

### 2. Write the summaries for the new files

Only `new` lines need a sentence. The mechanical extract is usually a status line, which says when something was created rather than what it is for. **Write each one to answer "why would I open this file".** One sentence, no trailing full stop needed, present tense.

`build.py` hands the existing summaries back, so "replace wholesale" costs only the genuinely new documents.

Two conventions carry over and both earn their place:

- **`done/` folders get a compact, path-only listing**, not per-file summaries. They are archives; a reader needs to know they exist and what the folder holds, not a sentence about each.
- **`docs/features/backlog/` gets per-file summaries.** Backlog items are live, numerous and unfamiliar, and a bare filename tells a reader nothing about whether it is the one they want.

### 3. Run the pre-sync check

```bash
python3 .claude/skills/tpl-prepare-docs-reference/build.py --check
```

It reports, and does not fix:

- **Status lines that contradict the CHANGELOG.** Stale "In implementation" placeholders are the known case.
- **Cited paths that do not resolve.** A document pointing at a file that has moved or gone is worse than one that points nowhere, because the reader trusts it. A line reference on the end of a citation (`path/file.php:49-50`) is ignored, since the file is what has to exist. A citation that is meant not to resolve (a file since deleted that a historical record names, an example, a branch or package name shaped like a path, a document a work package proposes to write) is excused by a line in `unresolved-allow.tsv` beside the script: citing file, cited path and reason, tab separated. Excuse one only when rewriting the path would make the sentence untrue; a renamed or moved target gets its path fixed instead. The check also reports any allowance nothing used, so the file shrinks when a citation is fixed.
- **Files in the synced set the index does not cover**, which is how an index silently rots.

**Still not implemented**, despite the first bullet above: nothing compares status lines against `CHANGELOG.md`. The check reports spec feature documents with no status line at all, which is not the same thing. Treat that bullet as a wanted feature rather than a description of what runs.

Report the findings alongside the regenerated file. **Fixing them is a separate decision**, because a stale status line may be the honest state of a document rather than an error in it.

### 4. Write the file

`docs/reference.md`, with a header stating that it is generated, by this skill, and on what date. Never hand-edit it: the next run overwrites it.

### 5. Rebuild the mobile subset

**Skip this step when invoked with the argument `no-subset`**, which is how `tpl-merge` calls it: stop after step 4 and say the subset was not rebuilt.

```bash
python3 .claude/skills/tpl-prepare-docs-reference/subset.py
```

It reads `docs/claude-transfer/members.txt` (paths and globs relative to the repository root, `!` to exclude), replaces every symlink in `docs/claude-transfer/` with file-level links to the members, and writes `docs/claude-transfer/reference.md`: a header saying it is generated, by this skill, on what date and at what `CHANGELOG.md` version, that it covers only the uploaded subset, and that `docs/reference.md` is the index of the full synced set; then one row per member giving the filename as uploaded, the real repository path, and the summary `docs/reference.md` holds for it. Summaries are never written here. If a member has no row in `docs/reference.md`, add it there (step 2) and re-run; the two indexes must describe a document with the same sentence.

The script refuses to rebuild, exits 2 and lists the reason when: two members share a filename (the upload flattens paths, so one would silently vanish), a member does not exist or a pattern matches nothing, a link does not resolve, or a regular file other than `members.txt` and `reference.md` sits in the folder (a write through a symlink replaces the link with a copy; look at it before deleting anything). `--check` reports without touching the folder.

It also prints a **membership review**, which it reports and never applies: a member whose status line reads as finished (removal candidate), a current-batch work package (`wp-000-*`) or a selected feature (a numbered `docs/features/spec-*.md` with no `specs/NNN-*/` directory) that is not a member (addition candidates), the count of other live packages outside the subset, and a warning past twenty files or thirty. Membership is the operator's call; edit `members.txt` only when they say so.

### 6. Report

Alongside the pre-sync findings, say whether the subset changed: membership, or the content of a member since the last upload (`git log --since` against the date in the previous `docs/claude-transfer/reference.md` header is the quick test). If it did, the operator's upload needs redoing: delete the previous uploads from the project's Context panel and upload the contents of `docs/claude-transfer/` (symlinks resolve on upload; `members.txt` may go along or be skipped). If nothing in the subset changed, Sync alone is enough. Do not commit. When `tpl-merge` is the caller, its fifth phase commits the regenerated files onto their own branch, checks the diff holds nothing but generated output, and opens the follow-up PR; on a hand run, leave them for the operator to review.

## When this runs

**From post-merge `main`, as the fourth phase of the `tpl-merge` skill**. The indexes are only correct when built after the merge, and a copy built on a feature branch collides with every other in-flight branch's copy, which with several machines working features in parallel is the normal case rather than the unlucky one. `tpl-merge` runs this skill once the merge has landed and been pulled, then carries the output in a documentation-only follow-up PR. **When `tpl-merge` is the caller, step 5 (the mobile subset) is skipped**: it rarely changes between merges and is rebuilt only when the operator runs this skill by hand to refresh the mobile upload.

Run it by hand on `main` for the same reasons otherwise: after any documentation change large enough that the index would otherwise mislead, or before the operator syncs. Either way the run belongs on `main`, not on a branch that has yet to merge.

`docs/claude-transfer/` holds only file-level symlinks, `members.txt` and the generated `reference.md`. Never place a symlink by hand; membership lives in `members.txt` so a change is reviewable in a diff. Never edit a document through the folder, and exclude it from repository-wide sweeps: a match inside it is the real file's match again. If Anthropic makes connector content reachable on mobile, the subset half of this skill can be retired; the recorded reason for it is in `CLAUDE.md` under "claude.ai project context".

**It is deliberately not automated**. A pre-push hook that regenerated the file and failed on staleness was considered and judged more machinery than the problem justifies while the sync itself is a manual click: a stale index is visible and cheap to fix, and a hook that fails pushes over a documentation index would cost more attention than it saves. Revisit if the index is ever found stale at a moment it mattered.
