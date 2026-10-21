# Multi-model agent orchestration (spec-kit and Claude Code subagents)

**Status:** adopted convention. Applies to all feature work on this repository.
**Audience:** anyone running the spec-kit loop on this codebase.

## Why this exists

Spec-kit is model-agnostic: it generates `/speckit.*` skills but has no concept of "run this phase on model X". Model routing is our layer on top. Reasoning-heavy work (specifying, planning, review against the spec) runs on the strongest model; the bulk of implementation runs on a cheaper one, without hand-switching models mid-session or losing the spec artefacts as the single source of truth.

The mechanism is Claude Code **subagents with pinned models**. The spec, plan and tasks files in `specs/NNN-*` are the handoff contract between phases; the subagents run each phase on the right model with the right, restricted, tool access.

## The model to phase mapping

| Phase | Runs as | Model | Why |
|---|---|---|---|
| `/speckit.specify`, `/speckit.clarify`, `/speckit.plan`, `/speckit.tasks`, `/speckit.analyze` | Main conversation | Strongest available | Artefact quality here determines everything downstream. |
| `/speckit.implement` (task execution) | `implementer` subagent | Sonnet | Well-scoped tasks against a confirmed plan; fast and cheap enough to run per task. |
| Spec-conformance review and test audit before PR | `spec-reviewer` subagent | Opus | Independent, read-only judgement against the spec and the constitution; must not share the implementer's context. |
| Promotion consistency check | `product-owner` subagent | Opus | Judgement on roadmap fit, called by `{{SKILL_PREFIX}}-po-check` and `{{SKILL_PREFIX}}-promote-backlog-spec`. |

The agent definitions live in `.claude/agents/`. The reviewer and product owner are **read-only by construction** (tool allowlist), not by prompt instruction.

## How subagents work

A subagent is a Markdown file with YAML frontmatter in `.claude/agents/`. The frontmatter declares `name` and `description` (the description drives automatic delegation, so it says *when* to use the agent), `tools` (an allowlist; without `Write`/`Edit` it physically cannot modify files), `model` (the pin) and optionally `maxTurns`. The body becomes the subagent's **entire system prompt**.

Each subagent runs in a fresh context and returns only its final result. That isolation is a feature for review and a constraint for implementation: the subagent must be told where the artefacts live.

**The agent cannot see its own turn count**, so it cannot wind up gracefully near a cap. The `implementer` definition instead asks for a `specs/NNN-name/.handover.md`, written early and updated at each checkpoint, gitignored, which survives being stopped at any point. If a run stops at its turn limit with edits in the tree and no report, send it a message asking only for a status report.

**Do not set `CLAUDE_CODE_SUBAGENT_MODEL`** in your environment: it overrides every subagent's frontmatter model and silently defeats this convention.

## The workflow, end to end

**Phase 1, spec and plan, main session:**

```
/speckit.specify <feature description>
/speckit.clarify
/speckit.plan
/speckit.tasks
/speckit.analyze
```

Resolve every `/speckit.analyze` finding before proceeding. For anything in the constitution's operator-review list, the plan goes to the operator **now**, before implementation.

**Phase 2, implement, via subagent.** Rather than running `/speckit.implement` inline, delegate per task, explicitly:

```
Use the implementer agent to complete task T003 from specs/001-example/
```

Batch tightly coupled tasks into one invocation; keep independent tasks separate so a bad run stays contained. The main session stays the orchestrator, tracking `tasks.md` without accumulating implementation noise.

**Static analysis is part of implement, not a CI surprise:** every spec's final phase includes `make stan`, and any task that changes docblocks, relation nullability or service signatures runs it before reporting done.

**Phase 3, review, via subagent:**

```
Use the spec-reviewer agent to review the current branch against specs/001-example/
```

Fix BLOCKER and MAJOR findings by handing them back to the implementer as corrective tasks, re-review, then open the PR. The reviewer's READY verdict is a precondition for the PR, not a substitute for operator review.

**Then** `/speckit.checklist` and `/speckit.converge`, on every spec. Converge appends whatever is still unbuilt to `tasks.md`; a spec is finished when it finds nothing left.

## Skill models

Project skills pin a model in their frontmatter too. Two shapes, chosen by whether the skill has to stop and ask the operator something:

- **`model` plus `context: fork`**: the skill runs as a subagent in a clean context, which is cheap, but cannot ask anything or see the conversation. Mechanical skills that ask nothing use this shape.
- **`model` alone (inline)**: the skill can still ask, but the pinned model reads the whole conversation so far.

Judgement-and-writing skills (`{{SKILL_PREFIX}}-split-feature`, `{{SKILL_PREFIX}}-review-backlog`, `{{SKILL_PREFIX}}-review-session-notes`) carry no pin and run on the session model.

## Gotchas

- **Token cost is real.** Multi-agent workflows run at several times the tokens of a single-agent session. Don't spawn subagents for one-line fixes.
- **Subagents start cold.** Every invocation states the feature directory and task numbers explicitly.
- **Description collisions break routing.** Keep agent descriptions sharp and non-overlapping, and invoke explicitly for anything critical.
- **The body replaces the default system prompt.** Constitution rules a subagent must obey have to be in its agent file.

## Changing this convention

Changes to the agent definitions or the mapping go through a normal PR. If a change conflicts with the constitution, the constitution wins and is amended first.
