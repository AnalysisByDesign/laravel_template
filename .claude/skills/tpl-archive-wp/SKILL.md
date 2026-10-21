---
name: tpl-archive-wp
description: Archive one delivered work package by moving it to docs/work-packages/done/, stripping its batch number, restating its status line, removing its row from the folder README table, and rewriting every reference across the repository. One package per invocation; leaves the change staged for the operator to review and commit.
compatibility: Requires the docs/work-packages/ layout and conventions described in docs/work-packages/README.md
model: haiku
metadata:
  author: laravel-template
---

# Archive a Delivered Work Package

Move a work package whose work has been delivered out of the live folder and into `docs/work-packages/done/`, keeping every reference in the repository resolving. This is the work-package sibling of the `tpl-archive-spec` skill, and it is deliberately not the same operation: a spec archive is a pure relocation, whereas a work package **changes its filename and its status line on the way**.

Three things make this more than a `git mv`, and all three are conventions set in `docs/work-packages/README.md`:

- **The batch number is stripped.** Batch numbers name the batch currently being worked and are reused, so an archived `wp-000-thing.md` would compete for a number a live package now holds. It becomes `wp-thing.md` in the same commit as the move.
- **Because the filename changes, bare filename references change too.** Archiving a spec leaves `spec-013` meaning the same thing everywhere; archiving `wp-000-rollup.md` does not, because there is no longer a file by that name. This is the opposite of the rule in `tpl-archive-spec` and is the single easiest thing to get wrong here.
- **The status line is rewritten** to say what the package produced. `docs/work-packages/README.md` requires it, because a delivered package whose status still says "open, not started" is worse than no status at all.

**Input**: one work package identifier. A slug (`rollup`), a numbered filename (`wp-000-rollup.md`), or anything in between. Match on the slug with the batch number tolerated, since the number is the part being removed.

**One package per invocation.** If asked to archive several, refuse and do them one at a time across separate invocations, each with its own reviewable diff. Batch moves are explicitly not wanted, for the same reason they are not wanted for specs: the reference sweep is the risky half, and it needs a diff a person can actually read.

## 1. Preconditions

Check all of these before touching anything. If any fails, stop, report which one and why, and make no changes at all.

1. **Clean working tree**: `git status --porcelain` is empty. The move must land as its own reviewable change, not mixed into unrelated edits.
2. **The package exists in the live location**: exactly one `docs/work-packages/wp-*<slug>*.md` at the folder root, or in `backlog/` when it was abandoned or superseded without being started, and not already in `done/`. If the slug matches more than one file, stop and list them rather than picking.
3. **The work has genuinely been delivered.** Read the status line. `docs/work-packages/done/README.md` sets the bar: a package arrives in `done/` because the work happened, and an abandoned or superseded package also belongs there provided its status says which. So:
   - Status says delivered, done, closed, shipped, superseded, or abandoned: proceed.
   - Status says open, captured, not started, draft, parked, or anything ambiguous: **stop and ask the operator**. Do not infer delivery from the presence of ticked checkboxes, from a linked merged PR, or from the work looking finished. Whether a package is done is the operator's call, not a reading of its contents.
4. **No collision in `done/`**: no `docs/work-packages/done/wp-<slug>.md` already exists. If one does, this is very likely a squash-merge duplication (the rename half of a squash not removing the old name) rather than a genuine clash. Stop, say so, and let the operator resolve it.
5. **Nothing live is gated on it.** Grep the live folder for other packages naming this one on their `**Gate**` line. A gate pointing at a package being archived is not a blocker to the move, because delivery is exactly what clears a gate, but it **must be named in the report** so the operator can update the dependent package's gate line themselves.

Which packages get archived is the operator's judgement call, made per package when they invoke this skill. Never suggest or perform archiving unprompted.

## 2. Move, stripping the batch number

```bash
git mv docs/work-packages/wp-NNN-<slug>.md docs/work-packages/done/wp-<slug>.md
```

A sequence letter after the number (`wp-000b-<slug>.md`) is part of the batch number and comes off with it; read `NNN` below as `NNN` plus any letter.

If the package carries no batch number, the filename does not change and only the folder does. That is normal: unnumbered means the package was not in a current batch, not that something is missing.

**A package directory** (the shape `competitor-research-2026-09/` takes, per the folder README's "Directories" section) moves intact:

```bash
git mv docs/work-packages/<dir-name> docs/work-packages/done/<dir-name>
```

Do not edit, prune, or reorganise its contents, and do not rename it. Directory names are dated rather than batched, so there is no number to strip.

## 3. Restate the status line

Edit the status line, and **nothing else in the document**.

The status line must end up saying what the package produced and when. `docs/work-packages/README.md` requires this as part of the move; `docs/work-packages/done/README.md` explains why the distinction between delivered and superseded has to survive, because "we did this" and "we decided not to" are answers to different questions and both get asked later.

- **If the status line already records the outcome and the date**, leave it. It is already doing its job, and rewriting it would be churn.
- **If it records the outcome but not the date**, add the date.
- **If it does not record the outcome**, ask the operator for one sentence saying what the package produced. **Never invent it.** A fabricated outcome in a document nobody will re-read is exactly the shadow-archive failure the folder conventions exist to prevent, and it is unfalsifiable once written.

Everything below the status line is untouched. In particular:

- **Do not tick checkboxes** to make the document look finished.
- **Do not revise findings, decisions or dates.** `docs/work-packages/done/README.md` is explicit that these are not revised, because correcting them would falsify what was true at the time.
- **Do not reword the substance** of anything, including historical notes inside the document.

## 4. Update the folder README table

`docs/work-packages/README.md` holds a table of every live package with its batch, owner, gate and standing, and it says in terms to keep that table current when a package moves to `done/`. Remove the archived package's row.

That is the whole edit. Two things around it are deliberately out of scope:

- **The paragraph introducing the table carries a dated snapshot** ("Every live package, as of DATE", followed by prose about what was archived that day). That prose is a historical record and must not be reworded. Refreshing the date alone would leave the sentences after it describing the wrong day. Leave the paragraph as written and **report that its "as of" date now predates the table**, so the operator can restate it if they want to.
- **`docs/work-packages/done/README.md` has no index table**, so there is nothing to add there. It carries conventions, not contents.

## 5. Rewrite references

Sweep the whole repository and repoint every reference. `docs/work-packages/done/README.md` gives the governing principle: findings and dates are preserved, but **references are not covered by that**, because a path that no longer resolves tells a reader neither what was true then nor where the document is now.

Both halves of the name change, so run both greps:

```bash
grep -rn --exclude-dir=.git --exclude-dir=vendor --exclude-dir=node_modules \
  --exclude-dir=storage --exclude-dir=claude-transfer --exclude=CHANGELOG.md \
  -e "docs/work-packages/wp-NNN-<slug>" -e "wp-NNN-<slug>" .
```

### What is rewritten

**Only genuine file references.** A reference qualifies if it names a location on disk: it contains a path separator, or a `.md` extension, or otherwise identifies a directory.

- `docs/work-packages/wp-NNN-<slug>.md` becomes `docs/work-packages/done/wp-<slug>.md`
- A bare `wp-NNN-<slug>.md`, with no directory, becomes `wp-<slug>.md`. The folder README table and the `**Gate**` lines in other packages both use this form.

**A naive folder substitution is wrong.** `s|docs/work-packages/|docs/work-packages/done/|` leaves the batch number in place and produces a path that does not exist. The number strip and the folder change are one edit, not two.

Apply each rewrite as an exact string replacement of the reference, changing nothing else on the line.

### What is left alone

- **Prose asserting something about the past.** "PR #12 renamed it to `wp-002-example-package...`" describes a past event correctly, and the old numbered name is part of the fact. This category is larger here than it is for specs, because every archived package leaves behind prose citing a filename that was accurate when written. The test is whether the sentence asserts something about the past; if it does, the old name stays.
- **Bare slugs with no `.md` and no path.** Prose naming the work rather than the file does not change, because the work is still called the same thing.
- **Matches already pointing at `done/`.**

### Files skipped, and why

- **`CHANGELOG.md`**: release-please generates and owns it, and its entries quote historical commit messages.
- **`docs/reference.md`**: generated by the `tpl-prepare-docs-reference` skill, so a match there is a copy of one already found at the real path, and a hand edit is undone by the next regeneration.
- **`docs/claude-transfer/`**: every entry is a file-level symlink rebuilt from `members.txt`, so a match inside it is the same match already found at the real path, and writing through one edits the real file twice and risks replacing the link with a regular file.

**`docs/claude-transfer/members.txt` is not skipped, and needs a deliberate check.** Membership currently includes the current batch by glob (`docs/work-packages/wp-000*.md`), so archiving a numbered package drops it from the subset automatically with no edit needed. If `members.txt` ever names this package explicitly, remove that line. Either way the subset has changed, which section 7 covers.

After rewriting, rerun both greps. Any remaining match must be either a deliberate skip, explained in the report, or a bug in the sweep.

## 6. Check for a duplicate

Run the check the folder README documents, which catches the squash-merge duplication that put one package on `main` twice under two names:

```sh
for d in docs/work-packages docs/work-packages/done; do
  ls "$d" | grep '\.md$' | grep -v '^README\.md$'
done | sed -E 's/^(wp)-[0-9]{3}[a-z]?-/\1-/' | sort | uniq -d
```

Silence means clean. Any output means the same slug now exists twice and the move needs unpicking before it is staged.

**This command was corrected on 2026-10-05**, here and in the folder README and `tpl-merge`. It stripped a leading `NNN-`, which is where the number sat under the older naming, so under the current convention (the number after the `wp-` prefix) it stripped nothing and reported clean against a genuine duplicate. The note that used to sit here said to strip `wp-[0-9]{3}-` as well, and the command beside it did not: a correct instruction next to a wrong command is read as a correct command, which is how this survived a month of clean runs.

## 7. Stage and report

Stage everything (`git add` the move, the edited document, the README, and the rewritten files) but **do not commit**. The operator reviews the diff and commits themselves.

Report so the diff can be checked rather than trusted:

- The move, old path to new path, naming the batch number stripped.
- The status line, before and after, or a note that it already said what was needed.
- The README table row removed, and the reminder that the paragraph's "as of" date now predates the table.
- Every file that had references rewritten, with a count per file, separating path rewrites from bare filename rewrites.
- Every match deliberately left alone, grouped by why.
- **Any live package whose gate line named this one**, since that gate is now satisfied and its wording is the operator's to update.
- The duplicate check result.
- A reminder that `docs/reference.md` is now stale, and that if the package was in the mobile subset (`wp-000-*` currently is, by glob) `docs/claude-transfer/` holds a dead symlink until regenerated. Suggest rerunning the `tpl-prepare-docs-reference` skill, which rebuilds both.

## Out of scope

- **Deciding whether a package is done.** That is the operator's, always, and precondition 3 stops rather than guesses.
- **Writing the outcome.** If the status line does not say what the package produced, ask; never compose one.
- Deleting anything. Nothing is removed, only relocated.
- Editing any part of a document other than its status line.
- Ticking checkboxes, closing GitHub issues, or any other act of finishing the work the package describes. This skill records that work finished; it does not finish it.
- Re-batching a package that is staying live. Numbers change here only as a consequence of moving to `done/`.
- Archiving specs. That is `tpl-archive-spec`, and the two are not interchangeable.
- Batch or scheduled archiving.
- Committing or pushing.
