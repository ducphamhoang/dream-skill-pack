#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


def copy_tree(src: Path, dst: Path, force: bool = False) -> None:
    if dst.exists():
        if not force:
            raise FileExistsError(f"Destination already exists: {dst}")
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def copy_file(src: Path, dst: Path, force: bool = False) -> None:
    if dst.exists() and not force:
        raise FileExistsError(f"Destination already exists: {dst}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def write_json(src: Path, dst: Path, force: bool = False, mode_override: str | None = None) -> None:
    if dst.exists() and not force:
        raise FileExistsError(f"Destination already exists: {dst}")
    data = json.loads(src.read_text(encoding="utf-8"))
    if mode_override is not None:
        data["mode"] = mode_override
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Install dream-skill-pack into a Hermes home")
    parser.add_argument("--hermes-home", default=str(Path.home() / ".hermes"), help="Target HERMES_HOME (default: ~/.hermes)")
    parser.add_argument("--mode", choices=["safe", "real"], default=None, help="Initialize dream/config.json with this mode")
    parser.add_argument("--force", action="store_true", help="Overwrite existing installed files")
    parser.add_argument("--print-cron-hint", action="store_true", help="Print suggested cronjob prompt reminder after install")
    args = parser.parse_args()

    pack_root = Path(__file__).resolve().parent
    hermes_home = Path(args.hermes_home).expanduser().resolve()

    src_skill_root = pack_root / "skills" / "software-development"
    src_dream_skill = src_skill_root / "nightly-dream-safe-mode"
    src_memory_skill = src_skill_root / "memory-capture-layering"
    src_promoter_skill = src_skill_root / "dream-promoter-instructions"
    src_script = pack_root / "scripts" / "dream.py"
    src_config = pack_root / "config-templates" / "dream.config.json"
    src_state = pack_root / "state-templates" / "dream.state.json"

    dst_skill_root = hermes_home / "skills" / "software-development"
    dst_dream_skill = dst_skill_root / "nightly-dream-safe-mode"
    dst_memory_skill = dst_skill_root / "memory-capture-layering"
    dst_promoter_skill = dst_skill_root / "dream-promoter-instructions"
    dst_script = hermes_home / "scripts" / "dream.py"
    dst_config = hermes_home / "dream" / "config.json"
    dst_state = hermes_home / "dream" / "state.json"

    for required in [src_dream_skill / "SKILL.md", src_memory_skill / "SKILL.md", src_promoter_skill / "SKILL.md", src_script, src_config, src_state]:
        if not required.exists():
            raise FileNotFoundError(f"Missing bundle asset: {required}")

    dst_skill_root.mkdir(parents=True, exist_ok=True)
    (hermes_home / "scripts").mkdir(parents=True, exist_ok=True)
    (hermes_home / "dream").mkdir(parents=True, exist_ok=True)

    copy_tree(src_dream_skill, dst_dream_skill, force=args.force)
    copy_tree(src_memory_skill, dst_memory_skill, force=args.force)
    copy_tree(src_promoter_skill, dst_promoter_skill, force=args.force)
    copy_file(src_script, dst_script, force=args.force)
    write_json(src_config, dst_config, force=args.force, mode_override=args.mode)
    write_json(src_state, dst_state, force=args.force)

    result = {
        "installed_to": str(hermes_home),
        "skills": [str(dst_dream_skill), str(dst_memory_skill), str(dst_promoter_skill)],
        "script": str(dst_script),
        "dream_config": str(dst_config),
        "dream_state": str(dst_state),
        "mode": args.mode or "safe",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.print_cron_hint:
        print("\nNext steps:")
        print("- Ensure the target Hermes config has any desired external memory provider enabled.")
        print("- Recreate/update the cron job so it uses script=dream.py and loads memory-capture-layering + dream-promoter-instructions.")
        print("- Run the script once manually to verify diary/run/candidate output before the first scheduled run.")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
