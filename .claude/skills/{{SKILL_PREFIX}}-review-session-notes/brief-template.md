# Session Brief Format

This is the contract between Claude in the claude.ai chat, which writes a brief, and the `{{SKILL_PREFIX}}-review-session-notes` skill in Claude Code, which processes it. The two never talk to each other, so the format has to be unambiguous enough that the skill is never guessing.

**Updated**: 2026-09-02, after the first brief was written to it. Added the heading level constraint, the cross-reference rule, the two-sided dependency rule, and guidance on `doc-edit` placement. Clarified `Phase` on blockers. Usage line updated to match the skill's batch behaviour.

**To use it**: paste this file into the chat session and ask for the session's output as a brief in this format. Save the result to `docs/sessions/YYYY-MM-DD-short-topic.md`, then run `{{SKILL_PREFIX}}-review-session-notes YYYY-MM-DD-short-topic` for that one brief, or `{{SKILL_PREFIX}}-review-session-notes` with no argument to process every brief in `docs/sessions/` whose status is still `unprocessed`.

## Rules for whoever writes the brief

- **One item per artefact.** Combining two backlog features at promotion time is trivial; splitting one that has grown is not.

- **State the type explicitly.** The skill never infers a type from content.

- **Write the body as the finished artefact**, not as a note about it. The body is copied across as written, so anything vague survives into the repository.

- **Use `###` or deeper for every heading inside an item body.** The skill finds items by scanning for `## Item`, so a `##` inside a body ends the item early and silently loses everything after it. This matters most for `work-package` items, whose bodies carry a full document structure.

- **Cross-reference by resulting filename, not item number.** Write `ft-image-safety-classification`, not "Item 3". Item numbers exist only inside the brief and are meaningless once the artefacts are created, so a reference written that way is dead on arrival in the repository.

- **State both sides of a dependency.** If one backlog feature blocks another, say so in both bodies. Only stating it in one leaves the other file looking unconstrained, and the backlog review ceremony reads them independently.

- **Record decisions that produce no artefact** under `## Decisions`. A ruling like "this rule sits underneath the existing operator review gates rather than merging into them" shapes later work and otherwise dies with the conversation.

- **No em dashes or en dashes**, per the house style rule in `CLAUDE.md`. Commas, colons, semicolons, full stops or parentheses instead.

### Writing a `doc-edit`

The body is applied as written, so placement instructions have to be right rather than plausible. Two rules follow.

**Anchor to something that verifiably exists.** Name the section the change goes into, above, or below, using a heading that is actually in the target file. Do not describe a position from memory of how the file used to be organised.

**Flag uncertainty rather than guessing.** If the target file's current structure is not in front of you, say so in the body: state the content, and leave the placement as a question for whoever applies it. A wrong placement instruction that reads confidently is worse than an open one, because it gets followed.

Several items may name the same `Target`. The skill consolidates them into one pass, in the order they appear in the brief.

---

```markdown
---
session: <YYYY-MM-DD short topic>
date: <YYYY-MM-DD>
status: unprocessed
---

# Session Brief: <Topic>

**Source**: Voice planning session with the operator, <date>.

<One or two paragraphs on what the session covered. Optional.>

## Decisions

Rulings made in this session that produce no artefact of their own. Free prose,
one bullet per decision, each stating what was decided and why.

- ...

## Item 1: <Title>

**Type**: backlog-feature
**Slug**: <kebab-case-name>
**Marker**: blocker | candidate
**Phase**: P1 | P2 | P3 | P4 | unknown
**Areas**: <tag>, <tag>

<The substance. Becomes docs/features/backlog/ft-<slug>.md.
Say what the single user-visible outcome is, why it exists, and what is
deliberately left open. A blocker states what it blocks, by filename.
Headings inside the body start at ###.>

## Item 2: <Title>

**Type**: work-package
**Slug**: <kebab-case-name>

<The substance. Becomes docs/work-packages/backlog/wp-<slug>.md, until it is
promoted with {{SKILL_PREFIX}}-promote-wp when work on it begins.
Follows the existing work package shape: why it exists, scope, explicitly
out of scope, open questions, done when. All of those are ### headings,
never ##.>

## Item 3: <Title>

**Type**: doc-edit
**Target**: <path/to/existing/file.md>

<The change to make, precise enough to apply without interpretation: which
section, what it should say, and whether it replaces or adds. See the
doc-edit rules above on anchoring and flagging uncertainty.>

## Item 4: <Title>

**Type**: issue
**Kind**: implementation | manual-check

<Context in prose, then:>

### Scope

- [ ] <task>
- [ ] <task>

### Notes

<Anything that is context rather than work. Optional.>

<The item title becomes the issue title; everything below the field block
becomes the issue body.>
```

## Field reference

| Field | Applies to | Values |
|---|---|---|
| `Type` | every item | `backlog-feature`, `work-package`, `doc-edit`, `issue` |
| `Slug` | `backlog-feature`, `work-package` | kebab case, no `ft-` or `wp-` prefix; the skill adds it |
| `Marker` | `backlog-feature` | `blocker` (must land before committed work can ship) or `candidate` (may never be built) |
| `Phase` | `backlog-feature` | required when `Marker` is `blocker`, omitted otherwise. The phase the blocker protects, or `unknown` where the work it guards is not itself attached to a phase yet. `unknown` is a legitimate answer, not a gap to fill by guessing; it resolves at backlog review when both attach together. |
| `Areas` | `backlog-feature` | optional. One to three tags from `docs/features/areas.json`, most central first. Omit the line when the vocabulary is not to hand, and the skill chooses from the body and reports what it chose. A tag outside the vocabulary is refused. |
| `Target` | `doc-edit` | a path that already exists in the repository |
| `Kind` | `issue` | `implementation` (there is code to write) or `manual-check` (a human pass with nothing to execute). Recorded in the issue body, not as a label: the skill applies no labels, because an unknown label fails the whole call. |

The item title, on the `## Item N:` line, becomes the artefact's title: the H1 of a created document, or the title of a created issue. Write it as the finished title, not as a label for the brief.

## What the skill will refuse

- An unrecognised or missing `Type`.
- A missing `Slug`, `Marker`, `Target` or `Kind`.
- A missing `Phase` on an item marked `blocker`.
- An `Areas` value that is not in `docs/features/areas.json`.
- A `Target` naming a file that does not exist.
- A `Slug` resolving to a file that already exists, which usually means the idea was captured in an earlier session.
- A brief whose `status:` already reads `processed`.
- A dirty working tree.

In every case it stops before changing anything and says which item failed.

Note that a `##` heading inside an item body cannot be refused, because the skill cannot tell it apart from the end of the item. It reads as truncation, not as an error. This is why the heading level rule is stated as a rule for the writer rather than a check on the reader.
