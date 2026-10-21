# Work packages: done

**Location**: `docs/work-packages/done/`

Work packages whose work has been delivered.

## How a package gets here

Through the `{{SKILL_PREFIX}}-archive-wp` skill, never a bare `git mv`. The skill strips the batch number from the filename, restates the status line to say what the package produced, removes the row from the live table in `docs/work-packages/README.md`, and repoints every reference.

## Delivered, not superseded

A package that was abandoned, or overtaken by a different approach, still comes here, but its status line must say which, because "we did this" and "we decided not to" answer different questions.

## These stay readable

Skill-shaped packages in particular remain the best account of why a skill works the way it does, and the skills link here for that reason. Being finished is not the same as being stale, and a live document pointing into `done/` is normal.

## What is preserved here, and what is not

A delivered package describes the repository as it stood when the work was done. Its **findings, decisions and dates are not revised**. The same rule covers `.specify/memory/constitution-changelog.md` and the briefs in `docs/sessions/`.

**References are not covered by it.** A path that no longer resolves is rot, not history: repoint it, or mark it `(lost)` when the target cannot be found.
