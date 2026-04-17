---
name: nightly-dream-safe-mode
description: Create a nightly 1 AM 'dream' consolidation workflow that incrementally processes undreamed Hermes session logs, writes daily diary markdown, stages candidate knowledge, and supports both safe-mode review and real-mode promotion.
version: 1.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [cron, memory, diary, consolidation, safe-mode, session-logs]
    related_skills: [memory-capture-layering, hermes-agent]
---

# Nightly Dream Modes

## When to use

Use this skill when the user wants a recurring background workflow that:
- reviews Hermes conversations from the day,
- skips anything already processed in earlier runs,
- writes a daily diary file for quick human indexing,
- stages candidate knowledge for later audit/backfill,
- and either runs in **safe mode** (proposal-only) or **real mode** (conservative promotion).

Use **safe mode** while validating the capture policy. Use **real mode** once the user is ready for the cron run to actually promote durable knowledge.

## Core design

Split the workflow into two layers:

1. **Pre-run script** (`script=` on the cron job)
   - Does all mechanical work before the agent turn
   - Reads Hermes session logs from `~/.hermes/sessions/session_*.json`
   - Tracks per-session processed progress so only **undreamed** content is considered
   - Writes a daily diary markdown file
   - Emits structured JSON to stdout for the cron-run agent to analyze

2. **Cron-run agent prompt**
   - Treats the script output as the only input corpus for this run
   - Uses `memory-capture-layering` taxonomy
   - Produces a nightly report with four buckets:
     - proposed built-in memory
     - proposed skill actions
     - proposed external-memory facts
     - rejected/no-save items
   - In safe mode, does **not** write memory, create/patch skills, or touch external providers

## Why this split matters

Do not make the cron-run agent scrape raw session files directly if you can avoid it. A pre-run script is better because it:
- keeps the cron prompt compact,
- handles idempotency cleanly,
- can write diary/state files deterministically,
- and leaves the agent responsible for **judgment**, not bookkeeping.

## Files and directories

Recommended paths:

- Script: `~/.hermes/scripts/dream.py`
- Mode config: `~/.hermes/dream/config.json`
- State: `~/.hermes/dream/state.json`
- Daily diary dir: `~/.hermes/dream/diary/`
- Daily diary file: `~/.hermes/dream/diary/diary_YYYY-MM-DD.md`
- Run payloads: `~/.hermes/dream/runs/dream_run_*.json`
- Candidate batches: `~/.hermes/dream/candidates/candidate_batch_*.json`

## State model

### Mode control

Use `~/.hermes/dream/config.json` to switch execution mode explicitly:

```json
{
  "mode": "safe"
}
```

Accepted values:
- `safe` -> diary + run payload + candidate batch + report only
- `real` -> diary + run payload + candidate batch + conservative promotion of approved durable knowledge

The script should read this config and stamp the chosen mode into the diary, candidate batch, and run payload.

The same config file is also the right place for heuristic tuning, for example:

```json
{
  "mode": "safe",
  "heuristics": {
    "top_topics_per_session": 4,
    "top_groups_in_summary": 8,
    "common_path_parts": [],
    "project_context_markers": []
  }
}
```

Use `common_path_parts` to suppress extra generic directory names in your own environment, and `project_context_markers` to add local words that usually indicate a project/repo mention.

Use a persistent JSON state file with at least:

```json
{
  "last_run_at": "2026-04-15T14:25:21Z",
  "last_candidate_batch_path": "~/.hermes/dream/candidates/candidate_batch_20260415T142521Z.json",
  "candidate_batches": [
    {
      "created_at": "2026-04-15T14:25:21Z",
      "path": "~/.hermes/dream/candidates/candidate_batch_20260415T142521Z.json",
      "candidate_count": 3,
      "status": "pending_review"
    }
  ],
  "sessions": {
    "20260415_155856_56e88396": {
      "processed_message_count": 123,
      "last_seen_updated": "2026-04-15T21:22:50.527101"
    }
  }
}
```

### Idempotency rule

Track **per-session processed_message_count** and advance it only after diary + run payload + candidate batch are written successfully.

This is simpler and safer than trying to hash every message first.

## Script behavior

The script should:

1. Load `state.json`
2. Enumerate `~/.hermes/sessions/session_*.json`
3. For each session:
   - read the JSON log,
   - skip already-processed messages,
   - discard system/developer/tool noise,
   - keep meaningful `user` and non-empty `assistant` messages
4. Build a diary for the target date
5. Write a **candidate batch** JSON file under `~/.hermes/dream/candidates/` with:
   - status `pending_review`
   - promotion status for built-in / skills / external
   - grouped sessions
   - preserved messages for later backfill
6. Emit a run payload JSON with:
   - mode
   - diary path
   - run path
   - candidate batch path
   - mode-specific notes
   - reviewed sessions
   - kept messages for each session
7. Persist updated state only after outputs are safely written

## Message filtering

Recommended default filtering:
- skip `system`
- skip `developer`
- skip `tool`
- keep `user`
- keep `assistant` only when content is non-empty

This keeps the nightly corpus readable while still reflecting the real conversation.

Additional diary hygiene rules:
- collapse injected skill wrappers and cron delivery wrappers into short placeholders instead of dumping huge system payloads into the diary
- prefer salient repo/path labels only; drop garbage path fragments and generic labels so the grouped index stays readable
- if the diary starts showing malformed path labels or prompt-wrapper noise, patch the script immediately instead of accepting degraded diary quality

## Diary behavior

Diary is a **daily index**, not long-term memory.

The diary file should include:
- run timestamp
- previous dream run timestamp
- number of sessions touched
- a summary count of kept messages
- heuristic grouping by inferred project / repo / topic
- a grouped session index
- brief transcript excerpts per session

### Heuristic grouping

Compute labels in the pre-run script, not in the cron prompt. Each session row should carry:
- `primary`
- `projects`
- `topics`
- `paths`
- `labels`

Practical findings:
- boost known project hints such as `py-hbs-ads`, `hbs-ads`, `hermes-agent`
- collect topic hits from keyword rules (`memory`, `skills`, `cron`, `discord`, `video`, `docs`, etc.)
- keep a small number of salient paths for context
- filter out generic labels like `built-in` or `long-term` so the grouping stays meaningful

### Important nuance

On the **first bootstrap run**, add a note that the diary may include backlog from earlier undreamed sessions. After bootstrap, the workflow becomes incremental.

## Cron job creation

Use a cron schedule like:

```json
{
  "action": "create",
  "name": "dream",
  "schedule": "0 1 * * *",
  "skill": "memory-capture-layering",
  "script": "dream.py",
  "deliver": "origin"
}
```

### Safe-mode prompt requirements

The cron prompt must explicitly say:
- safe mode only,
- do not auto-write built-in memory,
- do not create/patch skills,
- do not write to external providers,
- do not regenerate the diary,
- analyze **only** the undreamed content produced by the script,
- use the `memory-capture-layering` taxonomy,
- and output a concise nightly report.

### Real-mode prompt requirements

The cron prompt must explicitly say:
- real mode is active,
- treat the script output as the only input corpus,
- do not regenerate the diary or re-scan raw sessions,
- promote only high-confidence durable knowledge,
- write built-in memory only when it is compact and always useful,
- patch/create skills only when there is a verified reusable procedure gap,
- write external facts via `fact_store` for query-driven durable project knowledge,
- and update candidate-batch / state promotion metadata after successful writes.

## Output structure for the cron-run agent

Use sections like:

```markdown
# Dream Report
- Mode: safe or real
- Diary: <path>
- Run data: <path>
- Candidate batch: <path>
- Sessions reviewed: <count>

## Applied or proposed built-in memory
- Entry
- Type / Layer / Reason

## Applied or proposed skill actions
- Create or Patch
- Why this is a reusable procedure

## Applied or proposed external-memory facts
- Fact / relationship
- Why deep recall is the right layer

## Rejected / no-save items
- What not to save and why

## Operator note
- Any suggested policy changes
```

If there is no new content, the report should say so clearly and stop.

## Safe-mode philosophy

Safe mode is intentionally asymmetric:
- **Diary/state/run-payload/candidate-batch writes are allowed**
- **Durable memory writes are not**

This gives you nightly consolidation and observability without risking memory pollution, while preserving a backfill-ready staging layer for later promotion.

## Pitfalls

### 1. Reprocessing the whole backlog every night
Fix: maintain per-session processed counts in `state.json`.

### 2. Treating diary as memory
Diary is just an index and retrospective aid. Do not inject it into prompt as always-on memory.

### 3. Letting the cron-run agent mutate memory during early rollout
Start report-only first. Review quality before enabling any auto-write path.

### 4. Feeding raw tool output into nightly classification
Filter out tool chatter before constructing the run payload.

### 5. Forgetting bootstrap semantics
The first run may look noisy because it catches all undreamed history. Document that explicitly.

## External provider setup

For the normal Hermes runtime, enable **Holographic** as the active external provider in `~/.hermes/config.yaml`:

```yaml
memory:
  provider: holographic
```

Verification pattern:
- config reads back `memory.provider = holographic`
- `load_memory_provider('holographic')` succeeds
- `system_prompt_block()` is non-empty after initialize
- tool schemas include `fact_store` and `fact_feedback`

Important: the dream job can stay **report-only** even when Holographic is enabled for the main agent runtime.

## Upgrade path

A practical progression is:

1. **Safe mode**
   - diary + state + run payload + candidate batch
   - proposal-only report
   - no durable writes
2. **Real mode**
   - keep the same staging artifacts
   - allow conservative durable writes when confidence is high
   - mark promotion_status in candidate batches and state after successful writes
3. **Later refinements**
   - optional dedupe against same-day skill patches
   - optional stronger heuristics for built-in-memory confidence
   - optional operator dashboards on promotion history

Do not jump straight to aggressive autonomous writing.

## Verification

After implementation:

1. Run the script manually once
2. Confirm diary, run payload, and state file were written
3. Run it again immediately
4. Confirm it reports zero new content
5. Verify the cron job is scheduled for `0 1 * * *`
6. Inspect the first nightly report for proposal quality

## Remember

The reusable pattern here is:
**script for deterministic incremental bookkeeping + agent for conservative nightly judgment**.
