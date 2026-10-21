---
name: tpl-archive-spec
description: Archive one shipped spec by moving its feature document to docs/features/done/ and its spec-kit directory to specs/done/, then rewriting every genuine path reference across the repository. One spec per invocation; leaves the change staged for the operator to review and commit.
compatibility: Requires the docs/features/ and specs/ layout described in CLAUDE.md
model: haiku
context: fork
metadata:
  author: laravel-template
---

# Archive a Shipped Spec

Move a shipped spec out of the working view and into `done/` subfolders, keeping every path reference in the repository resolving. Files move down, never away: still in git history, still readable, just out of the way of live work.

**This skill is for specs only.** Work packages archive differently: they strip their batch number, restate their status line, and therefore change their filename, so bare filename references have to change too. Use `tpl-archive-wp` for anything under `docs/work-packages/`.

**Input**: one spec identifier, e.g. `013` or `spec-013`. Normalise to the three-digit number `NNN`.

**One spec per invocation.** If asked to archive several, refuse and do them one at a time across separate invocations, each with its own reviewable diff. Batch moves are explicitly not wanted.

## 1. Preconditions

Check all of these before touching anything. If any fails, stop, report which one and why, and make no changes at all.

1. **Clean working tree**: `git status --porcelain` is empty. The move must land as its own reviewable change, not mixed into unrelated edits.
2. **The spec exists in the live locations**: exactly one `docs/features/spec-NNN-*.md` and at most one `specs/NNN-*/` directory. Match on the number prefix, not the slug; the feature filename and the spec directory slug are not always identical (e.g. `spec-002-users-staff-and-access-control.md` vs `002-users-staff-access-control/`). A spec with a feature document but no `specs/` directory (never taken through spec-kit) is fine; archive the document alone and say so.
3. **The spec is genuinely shipped**: the feature document's status line says shipped, merged, or equivalent. If the status is ambiguous or says anything like in progress, draft, or captured, stop and ask the operator rather than guessing.
4. **No live branch remains**: no local or remote branch named `NNN-*` exists (`git branch --all --list "*NNN-*"`). A surviving branch means spec-kit may still resolve `specs/NNN-*` by branch name, and the work may not be fully merged.

Which specs get archived is the operator's judgement call, made per spec when they invoke this skill. Never suggest or perform archiving unprompted.

## 2. Move

Create the target directories if they do not exist, then move with git so history follows:

```bash
mkdir -p docs/features/done specs/done
git mv docs/features/spec-NNN-<slug>.md docs/features/done/
git mv specs/NNN-<slug> specs/done/NNN-<slug>    # if the directory exists
```

The `specs/` directory moves intact: spec, plan, tasks, research, data model, contracts, checklists, everything. Do not edit, prune, or reorganise its contents.

## 3. Rewrite path references

Sweep the whole repository for references to the old locations and rewrite them to the new ones. This is the load-bearing step and the easiest to get wrong, so the rule is strict:

**Only genuine file paths are rewritten.** A reference qualifies if it names a location on disk: it contains a path separator, or a `.md` extension, or otherwise identifies a directory.

Rewritten (examples use a placeholder number):

- `docs/features/spec-NNN-some-slug.md` becomes `docs/features/done/spec-NNN-some-slug.md`
- `specs/NNN-some-slug/spec.md` becomes `specs/done/NNN-some-slug/spec.md`
- `specs/NNN-some-slug/` becomes `specs/done/NNN-some-slug/`

**Bare spec identifiers are never touched.** "spec-013", "Spec-013", "spec-013's FR-044", "superseded by spec-013" all name the spec, not its file. The number does not change when the file moves, so neither does the text.

This is a mechanical operation on path strings, not an interpretive one on prose. If a proposed rewrite requires understanding the surrounding sentence, the rule is being applied wrongly; do not make that edit. Historical amendment notes and changelog notes inside documents are in scope where they contain real paths (those paths should keep resolving) and out of scope for any other kind of edit: never reword, reorder, or update the substance of a historical record.

Mechanics:

```bash
grep -rn --exclude-dir=.git --exclude-dir=vendor --exclude-dir=node_modules \
  --exclude-dir=storage --exclude-dir=claude-transfer --exclude=CHANGELOG.md \
  -e "docs/features/spec-NNN-" -e "specs/NNN-" .
```

- Sweep everything the grep covers, including files inside the just-moved `specs/done/NNN-*/` directory and `docs/features/done/` (their internal cross-references must keep resolving too).
- Skip `CHANGELOG.md`: release-please generates and owns it, and its entries quote historical commit messages.
- Skip `docs/reference.md`: it is generated by the `tpl-prepare-docs-reference` skill, so a match there is a copy of one already found at the real path, and editing it by hand is undone by the next regeneration.
- Skip `docs/claude-transfer/`: every entry there is a file-level symlink rebuilt from `members.txt` by the same skill, so a match inside it is the same match already found at the real path, and editing through one writes the real file twice and risks replacing the link with a regular file. Its `reference.md` is generated too.
- Skip matches already pointing at the `done/` path.
- Apply each rewrite with an exact string replacement of the path, changing nothing else on the line.
- After rewriting, rerun the grep. Any remaining match must be either a deliberate skip (explain it in the report) or a bug in the sweep.

## 4. Stage and report

Stage everything (`git add` the moves and the rewritten files) but **do not commit**. The operator reviews the diff and commits themselves.

Report so the diff can be checked rather than trusted:

- The two moves (or one, if there was no `specs/` directory), old path to new path.
- Every file that had references rewritten, with a count per file.
- Any grep matches deliberately left alone and why.
- A reminder that `docs/reference.md` will be stale once a feature document moves, and that `docs/claude-transfer/` will hold a dead symlink if the document was in the mobile subset; suggest rerunning the `tpl-prepare-docs-reference` skill, which rebuilds both.

## Out of scope

- Deleting anything. Nothing is removed, only relocated.
- Editing the substance of any document, including status lines. Archiving records where a file lives, not what it says.
- Any change to `specs/` directory contents beyond their location.
- Choosing which specs to archive.
- Batch or scheduled archiving.
- Committing or pushing.
