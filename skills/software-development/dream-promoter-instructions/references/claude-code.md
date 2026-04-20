# Claude Code style promoter adapter

Use this adapter when the runtime does not expose Hermes memory tools directly.

## Principle
Treat promotion as an instruction-following workflow, not a fixed API contract.

## Typical write paths
- built-in memory -> update the runtime's memory file, agent instructions, or persistent note file
- skills/playbooks -> patch reusable docs, prompt files, or local agent skill directories
- external/project facts -> write into the runtime's structured note store, database, or retrieval layer if available

## Rules
- Prefer explicit file edits over hidden assumptions.
- If there is no durable write interface, stop after classification and report the missing adapter capability.
- Record what was applied in the candidate-batch audit metadata.
