---
name: memory-capture-layering
description: Decide whether durable knowledge belongs in built-in memory, a reusable skill, an external deep-memory provider, or nowhere. Use to keep Hermes memory clean as projects, workflows, and skills scale over time.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [memory, skills, taxonomy, knowledge-management, triage]
    related_skills: [dream-promoter-instructions, hermes-agent, orchestration-docs-layering]
---

# Memory Capture Layering

## Overview

Use this skill whenever you are about to save durable knowledge and must decide **where it belongs**:

- **Built-in memory** (`memory` / `user`) for small, always-useful facts
- **Skill** for reusable procedures and playbooks
- **External memory provider** (e.g. Holographic) for deeper structured recall
- **Nowhere** for temporary noise, task progress, or low-confidence observations

The goal is not to save more information. The goal is to save the **right kind of information in the right layer** so retrieval stays accurate as projects and workflows scale.

Important: this skill handles **classification**, not runtime-specific execution. Pair it with `dream-promoter-instructions` when a system must actually apply approved writes.

## Core Model

Treat Hermes memory as three layers:

1. **Built-in memory = always-on context**
   - Small, stable, high-value facts worth injecting into many future turns
   - Examples: user preferences, hard constraints, stable project conventions

2. **Skills = reusable procedures**
   - Stepwise approaches that can be executed again
   - Examples: workflows, debugging playbooks, orchestration patterns, review checklists

3. **External provider = deep recall**
   - Larger, structured, query-driven knowledge not worth injecting every turn
   - Examples: project facts, entity relationships, historical issue patterns, architecture notes

If a piece of information does not fit any of those layers cleanly, strongly consider **not saving it**.

## Fast Triage

Run this decision flow in order:

### 1. Is it a **procedure** or a **fact**?
- If it is a reusable way of working, it is usually a **skill**.
- If it is descriptive knowledge, continue.

### 2. Does Hermes need this in mind for many unrelated future tasks?
- If yes, prefer **built-in memory**.
- If no, continue.

### 3. Is it long-lived and likely useful months later?
- If no, do **not** save it.
- If yes, continue.

### 4. Is it small and universally important, or larger and query-dependent?
- Small + critical -> **built-in memory**
- Larger, relational, project-scoped, or only sometimes relevant -> **external provider**

### 5. Is it low-confidence, temporary, or just session progress?
- If yes, do **not** save it yet.

## Built-in Memory Rules

Put something in built-in memory only if all or most are true:

- It is **stable**
- It is **compact**
- It changes how Hermes should behave in many future tasks
- The user would expect Hermes to remember it without being reminded
- It is worth spending prompt budget on repeatedly

### Good built-in memory candidates
- User language and communication preferences
- Stable user workflow expectations
- Hard constraints and repeated corrections
- Stable environment facts
- Core project conventions
- Identity mappings, home channels, durable routing rules

### Bad built-in memory candidates
- Temporary task status
- Detailed incident timelines
- Long project notes
- Large lists of facts
- Raw session outcomes
- Multi-step procedures

### Mental model
**Built-in memory should feel like a one-page index card Hermes should always carry.**

## Skill Rules

Create or update a skill when the knowledge is really a **playbook**.

A strong skill has:
- Clear trigger conditions
- Ordered steps
- Decision points
- Pitfalls / anti-patterns
- Verification steps
- Reuse value across multiple future tasks

### Good skill candidates
- Repeated workflows
- Domain-specific operating procedures
- Debugging approaches
- Review / verification checklists
- Delegation / orchestration patterns
- A nuanced classification policy like this one

### Bad skill candidates
- Single facts
- User preferences
- One-off outputs
- Temporary repo state

### Mental model
**If you can write “When X happens, do 1-2-3, watch for A/B/C, verify with D”, it belongs in a skill.**

## External Memory Provider Rules

Use the external provider for deeper knowledge that is durable but not worth carrying into every prompt.

### Good external-memory candidates
- Project facts that accumulate over time
- Relationships between repos, services, tools, owners, or workflows
- Historical engineering lessons
- Architecture notes and compatibility facts
- Recurrent issue patterns
- Contradictions or migrations from old truth to new truth
- Query-dependent project memory

### Bad external-memory candidates
- Raw chat dumps
- Noisy observations
- Unconfirmed claims
- Pure procedures that should become skills
- Trivial facts that should live in built-in memory

### Mental model
**External memory is a structured recall layer, not a transcript dump.**

## “Do Not Save” Rules

Do not save when the information is:
- Temporary task progress
- Already obvious from current context and easy to rediscover
- Not yet stable or not yet validated
- Too raw / too verbose / too noisy
- Better represented as a session transcript searchable later

When in doubt, prefer **not saving** over saving low-quality memory.

## Taxonomy

### Built-in memory categories
- user preference
- communication preference
- hard constraint
- environment fact
- stable project convention
- identity mapping

### Skill categories
- workflow
- debugging
- review / checklist
- integration procedure
- orchestration pattern
- project-specific SOP
- knowledge-triage policy

### External provider categories
- project fact
- system relationship
- architecture fact
- recurring incident pattern
- source-of-truth update
- ownership mapping
- compatibility note

### Usually do not store
- task progress
- raw transcript detail
- one-off outputs
- ephemeral TODOs
- speculative conclusions

## Worked Examples

### Built-in memory
- “User prefers Vietnamese.”
- “For py-hbs-ads, distinguish ephemeral workspace artifacts from shared library artifacts.”
- “Explicitly say when library-first lookup failed before falling back to another local source.”

### Skill
- “How to run a reusable py-hbs-ads video workflow.”
- “How to orchestrate bounded standalone Qwen workers.”
- “How to classify new durable knowledge into built-in vs skill vs external provider.”

### External provider
- “Repo A depends on service B and often breaks when ffmpeg path mapping changes in environment C.”
- “Project X migrated canonical source selection from path Y to path Z; older tasks may reference stale paths.”
- “These three services share ownership and deployment constraints.”

### Do not store
- “Today I ran command X and the second attempt succeeded.”
- “The current TODO list has four items.”
- “This temporary branch exists for a one-off experiment.”

## Anti-Patterns

Avoid these common mistakes:

1. **Stuffing built-in memory with project detail**
   - Causes prompt bloat and poor always-on recall

2. **Using external memory as a transcript archive**
   - Causes noisy retrieval and weak signal

3. **Saving procedures as facts**
   - Loses steps, checks, and reusable structure

4. **Saving low-confidence conclusions too early**
   - Creates future contradictions

5. **Refusing to save anything until it is perfect**
   - Misses durable lessons; save once stable enough

## Execution Pattern

When deciding where something belongs:

1. Summarize it into the smallest durable unit.
2. Decide: fact, procedure, or noise.
3. If fact, decide: always-on or query-driven.
4. Save to the proper layer.
5. If a skill was used and found incomplete, patch it immediately.
6. If nothing fits cleanly, do not save.

## Output Style

When explaining a storage decision to the user or to yourself, use this compact format:

- **Type:** fact / procedure / temporary
- **Layer:** built-in / skill / external / none
- **Reason:** one sentence about why this layer is the best fit

Example:
- **Type:** procedure
- **Layer:** skill
- **Reason:** reusable multi-step workflow with pitfalls and verification, not an always-on fact.

## Session-Level Save Policy

Use this compact default policy at the end of a task or session:

1. **Save to built-in memory** only when the user revealed or confirmed a stable preference, hard constraint, environment fact, or durable convention that should influence many future tasks.
2. **Create or patch a skill** when a reusable workflow, debugging method, checklist, or decision policy proved itself and would save future turns or prevent repeated mistakes.
3. **Save to external memory** when the result is durable project knowledge or an entity relationship worth recalling later, but too large or too query-dependent for always-on prompt injection.
4. **Do not save** raw task progress, temporary notes, low-confidence conclusions, or transcript detail that is better left to session history/search.
5. **When uncertain**, prefer `none` first, then revisit after the pattern repeats or the fact is confirmed.
6. **When explaining the choice**, emit: `Type / Layer / Reason`.

### End-of-session checklist
- Did the user teach Hermes a stable preference or constraint? -> built-in memory
- Did we discover a reusable procedure? -> skill
- Did we learn durable project/system knowledge? -> external memory
- Is it only useful for reconstructing what happened today? -> session history only

## Remember

The objective is not maximum retention. It is **clean retrieval under long-term scale**.

When projects multiply, the best system is the one that:
- keeps always-on memory small
- turns repeated work into skills
- reserves deep recall for structured external knowledge
- leaves temporary noise out entirely
