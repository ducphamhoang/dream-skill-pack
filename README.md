# Dream Skill Export Pack

This bundle packages the minimum reusable assets needed to move the current Dream workflow to another agent/runtime.

The pack now treats labeling heuristics as runtime configuration, not hardcoded repo names. Tune them in `dream/config.json` under `heuristics` if a target environment needs extra path-part suppression or custom project-context markers.

## Included
- `skills/software-development/nightly-dream-safe-mode/SKILL.md`
- `skills/software-development/memory-capture-layering/SKILL.md`
- `skills/software-development/dream-promoter-instructions/SKILL.md`
- `scripts/dream.py`
- `config-templates/dream.config.json`
- `state-templates/dream.state.json`
- `manifest.json`

## Why this is more than just copying SKILL.md
The Dream workflow depends on both:
1. procedural guidance in the skill files, and
2. a concrete bookkeeping script (`dream.py`) plus state/config files.

Without `dream.py`, the skill alone does not provide:
- incremental session scanning
- diary writing
- candidate batch creation
- state tracking
- mode stamping (`safe` vs `real`)
- diary hygiene filtering

## Install into another Hermes agent

### One-command installer
From inside this pack:

```bash
./install.sh --hermes-home ~/.hermes --mode safe --print-cron-hint
```

Or directly:

```bash
python3 install.py --hermes-home ~/.hermes --mode real --print-cron-hint
```

Installer behavior:
1. Copies three skill directories into `<HERMES_HOME>/skills/software-development/`
2. Copies `scripts/dream.py` into `<HERMES_HOME>/scripts/dream.py`
3. Bootstraps:
   - `<HERMES_HOME>/dream/config.json`
   - `<HERMES_HOME>/dream/state.json`
   - including heuristic knobs under `dream/config.json -> heuristics` for environment-specific label tuning
4. Leaves cron creation/update as an explicit operator step

## Working architecture from now on
- `dream.py` = staging only
- `memory-capture-layering` = classification policy
- `dream-promoter-instructions` = runtime-specific execution playbook

In Hermes, the real-mode cron run should load both `memory-capture-layering` and `dream-promoter-instructions`.

Useful flags:
- `--mode safe|real` -> initializes `dream/config.json`
- `--force` -> overwrite existing installed pack files
- `--print-cron-hint` -> prints the follow-up checklist

Manual install remains possible too:
1. Copy the skill directories under that agent's local skills dir, or mount this bundle's `skills/` path via `skills.external_dirs`.
2. Copy `scripts/dream.py` into that agent's scripts directory.
3. Create the target dream runtime files:
   - `~/.hermes/dream/config.json` from `config-templates/dream.config.json`
   - `~/.hermes/dream/state.json` from `state-templates/dream.state.json`
4. Create or update the cron job to use `script=dream.py` and load both `memory-capture-layering` and `dream-promoter-instructions`.
5. If real mode should write external facts, ensure the target runtime has an external memory provider configured and exposes `fact_store`.

## Install into a non-Hermes agent
Use the SKILL.md files as playbooks/prompts and port `dream.py` logic into that agent's own:
- session storage format
- scheduler/cron system
- memory-writing interface
- filesystem layout

## Suggested source-of-truth strategy
Keep this bundle in a git repo and treat it as the canonical exportable package. Then either:
- point Hermes agents to it via `skills.external_dirs`, or
- sync/copy from it into other runtimes.
