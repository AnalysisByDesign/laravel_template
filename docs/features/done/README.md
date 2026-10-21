# Features: done

**Location**: `docs/features/done/`

Shipped specs. A spec arrives here when the work it describes is merged and released, not when the last task is ticked.

## How things arrive

Through the `tpl-archive-spec` skill, never a bare `git mv`. The skill moves both the feature document and its `specs/NNN-*/` spec-kit directory, then rewrites every reference across the repository. Moving the file alone leaves live documents pointing at a path that no longer exists, and nothing errors when one goes stale.

## What belongs here

Numbered specs, `spec-NNN-<slug>.md`, and nothing else.

Documents that describe how to use what was built are not specs and do not belong here even when a spec's task list produced them. They go in `docs/guides/`. The test is what the document is, not which spec caused it to exist.

## Numbers here are still in use

A number in this folder is allocated, not released. Check `done/` as part of any allocation sweep. See `docs/features/README.md` for the allocation rules.
