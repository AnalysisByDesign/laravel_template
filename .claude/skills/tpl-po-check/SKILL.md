---
name: tpl-po-check
description: Ask the product owner node whether promoting one backlog item now is consistent with the roadmap, the live batches and the constitution, without promoting it. Returns promote, challenge or defer with the grounds. Read-only; changes nothing. The tpl-promote-backlog-spec skill runs the same check before it acts.
compatibility: Needs python3 on the host and the docs/features/, docs/work-packages/ and docs/epics/ layout described in CLAUDE.md.
model: haiku
context: fork
metadata:
  author: laravel-template
---

# Check a promotion with the product owner node

**Input**: one backlog item, by slug or filename. `ft-`, a batch number and `.md` are all optional.

## 1. Assemble the context

```bash
python3 tools/po-check/context.py <item> > <scratch>/po-bundle.json
```

`<scratch>` is outside the repository. The script resolves the item, and exits 1 naming the problem if it is missing or ambiguous. The bundle is exactly what the node is allowed to reason from; nothing else is handed over.

## 2. Ask the node

Launch the `product-owner` agent once, with a prompt that names the bundle's path and asks for the verdict object. Save what it returns, the JSON alone, to `<scratch>/po-verdict.json`.

## 3. Validate the verdict

```bash
python3 tools/po-check/verdict.py check <scratch>/po-verdict.json
```

If it fails, launch the node once more, quoting the problems. If it fails again, stop and report the raw output; do not guess a verdict.

## 4. Report

State the verdict, the reason, what it displaces, the principle conflicts and whether a spec already exists, verbatim from the node. Add nothing. This skill does not promote, does not ask the operator to choose, and writes nothing to the repository.
