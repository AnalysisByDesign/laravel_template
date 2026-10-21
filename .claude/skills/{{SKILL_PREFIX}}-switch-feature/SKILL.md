---
name: "{{SKILL_PREFIX}}-switch-feature"
description: Point spec-kit at a different existing spec by setting feature_directory in .specify/feature.json, after verifying the spec exists and is in flight. Reports the active path and what state that spec is in. With no argument, reports the current feature and lists what is available. Never creates specs, runs phases, or changes spec-kit itself.
compatibility: Requires .specify/feature.json and the specs/ layout described in CLAUDE.md
model: haiku
context: fork
metadata:
  author: "{{GITHUB_OWNER}}"
---

# Switch the Active Spec-Kit Feature

Set `.specify/feature.json` to a different existing spec, so the next spec-kit phase acts on that one.

**Which spec a spec-kit command acts on is `.specify/feature.json`, not the branch you are on.** `.specify/scripts/powershell/common.ps1` resolves it in this order: the `SPECIFY_FEATURE_DIRECTORY` environment variable, then `feature.json`, then an error. Branch name never feeds into it. Returning to an earlier spec therefore means moving this pointer, which is what this skill does and all it does.

**Input**: one spec identifier. `036`, `spec-036`, `036-user-export`, or the directory path all work. Normalise to the three-digit number `NNN`.

**With no argument**, report the current active feature and list the specs available to switch to, then stop. Change nothing.

## 1. Check the environment first

```bash
echo "${SPECIFY_FEATURE_DIRECTORY:-(unset)}"
```

**If `SPECIFY_FEATURE_DIRECTORY` is set, stop and say so.** It takes precedence over `feature.json`, so the switch would appear to work and then be ignored, and `common.ps1` writes the variable's value back into `feature.json` on the next resolution, undoing the change. Because `feature.json` is gitignored, that write-back lands in an ignored file rather than a tracked one, so it dirties nothing, but it still overwrites the switch. Tell the operator to unset it in the shell they run spec-kit from, and make no edit.

This is the one failure mode that is invisible from the file alone, which is why it is checked before anything else.

## 2. Resolve the spec

Match `NNN` against the directories that exist:

```bash
ls -d specs/${NNN}-*/ 2>/dev/null        # in flight
ls -d specs/done/${NNN}-*/ 2>/dev/null   # archived
```

- **Exactly one match under `specs/`**: that is the target. Proceed.
- **No match under `specs/`, one under `specs/done/`**: the spec has been archived. Pointing spec-kit at an archived spec is almost certainly a mistake, so **stop and ask** rather than proceeding. If the operator confirms they want it, use it.
- **No match anywhere**: stop. List the available specs so the right number is one glance away. Do not guess at a near miss; `036` and `031` are one keystroke apart and picking the wrong one silently sends the next phase at the wrong spec.
- **More than one match**: stop and list them. This should not happen, and it means something is wrong with the numbering that needs a person.

**Verify the directory is a real spec**: it contains `spec.md`. A directory with no `spec.md` has not been through `/speckit.specify` and there is nothing for a later phase to read.

## 3. Write the pointer

**If the file already holds this value, change nothing** and say so. `Save-FeatureJson` in `common.ps1` behaves the same way, and a no-op write on a tracked file is a diff for no reason.

Otherwise replace the value of `feature_directory`, and **only that value**:

- **Store a repository-relative path**, for example `specs/036-gate-a-pre-marketing-launch`, with no trailing slash. This matches `Save-FeatureJson`, which strips the repo-root prefix from an absolute path before writing.
- **Preserve the file's existing formatting.** Spec-kit writes compressed JSON with no trailing newline; the file has at times been pretty-printed instead. Do not reformat in either direction: read the file, change the one value, keep the layout. That way the diff is a single line whichever tool wrote it last, and the file never flip-flops between two shapes.

## 4. Report

Say what changed and what the spec's state is, because the point of switching back to a spec after other work is knowing where it was left:

- **The active path, before and after.** Name it as "active" so the answer to "which spec am I on" is in the report.
- **Which phases have run**, read from the directory contents: `spec.md`, `plan.md`, `tasks.md`, `research.md`, `data-model.md`, `contracts/`, `checklists/`. Absence is informative. A spec with `spec.md` and no `tasks.md` has not been through `/speckit.tasks`.
- **The task counts** if `tasks.md` exists: how many `- [x]` and how many `- [ ]`. This is the fastest read on how far implementation got.
- **The feature document's status line**, from `docs/features/spec-NNN-*.md`. Several in-flight specs are outstanding on manual work rather than anything spec-kit does, and the status line is where that is recorded.
- **Whether a branch named `NNN-*` exists**, local or remote. Usually none does, because the practice is a short branch per unit of work rather than one long-lived branch per spec. Say so plainly rather than implying a branch is missing.

## 5. The pointer is local state

**`.specify/feature.json` is gitignored**. A switch changes this machine only: nothing to stage, nothing to commit, and nothing for another checkout to disagree with. Say so in the report, because the previous instruction was the opposite and anybody who has used this skill before will expect a diff.

It was tracked until then, and the reason it stopped is worth knowing rather than taking on trust. One key named the spec for the whole repository, so two checkouts working different specs each committed a diff to it and **whichever merged last became the pointer both then used**. Nothing errored: the other machine's next spec-kit phase simply resolved a spec nobody aimed it at, read the wrong `spec.md` and wrote into the wrong `specs/NNN-*/` directory.

Three things follow:

- **A switch no longer trips the clean-working-tree precondition** in `{{SKILL_PREFIX}}-archive-wp`, `{{SKILL_PREFIX}}-archive-spec`, `{{SKILL_PREFIX}}-promote-backlog-spec` and `{{SKILL_PREFIX}}-demote-active-spec`. If one of those refuses now, the cause is something else.
- **The pointer says nothing about the repository**, only about this machine. Never infer from it what another machine or another session is working on.
- **A fresh clone has no pointer at all.** That is correct and deliberate. The resolver's own error says to set `SPECIFY_FEATURE_DIRECTORY` or run the specify command, `.specify/feature.json.example` shows the shape, and `create-new-feature.ps1` writes the file unaided. If the file is absent, say so and offer to write it rather than treating it as damage.

`tools/docs-guard/check_local_state.py` fails CI if it is ever tracked again, which is the only way this regression would otherwise be noticed: it has no symptom until a spec-kit phase writes to the wrong place.

## Out of scope

- **Changing spec-kit itself.** No edits to anything under `.specify/scripts/`, `extensions.yml`, or the resolution order. This skill writes one value in one config file.
- **Changing whether `feature.json` is tracked.** It is gitignored and that is settled; this skill writes the value and nothing else.
- **Creating a spec.** That is `/speckit.specify`, which sets this pointer itself as part of creating the feature.
- **Running any spec-kit phase.** Switching says which spec is next; it does not start anything.
- **Archiving, promoting or demoting a spec.** Those are `{{SKILL_PREFIX}}-archive-spec`, `{{SKILL_PREFIX}}-promote-backlog-spec` and `{{SKILL_PREFIX}}-demote-active-spec`, and none of them touch this pointer.
- **Editing the spec, its documents, or its tasks.**
- **Committing or pushing.**
