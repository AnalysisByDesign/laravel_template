# Session briefs

**Location**: `docs/sessions/`

Dated briefs from planning sessions held with Claude in the claude.ai app, each one the structured output of a conversation that Claude Code cannot read.

## Why this folder exists

Design thinking often happens in conversations away from the repository. The bridge is necessarily manual, because Claude Code has no access to claude.ai conversations. What this folder changes is how much of it is manual: instead of placing five documents in five locations, Claude produces one brief, it is dropped here, and the `{{SKILL_PREFIX}}-review-session-notes` skill fans it out into the artefacts the repository needs.

## Naming

`YYYY-MM-DD-short-topic.md`. The date alone is not enough, because three Wednesdays look identical in a list.

## Lifecycle

1. **Written in the chat.** Paste `.claude/skills/{{SKILL_PREFIX}}-review-session-notes/brief-template.md` into the session and ask for the output as a brief in that format.
2. **Saved here**, unprocessed. The frontmatter `status:` reads `unprocessed`.
3. **Processed** by running `{{SKILL_PREFIX}}-review-session-notes <name>`, which creates every artefact the brief declares, raises its issues, and sets `status: processed` with a record of what was created.
4. **Kept.** A processed brief is never moved or deleted. It is the record of what that session decided, including the rulings that produced no artefact.

## What a brief holds

Session-level context, a `## Decisions` section for rulings that produce no artefact, and one block per artefact. Four artefact types are recognised: backlog features, work packages, documentation edits, and GitHub issues. The format contract lives in `.claude/skills/{{SKILL_PREFIX}}-review-session-notes/brief-template.md`.

## Not in the transfer set

`docs/sessions/` is deliberately excluded from the claude.ai project's synced set and from `docs/claude-transfer/members.txt`. A brief is a staging document whose content is processed into artefacts that are already synced; syncing the briefs too would put the same content in front of the project twice. With the GitHub connector syncing `docs/` as a tree, the exclusion has to be made by hand in the project's Configure Files panel.
