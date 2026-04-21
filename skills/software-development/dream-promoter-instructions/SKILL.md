---
name: dream-promoter-instructions
description: Runtime-specific execution playbook for Dream real-mode promotions. Use after memory-capture-layering decides what belongs in built-in memory, skills, external memory, or nowhere.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [dream, promotion, memory, skills, adapters, runtime]
    related_skills: [nightly-dream-safe-mode, memory-capture-layering, hermes-agent]
---

# Dream Promoter Instructions

## Purpose

Use this skill when Dream is running in **real mode** and the staged candidate batch has already been classified with `memory-capture-layering`.

This skill is the **execution playbook**, not the taxonomy.

- `dream.py` stages raw material.
- `memory-capture-layering` decides **what belongs where**.
- `dream-promoter-instructions` tells the agent **how to apply those decisions in the current runtime**.

## Core rule

Keep the stable parts portable and isolate the unstable part:

1. **Staging** — portable
2. **Classification policy** — portable
3. **Promotion execution** — runtime-specific

Do not bake runtime-specific write mechanics into `dream.py`.

## Runtime selection

Read `~/.hermes/dream/config.json` and look for a promotion block like:

```json
{
  "mode": "real",
  "promotion": {
    "adapter": "hermes",
    "built_in": "auto_on_real",
    "skills": "auto_on_real",
    "external": "auto_on_real"
  }
}
```

Meaning:
- `adapter` = which execution playbook to follow
- `built_in` / `skills` / `external` = whether the runtime should apply that layer automatically in real mode, or require manual review

Suggested values:
- `manual`
- `auto_on_real`
- `disabled`

If the config is missing, default conservatively:
- adapter = `hermes`
- all layers = `manual`

## What this skill does

- explains the execution adapter for the active runtime
- tells the agent which tools/files to use for each layer
- tells the agent how to mark the candidate batch after successful writes

## What this skill does NOT do

- it does not replace `memory-capture-layering`
- it does not reclassify candidates on its own
- it does not require hardcoded automation when the runtime is unstable

## Promotion flow

1. Read the staged candidate batch / run payload.
2. Use `memory-capture-layering` to classify each candidate.
3. Read the runtime adapter and per-layer policy from `dream/config.json`.
4. Apply only the layers allowed by policy.
5. Update the candidate batch metadata:
   - `promotion_status.built_in`
   - `promotion_status.skills`
   - `promotion_status.external`
   - prefer explicit lifecycle states:
     - `not_evaluated` for initial staged state before review
     - `applied` when the write succeeds
     - `not_applied` when review is complete but promotion is intentionally skipped (duplicate, temporary, low-confidence, below threshold)
     - `manual_review` when likely durable but not auto-promoted yet
     - `disabled` when policy forbids the layer
     - `blocked_memory_unavailable` / `blocked_tool_unavailable` when runtime capability is missing
     - `failed` when a write was attempted but errored unexpectedly
6. Record any identifiers/notes useful for audit (fact IDs, skill names, memory note summary).

## Adapter references

- Hermes runtime -> see `references/hermes.md`
- Claude Code style runtime -> see `references/claude-code.md`
- OpenClaw style runtime -> see `references/openclaw.md`

## Default recommendation

- Start with `manual` for all three layers until the runtime is trusted.
- Move to `auto_on_real` only for layers whose write path is stable.
- Keep `dream.py` staging-only.
- Keep adapter logic as instructions/playbooks unless the write API is stable enough to automate safely.

## Verification

After any promotion run, verify:
- the intended write actually happened in the current runtime
- the candidate batch marks the right layers as applied / skipped / manual
- the final report distinguishes classification from execution

## Remember

`memory-capture-layering` answers **where** something belongs.

`dream-promoter-instructions` answers **how this runtime should apply that decision**.
