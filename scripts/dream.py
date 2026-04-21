#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


def hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))).expanduser()


HOME = hermes_home()
SESSIONS_DIR = HOME / "sessions"
DREAM_DIR = HOME / "dream"
DIARY_DIR = DREAM_DIR / "diary"
RUNS_DIR = DREAM_DIR / "runs"
CANDIDATES_DIR = DREAM_DIR / "candidates"
STATE_PATH = DREAM_DIR / "state.json"
CONFIG_PATH = DREAM_DIR / "config.json"

SYSTEM_ROLES = {"system", "developer"}
SKIP_ASSISTANT_EMPTY = True
MAX_MESSAGE_RENDER = 18
DEFAULT_TOP_TOPICS_PER_SESSION = 4
DEFAULT_TOP_GROUPS_IN_SUMMARY = 8
TOP_TOPICS_PER_SESSION = DEFAULT_TOP_TOPICS_PER_SESSION
TOP_GROUPS_IN_SUMMARY = DEFAULT_TOP_GROUPS_IN_SUMMARY

AUTO_SKILL_REVIEW_PROMPT_PREFIX = "Review the conversation above and consider saving or updating a skill if appropriate."

REPO_PATTERNS = [
    re.compile(r"\b[a-z0-9]+(?:[-_][a-z0-9]+){1,}\b", re.I),
    re.compile(r"(?:(?:~|/)[^\s`]+)+"),
    re.compile(r"\b[A-Za-z]:\\[^\s`]+"),
]

TOPIC_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("memory", ("memory", "holographic", "fact_store", "dream", "diary", "session_search")),
    ("skills", ("skill", "skills", "skill_manage", "skill_view")),
    ("cron", ("cron", "scheduler", "schedule", "heartbeat")),
    ("discord", ("discord", "channel", "server", "mention", "telegram", "slack")),
    ("video", ("video", "ffmpeg", "trim", "mix", "asset", "cta")),
    ("docs", ("docs", "documentation", "agents.md", "readme", "spec")),
    ("notion", ("notion",)),
    ("testing", ("pytest", "test", "tests", "debug", "failure")),
    ("tools", ("tool", "browser_", "terminal", "patch", "execute_code")),
]


DEFAULT_COMMON_PATH_PARTS = {
    ".git",
    ".hermes",
    "agent",
    "app",
    "apps",
    "asset",
    "assets",
    "bin",
    "build",
    "candidate",
    "candidates",
    "config",
    "configs",
    "data",
    "diary",
    "doc",
    "docs",
    "file",
    "files",
    "home",
    "lib",
    "module",
    "modules",
    "package",
    "packages",
    "pkg",
    "repo",
    "repos",
    "run",
    "runs",
    "script",
    "scripts",
    "service",
    "services",
    "skill",
    "skills",
    "src",
    "state",
    "states",
    "template",
    "templates",
    "test",
    "tests",
    "tmp",
    "tool",
    "tools",
    "ubuntu",
    "user",
    "users",
    "workspace",
    "workspaces",
}

DEFAULT_PROJECT_CONTEXT_MARKERS = (
    "repo",
    "repository",
    "project",
    "workspace",
    "package",
    "module",
    "service",
    "folder",
    "directory",
    "codebase",
    "github",
    "git",
    "~/",
    "/",
    ".py",
    ".md",
    ".json",
)

COMMON_PATH_PARTS = set(DEFAULT_COMMON_PATH_PARTS)
PROJECT_CONTEXT_MARKERS = tuple(DEFAULT_PROJECT_CONTEXT_MARKERS)


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def parse_iso(text: str | None) -> datetime | None:
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_state() -> dict[str, Any]:
    return load_json(
        STATE_PATH,
        {
            "last_run_at": None,
            "sessions": {},
            "candidate_batches": [],
        },
    )


def load_dream_config() -> dict[str, Any]:
    config = load_json(CONFIG_PATH, {"mode": "safe"})
    if not isinstance(config, dict):
        config = {"mode": "safe"}
    promotion = config.get("promotion")
    if not isinstance(promotion, dict):
        promotion = {}
    config["promotion"] = promotion
    return config


def load_dream_mode() -> str:
    config = load_dream_config()
    mode = str(config.get("mode", "safe")).strip().lower()
    if mode not in {"safe", "real"}:
        return "safe"
    return mode


def snapshot_promotion_policy(config: dict[str, Any]) -> dict[str, str]:
    promotion = config.get("promotion") if isinstance(config, dict) else {}
    if not isinstance(promotion, dict):
        promotion = {}
    return {
        "adapter": str(promotion.get("adapter", "hermes") or "hermes").strip().lower() or "hermes",
        "built_in": str(promotion.get("built_in", "manual") or "manual").strip().lower() or "manual",
        "skills": str(promotion.get("skills", "manual") or "manual").strip().lower() or "manual",
        "external": str(promotion.get("external", "manual") or "manual").strip().lower() or "manual",
    }



def _clean_str_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        item = value.strip()
        if not item:
            continue
        if item not in seen:
            cleaned.append(item)
            seen.add(item)
    return cleaned



def load_heuristic_config() -> dict[str, Any]:
    global TOP_TOPICS_PER_SESSION, TOP_GROUPS_IN_SUMMARY, COMMON_PATH_PARTS, PROJECT_CONTEXT_MARKERS

    config = load_json(CONFIG_PATH, {"mode": "safe"})
    heuristics = config.get("heuristics") if isinstance(config, dict) else {}
    if not isinstance(heuristics, dict):
        heuristics = {}

    top_topics = heuristics.get("top_topics_per_session", DEFAULT_TOP_TOPICS_PER_SESSION)
    top_groups = heuristics.get("top_groups_in_summary", DEFAULT_TOP_GROUPS_IN_SUMMARY)
    try:
        TOP_TOPICS_PER_SESSION = max(1, int(top_topics))
    except Exception:
        TOP_TOPICS_PER_SESSION = DEFAULT_TOP_TOPICS_PER_SESSION
    try:
        TOP_GROUPS_IN_SUMMARY = max(1, int(top_groups))
    except Exception:
        TOP_GROUPS_IN_SUMMARY = DEFAULT_TOP_GROUPS_IN_SUMMARY

    extra_path_parts = {item.lower() for item in _clean_str_list(heuristics.get("common_path_parts"))}
    COMMON_PATH_PARTS = set(DEFAULT_COMMON_PATH_PARTS) | extra_path_parts

    extra_markers = tuple(item.lower() for item in _clean_str_list(heuristics.get("project_context_markers")))
    PROJECT_CONTEXT_MARKERS = tuple(dict.fromkeys((*DEFAULT_PROJECT_CONTEXT_MARKERS, *extra_markers)))

    return {
        "top_topics_per_session": TOP_TOPICS_PER_SESSION,
        "top_groups_in_summary": TOP_GROUPS_IN_SUMMARY,
        "common_path_parts": sorted(COMMON_PATH_PARTS),
        "project_context_markers": list(PROJECT_CONTEXT_MARKERS),
    }



def list_session_files() -> list[Path]:
    if not SESSIONS_DIR.exists():
        return []
    return sorted(SESSIONS_DIR.glob("session_*.json"), key=lambda p: p.stat().st_mtime)


def clean_text(value: Any) -> str:
    if isinstance(value, str):
        text = value
    elif isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, dict):
                if item.get("type") == "text" and item.get("text"):
                    parts.append(str(item.get("text")))
                elif item.get("content"):
                    parts.append(str(item.get("content")))
            elif item is not None:
                parts.append(str(item))
        text = "\n".join(part for part in parts if part).strip()
        if not text:
            text = json.dumps(value, ensure_ascii=False)
    else:
        text = json.dumps(value, ensure_ascii=False)
    text = text.replace("\r", " ")
    text = "\n".join(line.rstrip() for line in text.splitlines())
    text = text.strip()

    if text.startswith("[SYSTEM: The user has invoked the ") and "The full skill content is loaded below." in text:
        match = re.search(r'invoked the "([^"]+)" skill', text)
        skill_name = match.group(1) if match else "skill"
        return f"[SYSTEM skill injection omitted: {skill_name}]"

    if text.startswith("[SYSTEM: You are running as a scheduled cron job."):
        return "[SYSTEM cron delivery wrapper omitted]"

    if "## Script Output" in text and text.startswith("[SYSTEM:"):
        return "[SYSTEM cron pre-run payload omitted]"

    return text


def shorten(text: str, limit: int = 220) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def session_preview(messages: list[dict[str, Any]]) -> str:
    for msg in messages:
        if msg.get("role") == "user":
            text = clean_text(msg.get("content", ""))
            if text:
                return shorten(text, 120)
    return "(no user preview)"


def message_keep(msg: dict[str, Any]) -> bool:
    role = msg.get("role", "")
    if role in SYSTEM_ROLES:
        return False
    if role == "tool":
        return False
    if role == "assistant":
        content = clean_text(msg.get("content", ""))
        if SKIP_ASSISTANT_EMPTY and not content:
            return False
    return True


def is_auto_skill_review_prompt(text: str) -> bool:
    return text.startswith(AUTO_SKILL_REVIEW_PROMPT_PREFIX)


def strip_meta_skill_review_turns(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop auto-generated end-of-session skill-review prompts and their direct assistant replies.

    These review turns are bookkeeping scaffolding, not substantive conversation content.
    If kept, dream may misclassify them as fresh work and attempt unsafe skill patches.
    """
    cleaned: list[dict[str, Any]] = []
    skip_next_assistant = False

    for msg in messages:
        role = msg.get("role", "")
        text = clean_text(msg.get("content", ""))

        if role == "user" and is_auto_skill_review_prompt(text):
            skip_next_assistant = True
            continue

        if skip_next_assistant and role == "assistant":
            skip_next_assistant = False
            continue

        if role == "user":
            skip_next_assistant = False

        cleaned.append(msg)

    return cleaned


def normalize_label(text: str) -> str:
    text = text.strip().strip("`*_#:- ")
    text = text.replace("\\", "/")
    text = text.replace("_", "-")
    if not text:
        return ""
    if text.startswith("~/") or text.startswith("/"):
        parts = [p for p in text.split("/") if p and p not in {"home", "brewuser", "mnt", "d", "work"}]
        if parts:
            text = "/".join(parts[-2:]) if len(parts) >= 2 else parts[-1]
    lowered = text.lower()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", lowered):
        return ""
    if re.fullmatch(r"\d{3}-\d{3}-\d{4}", lowered):
        return ""
    if lowered in {"memory", "skills", "dream", "diary", "cron", "docs", "video", "testing", "tools", "discord", "notion"}:
        return lowered
    if re.fullmatch(r'[\\/\",.:;`\-\s]+', text):
        return ""
    if "/" in text and not re.search(r"[A-Za-z0-9]", text.replace("/", "")):
        return ""
    if "/" not in lowered and "." not in lowered and len(lowered) < 4:
        return ""
    if len(text) > 60:
        text = text[:60].rstrip() + "…"
    return text



def looks_like_project_token(token: str) -> bool:
    lowered = token.lower()
    if "/" in lowered or "." in lowered or len(lowered) < 4:
        return False
    parts = [part for part in re.split(r"[-_]", lowered) if part]
    if len(parts) < 2:
        return False
    if all(len(part) <= 3 for part in parts):
        return False
    return True



def has_project_context(text: str, start: int, end: int) -> bool:
    window = text[max(0, start - 40): min(len(text), end + 40)].lower()
    return "`" in window or any(marker in window for marker in PROJECT_CONTEXT_MARKERS)



def derive_project_candidates(path_label: str) -> list[str]:
    parts = [part for part in path_label.split("/") if part]
    if parts and "." in parts[-1]:
        parts = parts[:-1]
    for part in reversed(parts):
        lowered = part.lower().strip()
        if not lowered or lowered in COMMON_PATH_PARTS:
            continue
        candidate = normalize_label(lowered)
        if not candidate or "/" in candidate or "." in candidate or len(candidate) < 4:
            continue
        return [candidate.lower()]
    return []



def infer_labels(texts: list[str]) -> dict[str, list[str]]:
    repo_hits: Counter[str] = Counter()
    topic_hits: Counter[str] = Counter()
    path_hits: Counter[str] = Counter()

    for text in texts:
        lowered = text.lower()
        for topic, keywords in TOPIC_RULES:
            if any(keyword in lowered for keyword in keywords):
                topic_hits[topic] += 1

        for pattern in REPO_PATTERNS:
            for match in pattern.finditer(text):
                label = normalize_label(match.group(0))
                if not label:
                    continue
                if "/" in label or label.endswith(".py") or label.endswith(".md"):
                    path_hits[label] += 1
                    for candidate in derive_project_candidates(label):
                        repo_hits[candidate] += 2
                elif looks_like_project_token(label) and has_project_context(text, match.start(), match.end()):
                    repo_hits[label.lower()] += 1

    project_candidates = [name for name, _ in repo_hits.most_common(TOP_TOPICS_PER_SESSION)]
    path_candidates = [name for name, _ in path_hits.most_common(2)]
    topic_candidates = [name for name, _ in topic_hits.most_common(TOP_TOPICS_PER_SESSION)]

    primary = project_candidates[0] if project_candidates else (topic_candidates[0] if topic_candidates else "general")

    labels = []
    seen = set()
    for item in [primary, *project_candidates, *topic_candidates, *path_candidates]:
        if item and item not in seen:
            labels.append(item)
            seen.add(item)
    return {
        "primary": primary,
        "projects": project_candidates,
        "topics": topic_candidates,
        "paths": path_candidates,
        "labels": labels[:8],
    }



def extract_incremental_session(path: Path, state: dict[str, Any]) -> dict[str, Any] | None:
    raw = load_json(path, None)
    if not isinstance(raw, dict):
        return None
    session_id = raw.get("session_id") or path.stem.replace("session_", "")
    platform = raw.get("platform") or "unknown"
    if platform == "cron":
        return None
    messages = raw.get("messages") or []
    if not isinstance(messages, list):
        return None

    processed = state.get("sessions", {}).get(session_id, {})
    processed_count = int(processed.get("processed_message_count", 0) or 0)
    new_messages = messages[processed_count:]
    kept = [m for m in new_messages if isinstance(m, dict) and message_keep(m)]
    kept = strip_meta_skill_review_turns(kept)

    session_start = parse_iso(raw.get("session_start"))
    last_updated = parse_iso(raw.get("last_updated"))
    text_samples = [clean_text(m.get("content", "")) for m in kept if clean_text(m.get("content", ""))]
    inferred = infer_labels(text_samples)

    return {
        "session_id": session_id,
        "platform": platform,
        "model": raw.get("model") or "unknown",
        "session_start": session_start.isoformat() if session_start else None,
        "last_updated": last_updated.isoformat() if last_updated else None,
        "message_count_total": len(messages),
        "new_message_count_raw": len(new_messages),
        "new_message_count": len(kept),
        "preview": session_preview(messages),
        "messages": kept,
        "raw_path": str(path),
        "inferred": inferred,
    }


def pick_diary_date(run_at: datetime) -> str:
    target = run_at - timedelta(days=1) if run_at.hour < 6 else run_at
    return target.date().isoformat()


def render_transcript(messages: list[dict[str, Any]], limit: int = MAX_MESSAGE_RENDER) -> str:
    rendered = []
    for msg in messages[:limit]:
        role = msg.get("role", "unknown")
        text = shorten(clean_text(msg.get("content", "")), 500)
        if not text:
            continue
        rendered.append(f"- {role}: {text}")
    omitted = max(0, len(messages) - limit)
    if omitted:
        rendered.append(f"- … {omitted} more kept messages omitted")
    return "\n".join(rendered)


def summarize_groups(sessions: list[dict[str, Any]]) -> list[tuple[str, list[dict[str, Any]]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sess in sessions:
        grouped[sess["inferred"]["primary"]].append(sess)
    ordered = sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))
    return ordered


def build_candidate_batch(config: dict[str, Any], dream_mode: str, run_at: datetime, diary_date: str, sessions: list[dict[str, Any]], diary_path: Path) -> dict[str, Any]:
    grouped = summarize_groups(sessions)
    promotion_policy = snapshot_promotion_policy(config)
    return {
        "schema_version": "2.0",
        "status": "pending_review",
        "mode": dream_mode,
        "created_at": run_at.isoformat() + "Z",
        "diary_date": diary_date,
        "diary_path": str(diary_path),
        "candidate_count": len(sessions),
        "promotion_policy": promotion_policy,
        "promotion_status": {
            "built_in": "not_evaluated",
            "skills": "not_evaluated",
            "external": "not_evaluated",
        },
        "backfill_ready": True,
        "groups": [
            {
                "name": name,
                "session_ids": [row["session_id"] for row in items],
                "count": len(items),
            }
            for name, items in grouped
        ],
        "sessions": [
            {
                "session_id": row["session_id"],
                "preview": row["preview"],
                "platform": row["platform"],
                "model": row["model"],
                "last_updated": row["last_updated"],
                "new_message_count": row["new_message_count"],
                "inferred": row["inferred"],
                "messages": [
                    {
                        "role": msg.get("role"),
                        "content": clean_text(msg.get("content", "")),
                    }
                    for msg in row["messages"]
                ],
            }
            for row in sessions
        ],
        "notes": [
            "This candidate batch preserves reviewed inputs so later audits, backfills, and promotions stay possible.",
            "A batch marked pending_review should not be treated as committed memory until promotion is applied.",
        ],
    }


def build_diary_markdown(dream_mode: str, diary_date: str, run_at: datetime, sessions: list[dict[str, Any]], state_before: dict[str, Any]) -> str:
    lines: list[str] = []
    previous_run = state_before.get("last_run_at") or "none"
    first_run = previous_run == "none"
    lines.append(f"# Diary {diary_date}")
    lines.append("")
    lines.append(f"- Generated by `dream` {dream_mode} mode")
    lines.append(f"- Run at: {run_at.isoformat()}Z")
    lines.append(f"- Sessions touched: {len(sessions)}")
    lines.append(f"- Previous dream run: {previous_run}")
    if first_run:
        lines.append("- Bootstrap run: this diary may include backlog from earlier undreamed sessions.")
    lines.append("")

    if not sessions:
        lines.append("## Summary")
        lines.append("")
        lines.append("No new undreamed conversation content was found.")
        return "\n".join(lines) + "\n"

    role_counter: Counter[str] = Counter()
    total_kept = 0
    topic_counter: Counter[str] = Counter()
    path_counter: Counter[str] = Counter()
    for sess in sessions:
        for msg in sess["messages"]:
            role_counter[msg.get("role", "unknown")] += 1
            total_kept += 1
        for topic in sess["inferred"].get("topics", []):
            topic_counter[topic] += 1
        for item in sess["inferred"].get("paths", []):
            path_counter[item] += 1

    grouped = summarize_groups(sessions)

    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Kept messages reviewed: {total_kept}")
    lines.append(f"- User messages: {role_counter.get('user', 0)}")
    lines.append(f"- Assistant messages: {role_counter.get('assistant', 0)}")
    lines.append("- Primary groups: " + ", ".join(f"`{name}` ({len(items)})" for name, items in grouped[:TOP_GROUPS_IN_SUMMARY]))
    if topic_counter:
        lines.append("- Topics seen: " + ", ".join(f"`{name}` ({count})" for name, count in topic_counter.most_common(TOP_GROUPS_IN_SUMMARY)))
    if path_counter:
        lines.append("- Paths / repos seen: " + ", ".join(f"`{name}`" for name, _ in path_counter.most_common(6)))
    lines.append("")

    lines.append("## Grouped Index")
    lines.append("")
    for name, items in grouped:
        lines.append(f"### {name}")
        lines.append("")
        for sess in items:
            updated = sess.get("last_updated") or "unknown"
            labels = ", ".join(f"`{label}`" for label in sess["inferred"].get("labels", []) if label != name)
            suffix = f" | labels: {labels}" if labels else ""
            lines.append(f"- `{sess['session_id']}` ({sess['platform']}, {sess['model']}, updated {updated}) — {sess['preview']}{suffix}")
        lines.append("")

    lines.append("## Session Details")
    lines.append("")
    for name, items in grouped:
        lines.append(f"### Group: {name}")
        lines.append("")
        for sess in items:
            inferred = sess["inferred"]
            lines.append(f"#### {sess['session_id']}")
            lines.append("")
            lines.append(f"- Platform: {sess['platform']}")
            lines.append(f"- Model: {sess['model']}")
            lines.append(f"- Preview: {sess['preview']}")
            lines.append(f"- New kept messages: {sess['new_message_count']}")
            lines.append(f"- Primary: `{inferred['primary']}`")
            if inferred["projects"]:
                lines.append("- Projects / repos: " + ", ".join(f"`{item}`" for item in inferred["projects"]))
            if inferred["topics"]:
                lines.append("- Topics: " + ", ".join(f"`{item}`" for item in inferred["topics"]))
            if inferred["paths"]:
                lines.append("- Paths: " + ", ".join(f"`{item}`" for item in inferred["paths"]))
            lines.append("")
            lines.append(render_transcript(sess["messages"]))
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    state = load_state()
    dream_config = load_dream_config()
    dream_mode = load_dream_mode()
    heuristic_config = load_heuristic_config()
    promotion_policy = snapshot_promotion_policy(dream_config)
    run_at = utcnow()
    diary_date = pick_diary_date(run_at)

    DIARY_DIR.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)
    session_files = list_session_files()
    session_rows: list[dict[str, Any]] = []
    processed_rows: list[dict[str, Any]] = []

    for path in session_files:
        row = extract_incremental_session(path, state)
        if not row:
            continue
        if row["new_message_count_raw"] <= 0:
            continue
        processed_rows.append(row)
        if row["new_message_count"] <= 0:
            continue
        session_rows.append(row)

    diary_path = DIARY_DIR / f"diary_{diary_date}.md"
    diary_markdown = build_diary_markdown(dream_mode, diary_date, run_at, session_rows, state)
    diary_path.write_text(diary_markdown, encoding="utf-8")

    grouped = summarize_groups(session_rows)
    candidate_batch = build_candidate_batch(dream_config, dream_mode, run_at, diary_date, session_rows, diary_path)
    candidate_batch_path = CANDIDATES_DIR / f"candidate_batch_{run_at.strftime('%Y%m%dT%H%M%SZ')}.json"
    save_json(candidate_batch_path, candidate_batch)

    run_payload = {
        "schema_version": "2.0",
        "mode": dream_mode,
        "run_at": run_at.isoformat() + "Z",
        "promotion_policy": promotion_policy,
        "diary_date": diary_date,
        "diary_path": str(diary_path),
        "state_path": str(STATE_PATH),
        "candidate_batch_path": str(candidate_batch_path),
        "new_session_count": len(session_rows),
        "heuristics": heuristic_config,
        "groups": [
            {
                "name": name,
                "session_ids": [row["session_id"] for row in items],
                "count": len(items),
            }
            for name, items in grouped
        ],
        "sessions": [
            {
                "session_id": row["session_id"],
                "platform": row["platform"],
                "model": row["model"],
                "last_updated": row["last_updated"],
                "preview": row["preview"],
                "new_message_count": row["new_message_count"],
                "inferred": row["inferred"],
                "messages": [
                    {
                        "role": msg.get("role"),
                        "content": clean_text(msg.get("content", "")),
                    }
                    for msg in row["messages"]
                ],
            }
            for row in session_rows
        ],
        "notes": [
            (
                "Safe mode: generate diary and proposals only; do not auto-write built-in memory, skills, or external memory."
                if dream_mode == "safe"
                else "Real mode: the cron-run agent may promote approved built-in memory, skill updates, and external-memory facts after reviewing the staged candidate batch."
            ),
            "Sessions/messages already processed in prior dream runs were skipped using per-session processed_message_count state.",
            "Diary is intended as a quick daily index of what was worked on.",
            "Sessions are heuristically grouped by inferred project/repo/topic labels for faster review.",
            "A candidate batch file is written on every run so dream results remain auditable and backfill-friendly.",
        ],
    }

    run_path = RUNS_DIR / f"dream_run_{run_at.strftime('%Y%m%dT%H%M%SZ')}.json"
    save_json(run_path, run_payload)

    sessions_state = state.setdefault("sessions", {})
    for row in processed_rows:
        sessions_state[row["session_id"]] = {
            "processed_message_count": row["message_count_total"],
            "last_seen_updated": row.get("last_updated"),
        }
    state["last_run_at"] = run_at.isoformat() + "Z"
    state["last_diary_path"] = str(diary_path)
    state["last_run_path"] = str(run_path)
    state["last_candidate_batch_path"] = str(candidate_batch_path)
    state.setdefault("candidate_batches", []).append(
        {
            "created_at": run_at.isoformat() + "Z",
            "path": str(candidate_batch_path),
            "candidate_count": len(session_rows),
            "status": candidate_batch["status"],
            "promotion_policy": promotion_policy,
            "promotion_status": candidate_batch["promotion_status"],
        }
    )
    state["candidate_batches"] = state["candidate_batches"][-50:]
    save_json(STATE_PATH, state)

    output = {
        "schema_version": "2.0",
        "dream_mode": dream_mode,
        "promotion_policy": promotion_policy,
        "diary_date": diary_date,
        "diary_path": str(diary_path),
        "run_path": str(run_path),
        "candidate_batch_path": str(candidate_batch_path),
        "state_path": str(STATE_PATH),
        "new_session_count": len(session_rows),
        "groups": run_payload["groups"],
        "session_ids": [row["session_id"] for row in session_rows],
        "message_counts": {
            row["session_id"]: row["new_message_count"] for row in session_rows
        },
        "notes": run_payload["notes"],
        "sessions": run_payload["sessions"],
    }
    try:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    except BrokenPipeError:
        pass


if __name__ == "__main__":
    main()
