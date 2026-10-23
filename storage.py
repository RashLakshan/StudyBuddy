"""
storage.py – JSON persistence helpers for Study Buddy AI.

All reading and writing goes through these functions to avoid
scattered JSON logic and prevent data corruption.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import config

logger = logging.getLogger(__name__)

# ── Generic helpers ──────────────────────────────────────────────────────────

def _read_json(filepath: str, default: Any) -> Any:
    """
    Safely read a JSON file.

    Returns *default* when the file is absent or contains invalid JSON,
    logging the issue without crashing.
    """
    if not os.path.exists(filepath):
        logger.debug("JSON file not found, using default: %s", filepath)
        return default

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON in %s: %s – returning default.", filepath, exc)
        return default
    except OSError as exc:
        logger.error("Cannot read %s: %s – returning default.", filepath, exc)
        return default


def _write_json(filepath: str, data: Any) -> None:
    """
    Write *data* to *filepath* as UTF-8 JSON.

    Raises OSError if the write fails so callers can report the error.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── Quiz progress ────────────────────────────────────────────────────────────

def load_progress() -> dict:
    """Return the full progress store (dict with a 'records' list)."""
    data = _read_json(config.PROGRESS_FILE, {"records": []})
    if not isinstance(data, dict) or "records" not in data:
        logger.warning("progress.json has unexpected structure – resetting.")
        return {"records": []}
    return data


def save_progress(data: dict) -> None:
    """Persist the full progress store."""
    _write_json(config.PROGRESS_FILE, data)


def append_quiz_record(topic: str, score: int, total: int) -> dict:
    """
    Append a single quiz record and persist.

    Returns the saved record on success.
    Raises ValueError for invalid arguments.
    """
    topic = topic.strip()
    if not topic:
        raise ValueError("Topic must not be empty.")
    if len(topic) > config.MAX_TOPIC_LENGTH:
        raise ValueError(f"Topic is too long (max {config.MAX_TOPIC_LENGTH} chars).")
    if not isinstance(total, int) or total <= 0 or total > 1000:
        raise ValueError("Total must be a positive integer no greater than 1000.")
    if not isinstance(score, int) or score < 0 or score > total:
        raise ValueError(f"Score must be between 0 and {total}.")

    record = {
        "topic": topic,
        "score": score,
        "total": total,
        "percentage": round(score / total * 100, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    data = load_progress()
    data["records"].append(record)
    save_progress(data)
    return record


def get_progress_records(topic_filter: str = "") -> list:
    """
    Return quiz records, optionally filtered by topic (case-insensitive).
    """
    data = load_progress()
    records = data.get("records", [])
    if topic_filter:
        topic_filter = topic_filter.strip().lower()
        records = [
            r for r in records
            if topic_filter in r.get("topic", "").lower()
        ]
    return records


# ── Study plans ──────────────────────────────────────────────────────────────

def load_study_plans() -> dict:
    """Return the full study-plans store (dict with a 'plans' list)."""
    data = _read_json(config.STUDY_PLANS_FILE, {"plans": []})
    if not isinstance(data, dict) or "plans" not in data:
        logger.warning("study_plans.json has unexpected structure – resetting.")
        return {"plans": []}
    return data


def save_study_plans(data: dict) -> None:
    """Persist the full study-plans store."""
    _write_json(config.STUDY_PLANS_FILE, data)


def append_study_plan(topic: str, plan: str) -> dict:
    """
    Append a study plan and persist.

    Returns the saved plan record on success.
    Raises ValueError for invalid arguments.
    """
    topic = topic.strip()
    plan = plan.strip()
    if not topic:
        raise ValueError("Topic must not be empty.")
    if len(topic) > config.MAX_TOPIC_LENGTH:
        raise ValueError(f"Topic is too long (max {config.MAX_TOPIC_LENGTH} chars).")
    if not plan:
        raise ValueError("Plan must not be empty.")
    if len(plan) > config.MAX_PLAN_LENGTH:
        raise ValueError(f"Plan is too long (max {config.MAX_PLAN_LENGTH} chars).")

    record = {
        "topic": topic,
        "plan": plan,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    data = load_study_plans()
    data["plans"].append(record)
    save_study_plans(data)
    return record


def get_study_plans(topic_filter: str = "") -> list:
    """Return study plans, optionally filtered by topic."""
    data = load_study_plans()
    plans = data.get("plans", [])
    if topic_filter:
        topic_filter = topic_filter.strip().lower()
        plans = [
            p for p in plans
            if topic_filter in p.get("topic", "").lower()
        ]
    return plans


# ── Agent execution trace ────────────────────────────────────────────────────

def append_trace(entry: dict) -> None:
    """
    Append a single trace entry (JSON Lines format) to the agent trace log.

    Each entry should be a dict with at minimum:
        step, node, tool_name (optional), args (optional), result_summary
    """
    entry.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    os.makedirs(config.LOGS_DIR, exist_ok=True)
    try:
        with open(config.AGENT_TRACE_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as exc:
        logger.error("Could not write trace entry: %s", exc)
