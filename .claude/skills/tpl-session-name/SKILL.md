---
name: tpl-session-name
description: Give the operator the exact /rename command that names the current Claude Code session for the work it holds, so a session list across two machines shows which spec or merge each session belongs to. Spec mode (the default, run as an after_specify hook) derives the heading from the active spec; done mode (called by the tpl-merge skill as its last step) prefixes DONE. Never claims a rename it did not perform, because it cannot perform one.
compatibility: Requires .specify/feature.json for spec mode; done mode needs only git
model: haiku
context: fork
metadata:
  author: laravel-template
---

# Name the Claude Code Session

Produce the one `/rename` line that names this session, and hand it to the operator. That is the whole job.

**This skill cannot rename the session itself, and must never say it has.** Per the Claude Code documentation: built-in commands such as `/rename` are not reachable from a skill or the model, and the one programmatic route, `sessionTitle` in a `SessionStart` hook's output, fires only at startup, resume and fork, never at the point a skill runs. So the skill ends with the command for the operator to type.

**Modes**: `tpl-session-name` or `tpl-session-name spec` for spec mode; `tpl-session-name done [heading]` for done mode. The `after_specify` hook in `.specify/extensions.yml` calls it with no argument, which is spec mode.

## Heading rules

The planning-session convention in `CLAUDE.md`, applied to Claude Code sessions:

- **Date first**, `YYYY-MM-DD`, the date the session started. Take it from the date this session was given at its start, not from the spec directory or the branch. This skill runs forked and cannot see the session, so in done mode the date comes from the argument; in spec mode, which runs straight after `/speckit.specify`, today's date is the start date.
- **Then a short topic**, lower case words separated by single spaces.
- **No em dashes or en dashes.** The hyphen inside `spec-NNN` is the identifier and stays; a slug's other hyphens become spaces.
- **`DONE` prefixed only once the work is complete.**

## Spec mode

1. Read `feature_directory` from `.specify/feature.json`. If `SPECIFY_FEATURE_DIRECTORY` is set in the environment, it wins, as it does for spec-kit. If neither gives a directory, stop and say so; do not guess a spec from the branch name.
2. The directory's last segment is `NNN-short-name`. Build `YYYY-MM-DD spec-NNN short name`.

`specs/052-guest-reorder` started on 2026-10-05 gives `2026-10-05 spec-052 guest reorder`.

## Done mode

1. **Check the work really is complete.** If the caller says anything is still open (the follow-up documentation PR not merged, a gate outstanding, the operator's read-through pending), do not produce a `DONE` heading. Say what is open and that the heading waits for it.
2. **Use the session's existing heading when there is one.** The skill cannot see the session title, so it comes from the argument, or from the heading this session was named with earlier in the conversation. Prefix it: `DONE 2026-10-05 spec-052 guest reorder`.
3. **Otherwise, build one**, so that it reads like the heading spec mode would have given:
   - **A spec branch** (`NNN-short-name`, the shape spec-kit creates): `DONE YYYY-MM-DD spec-NNN short name`. `052-user-export` merged from a session started 2026-10-05 gives `DONE 2026-10-05 spec-052 user export`.
   - **Any other branch**: `DONE YYYY-MM-DD` plus the branch name with any `type/` prefix dropped and hyphens turned to spaces. `tooling/claude-code-session-naming` gives `DONE 2026-10-05 claude code session naming`.

   The date is this session's start date, which may differ from the date of the session that ran `/speckit.specify`. That is expected: it names the session doing the merge.

## Output

Exactly this shape, as the last thing in the response so it is not lost under other output:

```
Session name: /rename 2026-10-05 spec-052 guest reorder
```

If the heading could not be built, the line says why instead, in one sentence. Nothing else, no preamble.

## Out of scope

- Renaming claude.ai planning sessions, which stays a prompt to the operator.
- Sweeping or deleting Claude Code sessions.
- Deciding whether work is complete. Done mode trusts the caller, which is `tpl-merge`'s gate: it withholds a `DONE` heading while the follow-up documentation PR is open, a gate is outstanding, or a reported migration was not run.
