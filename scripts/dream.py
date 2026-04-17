#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
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
TOP_TOPICS_PER_SESSION = 4
TOP_GROUPS_IN_SUMMARY = 8

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


KNOWN_PROJECT_HINTS = [
    "py-hbs-ads",
    "hbs-ads",
    "hermes-agent",
    "mygame_ads",
    "video-library",
    "video-workspace",
]

GENERIC_LABELS = {
    "built-in",
    "long-term",
    "report-only",
    "safe-mode",
    "real-mode",
    "always-on",
    "query-driven",
    "one-off",
    "tool-system",
    "type-layer-reason",
    "low-confidence",
    "backfill-ready",
    "backfill-friendly",
    "pending-review",
    "promotion-status",
}


def utcnow() -> datetime:
    return datetime.utcnow()


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


def load_dream_mode() -> str:
    config = load_json(CONFIG_PATH, {"mode": "safe"})
    mode = str(config.get("mode", "safe")).strip().lower()
    if mode not in {"safe", "real"}:
        return "safe"
    return mode


def list_session_files() -> list[Path]:
    if not SESSIONS_DIR.exists():
        return []
    return sorted(SESSIONS_DIR.glob("session_*.json"), key=lambda p: p.stat().st_mtime)


def clean_text(value: Any) -> str:
    if isinstance(value, str):
        text = value
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
    if lowered in GENERIC_LABELS:
        return ""
    if lowered in {"memory", "skills", "dream", "diary", "cron", "docs", "video", "testing", "tools", "discord", "notion"}:
        return lowered
    if re.fullmatch(r'[\\/",.:;`\-\s]+', text):
        return ""
    if "/" in text and not re.search(r"[A-Za-z0-9]", text.replace("/", "")):
        return ""
    if "/" not in lowered and "." not in lowered and len(lowered) < 4:
        return ""
    if len(text) > 60:
        text = text[:60].rstrip() + "…"
    return text



def infer_labels(texts: list[str]) -> dict[str, list[str]]:
    repo_hits: Counter[str] = Counter()
    topic_hits: Counter[str] = Counter()
    path_hits: Counter[str] = Counter()

    joined = "\n".join(t for t in texts if t)
    lower_joined = joined.lower()

    for hint in KNOWN_PROJECT_HINTS:
        if hint in lower_joined:
            repo_hits[hint] += 4

    for text in texts:
        lowered = text.lower()
        for topic, keywords in TOPIC_RULES:
            if any(keyword in lowered for keyword in keywords):
                topic_hits[topic] += 1

        for pattern in REPO_PATTERNS:
            for match in pattern.findall(text):
                label = normalize_label(match)
                if not label:
                    continue
                if "/" in label or label.endswith(".py") or label.endswith(".md"):
                    path_hits[label] += 1
                elif "-" in label:
                    repo_hits[label.lower()] += 1

    project_candidates = [name for name, _ in repo_hits.most_common(TOP_TOPICS_PER_SESSION)]
    path_candidates = [name for name, _ in path_hits.most_common(2)]
    topic_candidates = [name for name, _ in topic_hits.most_common(TOP_TOPICS_PER_SESSION)]

    primary = project_candidates[0] if project_candidates else (topic_candidates[0] if topic_candidates else "general")
    if primary in GENERIC_LABELS:
        primary = topic_candidates[0] if topic_candidates else "general"

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
    messages = raw.get("messages") or []
    if not isinstance(messages, list):
        return None

    processed = state.get("sessions", {}).get(session_id, {})
    processed_count = int(processed.get("processed_message_count", 0) or 0)
    new_messages = messages[processed_count:]
    kept = [m for m in new_messages if isinstance(m, dict) and message_keep(m)]

    session_start = parse_iso(raw.get("session_start"))
    last_updated = parse_iso(raw.get("last_updated"))
    text_samples = [clean_text(m.get("content", "")) for m in kept if clean_text(m.get("content", ""))]
    inferred = infer_labels(text_samples)

    return {
        "session_id": session_id,
        "platform": raw.get("platform") or "unknown",
        "model": raw.get("model") or "unknown",
        "session_start": session_start.isoformat() if session_start else None,
        "last_updated": last_updated.isoformat() if last_updated else None,
        "message_count_total": len(messages),
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


def build_candidate_batch(dream_mode: str, run_at: datetime, diary_date: str, sessions: list[dict[str, Any]], diary_path: Path) -> dict[str, Any]:
    grouped = summarize_groups(sessions)
    return {
        "status": "pending_review",
        "mode": dream_mode,
        "created_at": run_at.isoformat() + "Z",
        "diary_date": diary_date,
        "diary_path": str(diary_path),
        "candidate_count": len(sessions),
        "promotion_status": {
            "built_in": "not_applied",
            "skills": "not_applied",
            "external": "not_applied",
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
    run_at = utcnow()
    dream_mode = load_dream_mode()
    diary_date = pick_diary_date(run_at)

    DIARY_DIR.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)

    state = load_state()
    session_files = list_session_files()
    session_rows: list[dict[str, Any]] = []

    for path in session_files:
        row = extract_incremental_session(path, state)
        if not row:
            continue
        if row["new_message_count"] <= 0:
            continue
        session_rows.append(row)

    diary_path = DIARY_DIR / f"diary_{diary_date}.md"
    diary_markdown = build_diary_markdown(dream_mode, diary_date, run_at, session_rows, state)
    diary_path.write_text(diary_markdown, encoding="utf-8")

    grouped = summarize_groups(session_rows)
    candidate_batch = build_candidate_batch(dream_mode, run_at, diary_date, session_rows, diary_path)
    candidate_batch_path = CANDIDATES_DIR / f"candidate_batch_{run_at.strftime('%Y%m%dT%H%M%SZ')}.json"
    save_json(candidate_batch_path, candidate_batch)

    run_payload = {
        "mode": dream_mode,
        "run_at": run_at.isoformat() + "Z",
        "diary_date": diary_date,
        "diary_path": str(diary_path),
        "state_path": str(STATE_PATH),
        "candidate_batch_path": str(candidate_batch_path),
        "new_session_count": len(session_rows),
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
    for row in session_rows:
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
        }
    )
    state["candidate_batches"] = state["candidate_batches"][-50:]
    save_json(STATE_PATH, state)

    output = {
        "dream_mode": dream_mode,
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
