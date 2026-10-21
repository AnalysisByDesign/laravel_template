---
name: tpl-review-session-notes
description: Process session briefs from docs/sessions/ into the artefacts they declare (backlog features, work packages, documentation edits and GitHub issues), then mark each brief processed. Named brief, or every unprocessed brief when given no argument. Leaves file changes staged for the operator to review and commit, and raises issues directly.
compatibility: Requires docs/sessions/, the docs/features/backlog/ convention in its README, and an authenticated gh CLI
metadata:
  author: laravel-template
---

# Process a Session Brief

A large amount of the project's design thinking happens in voice conversations with Claude in the claude.ai app. Claude Code cannot read those conversations, so the bridge is a file: Claude in the chat writes one structured brief, the operator pastes it into `docs/sessions/`, and this skill fans it out into the artefacts the repository actually needs.

**The brief is the record, and this skill is mechanical.** Every judgement about what the artefacts should be was made in the conversation and written into the brief. This skill decides nothing. If an item is ambiguous, stop and ask; do not resolve it by inference.

`brief-template.md` in this directory is the format contract and the authority on what a brief may contain. Read it before parsing anything.

## Selecting briefs

- `tpl-review-session-notes <name>` processes that one brief. The `.md` extension and the `docs/sessions/` prefix are both optional.
- `tpl-review-session-notes` with no argument processes **every** brief in `docs/sessions/` whose `status:` is still `unprocessed`, oldest first by filename date.

Either way, **validate everything before changing anything** (section 1). A brief that fails validation stops the whole run, including any sibling briefs that would have passed. Nothing is half-applied: that is the state the `status:` field exists to make impossible.

`README.md` and `brief-template.md` in `docs/sessions/` are not briefs. Skip any file without brief frontmatter.

## 1. Preconditions

Check all of these across the full selected set first. If any fails, stop, say which brief and which item, and change nothing.

1. **Clean working tree**: `git status --porcelain` is empty, so the generated artefacts land as their own reviewable change.
2. **Each named brief exists**: exactly one match in `docs/sessions/`. If a name is ambiguous, list the candidates and ask.
3. **Each brief is unprocessed**: its frontmatter `status:` reads `unprocessed`. If it reads `processed`, stop and report when. Never reprocess without the operator saying so explicitly.
4. **Every item declares a recognised type**: `backlog-feature`, `work-package`, `doc-edit`, or `issue`. An unrecognised or missing type is a stop, not a guess.
5. **Every item has the fields its type requires** (section 2). A missing `Slug`, `Marker`, `Target` or `Kind` is a stop, and so is a missing `Phase` on an item marked `blocker`.
6. **Every `doc-edit` target exists** on disk. An edit naming a file that is not there means the brief was written against a different tree.
7. **No destination collision**, checked across every brief in the run as well as against the repository (for a work package, the same slug at the live root, in `backlog/` or in `done/`, with or without a batch number, counts): no `backlog-feature` or `work-package` item resolves to a path that already exists, and no two items resolve to the same path. Report the collision and ask; it usually means the idea was captured in an earlier session, which is the deduplication case the format does not try to solve on its own.
8. **`gh` is authenticated**, if any brief contains an `issue` item: `gh auth status`.

## 2. Parsing a brief

Items are found by scanning for lines beginning `## Item`. The item title is the rest of that line, after the colon. Immediately below it is a block of `**Field**: value` lines, and everything after that block until the next `## ` heading is the body.

| Type | Required fields | Destination |
|---|---|---|
| `backlog-feature` | `Slug`, `Marker` (`blocker` or `candidate`), `Phase` when `blocker`; `Areas` optional | `docs/features/backlog/ft-<slug>.md` |
| `work-package` | `Slug` | `docs/work-packages/backlog/wp-<slug>.md` |
| `doc-edit` | `Target` (a path that exists) | the named file |
| `issue` | `Kind` (`implementation` or `manual-check`) | GitHub |

**The item title is the artefact's title**: the H1 of a created document, or the title of a created issue. Use it as given.

**A `##` heading inside an item body silently truncates that item.** The contract tells brief writers to start body headings at `###`, but nothing can enforce it from this side, because a stray `##` is indistinguishable from the end of the item. So do not trust the parse blindly: if a body ends abruptly, reads as a fragment, or an item is much shorter than its neighbours, say so and ask before writing anything. Truncation that reaches the repository is worse than a run that stopped to check.

## 3. Create the file artefacts

Work through `backlog-feature` and `work-package` items in the order the brief lists them.

**Do not rewrite the body.** Copy the substance across as written. The brief was composed deliberately, and rewording it here loses the phrasing the operator settled on in the conversation. Add only the identity block the destination convention requires.

A backlog feature opens per `docs/features/backlog/README.md`:

```markdown
# Backlog: <item title>

**Status**: Unnumbered backlog item. Captured <session date> from a planning session. Not through `/speckit.specify`, no number allocated, no committed position in the build order.

**Areas**: <tag>, <tag>

**Marker**: Blocker for Phase <N>.   <- or: Candidate, no committed phase.
```

The `**Areas**` line is required on every feature document and the `docs-guard` CI job fails without it. The tags come from the closed vocabulary in `docs/features/areas.json`, most central area first, normally one to three. If the item carries an `Areas` field, use it, and stop if any value is not a key in `areas.json`: never coin a tag. If the item carries none, which is the usual case for a brief written on mobile, read `areas.json` and choose from the item body, respecting each tag's `not` boundary, then name the chosen tags in the report so the operator can correct them. Run `python3 tools/docs-guard/check_areas.py --require-tags` from the repository root after creating the files.

The marker matters and is not decoration. A blocker must land before work already committed to a phase can ship; a candidate may never be built. Recording it is what makes a backlog sweep fast, because blockers can be reviewed without walking the whole folder. `Phase: unknown` on a blocker is a legitimate answer, not a gap to fill in: write it as unknown rather than inferring a phase the brief did not name.

A work package follows the shape of the existing ones in `docs/work-packages/`, opening with "Read `CLAUDE.md` and prior work packages before starting." It also carries the three fields `docs/work-packages/README.md` requires near the top: `**Status**`, `**Owner**` and `**Gate**`. Status is factual (open, created on the session date, from which brief). Owner and Gate are taken from the body, usually its "Done when" and dependency statements, never invented; if the body gives no basis for one, write `unstated` and say so in the report.

Bodies cross-reference each other by resulting filename, never by item number. Those references should resolve once the files exist; check them before finishing, since a brief written in one pass can still name a sibling whose slug changed.

Then index every created file, since both folders are placed from their README tables rather than by reading each file:

- **Backlog features** go into the "Current contents" table in `docs/features/backlog/README.md`. Four columns: file, one line, phase as declared, origin. The phase cell repeats only what the item's marker and body state (`**P1 blocker**`, "after P1", "P3", or blank when the brief names no phase). Never fill it by inference; attachment to a phase is the `tpl-review-backlog` ceremony's decision. Origin is the session date. Update the item count in the sentence above the table.
- **Work packages** go into the every-package table in `docs/work-packages/README.md`, with the Package cell written `backlog/wp-<slug>.md`. Five columns: band, package, owner, gate, where it stands. Band is blank, because banding is the operator's scheduling and a brief does not set it. A new package lands in `backlog/` because nobody is working on it yet; the operator starts it with `tpl-promote-wp`, which cuts its feature branch. Owner and gate mirror the file's own header lines.

New rows sit in alphabetical order among the unprefixed entries.

## 4. Apply the documentation edits

**Consolidate first.** Group every `doc-edit` item by its `Target`, and treat each target as one piece of work regardless of how many items name it, applying them in the order they appear in the brief. Two separate edits to `CLAUDE.md` are one task. This is the rule most likely to be forgotten and the one whose failure is quiet: two passes over one file produce a merge conflict at best and a lost edit at worst.

**Verify the anchor before applying.** A body should name a section that actually exists in the target. Read the target first and confirm the anchor is really there. If it is not, or if the body says the writer could not see the file's current structure and left placement open, **stop and ask**. Do not place the content somewhere plausible. A confident but wrong placement instruction is the failure mode the contract warns about, and following it is worse than pausing.

Apply the change the body describes and nothing else. These are the only items that modify a file rather than create one, so the blast radius is larger than everything else in the brief combined. Match the surrounding prose style, including the house rule against dashes.

## 5. Raise the issues

Raise each `issue` item with `gh issue create`. The title is the item title; the body is everything below the field block, with a line reading `**Kind**: implementation` or `**Kind**: manual check` added, since a manual check dispatched to an agent is a failure and an implementation task left for a human is a delay.

- **Pace the calls.** Sleep about 10 seconds between creations. GitHub's secondary rate limit on rapid successive writes can stop a run after two issues, and a partially raised set is exactly the mess this skill exists to avoid.
- **No labels.** An unknown label fails the whole call. If labels would help, list what exists with `gh label list` and suggest a mapping in the report, but apply nothing.
- **On failure, report the real error and carry on** with the remaining items. Never retry blindly and never abort the run: the file artefacts are already written, and stopping halfway leaves exactly the half-applied state the preconditions exist to prevent.

## 6. Mark each brief processed

As each brief completes, set its frontmatter `status:` to `processed`, add `processed: <today's date>`, and append a short record to the end listing what was created, including issue numbers. The brief stays in place; it is marked, never moved or deleted.

In a batch run, mark each brief as it finishes rather than all of them at the end, so an interruption leaves an accurate picture of what happened.

The brief is a complete, dated record of the session, which the conversation itself is not. That is why it is kept.

## 7. Stage and report

Stage the new files, the edited files, and the briefs (`git add`), but **do not commit**. The operator reviews the diff and commits themselves. Issues are live by this point and cannot be staged, which is why the report has to be precise about them.

Report so the result can be checked rather than trusted:

- Every file created, with its path, grouped by brief in a batch run.
- Every file edited, with the target and how many items were consolidated into it.
- Every issue raised, with its number and title.
- Every issue that failed, with the actual error text.
- Any item whose body looked truncated or whose anchor could not be verified.
- Any decision in `## Decisions` that names a document but produced no item, since that is usually a doc edit someone forgot to declare.
- A reminder that `docs/reference.md` is now stale, since artefacts land in `docs/features/` and `docs/work-packages/`, both in the synced set, and that the mobile subset in `docs/claude-transfer/` may need a new member; suggest rerunning the `tpl-prepare-docs-reference` skill. The briefs themselves are deliberately not synced or uploaded.

## Out of scope

- Reading claude.ai conversations. This skill reads a file the operator placed. It has no access to the session that produced it.
- Deciding what the artefacts should be, or improving, merging, splitting or reordering the items in a brief.
- Assigning spec numbers. Backlog features stay unnumbered until promoted, and promotion is the tpl-promote-backlog-spec skill's job.
- Attaching a feature to a phase the brief did not name.
- Editing any file other than the `doc-edit` targets the brief explicitly names.
- Deduplication beyond the collision check in precondition 7.
- Deleting or moving a brief after processing.
- Committing, pushing, or opening a pull request.
- Hand-editing `docs/reference.md`, which is generated by the `tpl-prepare-docs-reference` skill.
- Touching `docs/claude-transfer/`, whose entries are symlinks rebuilt from `members.txt` by the same skill.
