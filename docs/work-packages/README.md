# Work packages

**Location**: `docs/work-packages/`

A work package is a unit of work handed to a session: what to do, in what order, what is out of scope, and what needs the operator rather than Claude. Specs describe what the product should be; work packages describe a piece of work to be carried out. Plenty of work never becomes a spec, because infrastructure, research, tooling and documentation are real work that the spec-kit sequence does not cover.

**A work package is not a feature.** It carries out work around the product and does not add functionality to it; anything that would is a feature capture under `docs/features/backlog/`.

## Naming

`wp-<slug>.md`. The prefix states what the document is: `ft-` a feature capture, `wp-` a work package, `spec-` something ready for action.

**A batch number may come after the prefix**: `wp-NNN-<slug>.md`, where `NNN` says which batch of work the package belongs to. It is not a spec number, claims no position in the build order, and never appears in prose as an identifier. It sits **inside** the name so every package still sorts together under `wp-`. No spaces around it.

**The number is a batch, not a severity.** Packages sharing a number are meant to be worked as a set, because doing them together is cheaper than one at a time:

| | Batch | What belongs in it |
| --- | --- | --- |
| 000 | [Define the current batch] | |

**Unnumbered means later, not unimportant.** Any unnumbered package can be pulled into a batch when it turns out to be needed.

**Numbers are reused.** They name the batch currently being worked. So:

- **Strip the number when a package moves to `done/`**, in the same commit, so an archived file never competes for a number a live package holds.
- **A number never means the same thing twice.** The table above is the only current definition, and it is dated for that reason.

**A sequence letter follows the number where a batch has a clear order**: `wp-000a-`, then `wp-000b-`. A package with no letter is actioned first. Two packages sharing a letter are parallel steps. The letter is stripped on archiving, and the duplicate check strips it too.

## Backlog, promotion and the feature branch

| Folder | Means | How it gets there |
| --- | --- | --- |
| `backlog/` | Captured, nobody working on it | `{{SKILL_PREFIX}}-review-session-notes` writes new packages here |
| the root | In flight, with its own `feature/wp-<slug>` branch | `{{SKILL_PREFIX}}-promote-wp` moves it, cuts and pushes the branch, and writes `**Target branch**` into the header |
| `done/` | Delivered, superseded or abandoned | `{{SKILL_PREFIX}}-archive-wp` |

**Every task PR for a promoted package targets its feature branch**, and the feature branch merges into `main` once, as the package's release gate (`{{SKILL_PREFIX}}-merge`, feature merge). The branch name carries no batch number, because batch numbers are reused and a branch outlives a batch.

**Every live package.** Keep this table current when a package is added, moved to `done/`, or re-batched, so the folder can be placed without reading it.

| Batch | Package | Owner | Gate | Where it stands |
| --- | --- | --- | --- | --- |

## Every document carries status, owner and gate

Three required fields, near the top, before the first heading:

- **Status**: where the work stands, and when finished, what it produced.
- **Owner**: who does it. The operator, Claude Code, or explicitly mixed.
- **Gate**: what has to be true before it can start, or `none`.

Without them the only way to learn whether a package is live is to read it. A package whose gate is another package is not work, it is a queue entry.

## Mixed ownership: section it before you split it

The most common defect is a package that interleaves operator-manual work with Claude work. Usually the better answer is to section, not split:

- **Section A**: the operator's decisions, explicitly labelled as not Claude tasks.
- **Section B**: work blocked behind section A.
- **Section C**: work with no gate, which can start immediately.

Split when the parts have genuinely different lives: a different gate, a different phase, or one part shippable while another waits on a third party.

## Duplicates after a stacked squash-merge

A squash-merge of a stacked PR that renames a file can leave `main` holding it under both names, and git will not warn you. `tools/docs-guard/check_duplicate_packages.py` runs in the `docs-guard` CI job and compares filenames with the batch numbers stripped, across these folders and the feature folders. To check by hand:

```sh
for d in docs/work-packages docs/work-packages/backlog docs/work-packages/done; do
  ls "$d" | grep '\.md$' | grep -v '^README\.md$'
done | sed -E 's/^(wp)-[0-9]{3}[a-z]?-/\1-/' | sort | uniq -d
```

The `README.md` exclusion is load-bearing: there is one in each directory. Silence means clean.

## When something moves to `done/`

**Through the `{{SKILL_PREFIX}}-archive-wp` skill, never a bare `git mv`**, and **when the work it describes has been delivered**, not when the document stops being useful. The move strips the batch number, restates the status line to say what the package produced, removes the row from the table above, and rewrites every reference.

## Directories

A work package earns a directory only when it accumulates enough companion material that a flat file stops working. A directory containing one file is just a file with an extra level of nesting.

## Related, and not here

- **Reviews, audits and triage records** go in `docs/reviews/`.
- **User-facing guides** go in `docs/guides/`.
- **Session briefs**, the bridge from claude.ai conversations, go in `docs/sessions/` and are processed by `{{SKILL_PREFIX}}-review-session-notes`.
