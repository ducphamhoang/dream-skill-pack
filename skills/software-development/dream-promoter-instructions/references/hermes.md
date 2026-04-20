# Hermes promoter adapter

Use this adapter when Dream runs inside Hermes and promotion is allowed.

## Built-in memory
- Use `memory(...)` for compact always-on facts.
- Prefer `target=user` for user identity/preferences.
- Prefer `target=memory` for stable environment/project conventions.
- Keep entries compact.

## Skills
- Use `skill_manage(...)` when the staged candidate is a reusable procedure.
- Prefer patching an existing skill over creating a near-duplicate.
- If the runtime skill tooling is unavailable or blocked, report that clearly and leave `promotion_status.skills` as `manual_review` or `blocked`.

## External memory
- Use `fact_store(...)` for durable project/system facts that are query-driven rather than always-on.
- Save small composable facts instead of transcript dumps.
- If helpful, later rate the saved fact with `fact_feedback(...)` after it proves useful.

## Candidate-batch audit updates
After successful writes, update the candidate batch and/or state file so it records what actually happened.
Suggested statuses:
- `applied`
- `manual_review`
- `disabled`
- `blocked`
- `not_applied`

## Safe default
If `dream/config.json` does not explicitly allow auto-apply for a layer, classify the candidate but do not write it automatically.
