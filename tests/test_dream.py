import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "dream.py"


def _load_dream_module(module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_candidate_batch_stages_schema_version_and_policy(tmp_path, monkeypatch):
    hermes_home = tmp_path / ".hermes"
    dream_dir = hermes_home / "dream"
    dream_dir.mkdir(parents=True)
    (dream_dir / "config.json").write_text(
        '{\n'
        '  "mode": "real",\n'
        '  "promotion": {\n'
        '    "adapter": "hermes",\n'
        '    "built_in": "auto_on_real",\n'
        '    "skills": "manual",\n'
        '    "external": "disabled"\n'
        '  }\n'
        '}\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))

    module = _load_dream_module("dream_pack_test_module")
    config = module.load_dream_config()
    batch = module.build_candidate_batch(
        config,
        "real",
        module.utcnow(),
        "2026-04-21",
        [],
        dream_dir / "diary" / "diary_2026-04-21.md",
    )

    assert batch["schema_version"] == "2.0"
    assert batch["promotion_policy"] == {
        "adapter": "hermes",
        "built_in": "auto_on_real",
        "skills": "manual",
        "external": "disabled",
    }
    assert batch["promotion_status"] == {
        "built_in": "not_evaluated",
        "skills": "not_evaluated",
        "external": "not_evaluated",
    }
