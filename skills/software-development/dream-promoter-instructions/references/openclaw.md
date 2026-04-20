# OpenClaw style promoter adapter

Use this adapter when Dream output is being consumed by an OpenClaw-like agent runtime.

## Principle
The promotion layer is runtime-specific and may change frequently.

## Suggested flow
- built-in memory -> update the runtime's always-loaded memory source
- skills/procedures -> patch reusable prompt/skill docs used by that runtime
- external facts -> store in whichever query-time memory/retrieval mechanism the runtime supports

## Rules
- Keep staging and classification portable.
- Keep write instructions local to the runtime.
- If the runtime lacks a safe write path, leave promotion in manual mode and report that explicitly.
