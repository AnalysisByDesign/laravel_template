# Spec-kit: a short guide

## The one-paragraph version

Spec-kit is a CLI (`specify`) that puts templates, scripts and skills into the repository so the coding agent follows a fixed pipeline instead of freestyling: **Constitution, Spec, Plan, Tasks, Implement**, with quality gates between. Each stage produces a Markdown file that feeds the next. This repository already has it installed (`.specify/`, `.claude/skills/speckit-*`); you do not run `specify init` again.

## Mental model mapping

| Familiar practice | Spec-kit equivalent |
|---|---|
| Project instructions | `.specify/memory/constitution.md` (binding) and `CLAUDE.md` (conventions) |
| "Talk it through, agree the shape" | `/speckit.specify` and `/speckit.clarify` |
| Architectural decisions | `plan.md` from `/speckit.plan` |
| Task list and build order | `tasks.md` from `/speckit.tasks` |
| Handing the work over | `/speckit.implement`, through the `implementer` subagent |

## The pipeline, stage by stage

Run these inside Claude Code, from the spec's `feature/NNN-<slug>` branch.

0. **`/speckit.constitution`**, once, and again only when a genuine principle changes (version-bump it when it does).
1. **`/speckit.specify <description>`**: **what and why, no tech stack.** Creates `specs/NNN-name/spec.md`; its `before_specify` hook cuts the first task branch. Hunt for `[NEEDS CLARIFICATION]` markers: they are the spec telling you where it guessed.
2. **`/speckit.clarify`**: targeted questions that resolve ambiguity, written back into the spec. Run it until it has nothing left to ask. Never skip it.
3. **`/speckit.plan`**: now the stack, data model and contracts. **Read this one properly**; it is where the agent commits to architecture.
4. **`/speckit.tasks`**: dependency-ordered, independently verifiable tasks grouped by user story. Reorder, split or veto as you would your own list.
5. **`/speckit.analyze`**: cross-checks spec, plan, tasks and constitution for contradictions and gaps. Always run it. A `/compact` afterwards is a good idea.
6. **`/speckit.implement`**: TDD-first, one user story at a time, each on its own task branch.
7. **`/speckit.checklist`** then **`/speckit.converge`**: not optional. Converge appends whatever is unbuilt to `tasks.md`; loop back to implement until it finds nothing.

Every phase auto-commits its artefacts through the git extension's `after_*` hooks.

## Which spec a command acts on

`.specify/feature.json` (gitignored, per machine) holds a single `feature_directory` key, not the branch. Use `{{SKILL_PREFIX}}-switch-feature` to point it at another in-flight spec. Setting `SPECIFY_FEATURE_DIRECTORY` writes its value back into `feature.json`, so it overwrites a switch rather than overriding it for one call.

## Traps

1. **Tech in the spec.** "A Livewire component for the list" belongs in the plan. The spec says "the user browses items by category".
2. **Skipping clarify because you are in a hurry.** That is vibe coding with extra files.
3. **Not reading `plan.md`.** Two minutes of reading beats two days of unwinding.
4. **Treating `tasks.md` as gospel.**
5. **Constitution bloat.** Non-negotiables only; preferences go in `CLAUDE.md` or the plan prompt.
6. **One giant spec.** A spec is one feature; oversized captures are split by `{{SKILL_PREFIX}}-split-feature` before promotion.
7. **Editing shipped code without touching the spec.** Update the spec and regenerate downstream, or the spec rots.
