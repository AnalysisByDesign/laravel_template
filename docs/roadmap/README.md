# Roadmap

**Location**: `docs/roadmap/`

Generated documents answering the two questions nobody can answer from one place:

| Document | Answers |
| --- | --- |
| `upcoming.md` | What is left, by gate and epic, in three lanes |
| `completed.md` | What has landed, newest first, with the merge date and PR |
| `roadmap-overview.png` | Every epic in sequence, each with a progress bar and its counts by state |
| `roadmap-gates.png` | What is left before each gate, item by item, coloured by state |

None of these exist until the generator first runs. The `.puml` beside each PNG is its source; the generator renders the PNG when PlantUML is installed and the source changed.

## Generated. Never edit by hand

Everything here is written by `tools/roadmap/build.py` from the repository's own artefacts: the epics folder, the feature documents, the work packages, `git log` and the open GitHub issues. **Nothing in this folder is a source.** To correct something, correct the document the row links to and regenerate:

```sh
python3 tools/roadmap/build.py
```

`--check` reports whether the committed files are current without writing. `--no-github` skips the issue lane for an offline or unauthenticated run.

**Staleness is not a CI gate, deliberately.** The fix lane carries open GitHub issues, which change without any commit, so a freshness check would fail whenever somebody opened an issue. CI runs the generator's unit tests in the `docs-guard` job; keeping the files current is the `tpl-merge` skill's job, from post-merge `main`.

## Markdown, not PDF

Other documents need to link into it, and the claude.ai project syncs `docs/` and cannot read a binary. A PDF can be made from Markdown whenever one is wanted.

## How state is decided

An item's folder decides it where the folder says anything: a document in `done/` is done, one in `dropped/` is dropped. Otherwise the state is read from the wording of the document's own status line, which is keyword matching on prose and is sometimes wrong. That is why the status sentence is printed next to the label: where the two disagree, the sentence is right.

## The two warnings worth acting on

- **Homed in no epic.** Items in none are invisible to a release review that reads `docs/epics/`.
- **Homed in more than one epic.** Adding the item tables up double counts these.
