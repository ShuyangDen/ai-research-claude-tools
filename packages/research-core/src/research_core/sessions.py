"""Compact idea-session sidecars; never merged into the canonical idea automatically."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .util import (
    SCHEMA_VERSION,
    atomic_write_json,
    atomic_write_text,
    file_lock,
    read_json,
    slug_is_safe,
    utc_now,
)


SESSION_FIELDS = {
    "mode",
    "objective",
    "scope_hash",
    "agreed",
    "contested",
    "open_questions",
    "claim_ids_used",
    "candidate_delta",
    "next_decision",
}

_LIST_FIELDS = {"agreed", "contested", "open_questions", "claim_ids_used"}


def session_path(idea_vault: str | Path, slug: str) -> Path:
    if not slug_is_safe(slug):
        raise ValueError(f"Unsafe idea slug: {slug!r}")
    return Path(idea_vault) / "ideas" / "sessions" / f"{slug}-session.json"


def discussion_log_path(idea_vault: str | Path) -> Path:
    return Path(idea_vault) / "ideas" / "sessions" / "discussion-log.jsonl"


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def record_discussion(
    idea_vault: str | Path,
    slug: str,
    *,
    mode: str,
    objective: str,
    summary: str,
    discussed_at: str | None = None,
) -> dict[str, Any]:
    """Append a compact timestamped event for weekly discussion reporting."""
    if not slug_is_safe(slug):
        raise ValueError(f"Unsafe idea slug: {slug!r}")
    timestamp = discussed_at or utc_now()
    _parse_timestamp(timestamp)
    event = {
        "schema_version": SCHEMA_VERSION,
        "discussed_at": timestamp,
        "slug": slug,
        "mode": str(mode),
        "objective": str(objective),
        "summary": str(summary),
    }
    path = discussion_log_path(idea_vault)
    with file_lock(path):
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        if existing and not existing.endswith("\n"):
            existing += "\n"
        line = json.dumps(event, ensure_ascii=False, sort_keys=True)
        atomic_write_text(path, f"{existing}{line}\n")
    return event


def list_discussions(
    idea_vault: str | Path,
    *,
    since: str,
    until: str,
) -> list[dict[str, Any]]:
    """Return discussion events in the half-open interval [since, until)."""
    start = _parse_timestamp(since)
    end = _parse_timestamp(until)
    if end <= start:
        raise ValueError("until must be later than since")
    path = discussion_log_path(idea_vault)
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
            timestamp = _parse_timestamp(str(event["discussed_at"]))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid discussion log entry at line {line_number}: {exc}") from exc
        if start <= timestamp < end:
            events.append(event)
    return sorted(events, key=lambda item: str(item["discussed_at"]))


def init_session(
    idea_vault: str | Path,
    slug: str,
    *,
    mode: str,
    objective: str,
    scope_hash: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    path = session_path(idea_vault, slug)
    if path.exists() and not overwrite:
        raise FileExistsError(f"Session already exists: {path}")
    now = utc_now()
    value = {
        "schema_version": SCHEMA_VERSION,
        "slug": slug,
        "mode": mode,
        "objective": objective,
        "scope_hash": scope_hash,
        "agreed": [],
        "contested": [],
        "open_questions": [],
        "claim_ids_used": [],
        "candidate_delta": None,
        "next_decision": None,
        "stale": False,
        "previous_scope_hash": None,
        "stale_reason": None,
        "updated_at": now,
    }
    atomic_write_json(path, value)
    return value


def load_session(idea_vault: str | Path, slug: str) -> dict[str, Any]:
    path = session_path(idea_vault, slug)
    if not path.exists():
        raise FileNotFoundError(path)
    return read_json(path)


def _validate_patch(patch: dict[str, Any]) -> None:
    unknown = set(patch) - SESSION_FIELDS
    if unknown:
        raise ValueError(f"Unsupported session fields: {', '.join(sorted(unknown))}")
    for name in _LIST_FIELDS:
        if name in patch and not isinstance(patch[name], list):
            raise ValueError(f"{name} must be a JSON array")


def update_session(idea_vault: str | Path, slug: str, patch: dict[str, Any]) -> dict[str, Any]:
    _validate_patch(patch)
    path = session_path(idea_vault, slug)
    with file_lock(path):
        value = load_session(idea_vault, slug)
        old_scope = value.get("scope_hash")
        new_scope = patch.get("scope_hash", old_scope)
        if old_scope != new_scope:
            value["stale"] = True
            value["previous_scope_hash"] = old_scope
            value["stale_reason"] = "scope_hash_changed"
        for key, item in patch.items():
            if key in _LIST_FIELDS:
                item = list(dict.fromkeys(str(entry) for entry in item))
            value[key] = item
        value["updated_at"] = utc_now()
        atomic_write_json(path, value)
        return value


def parse_field_assignments(values: Iterable[str]) -> dict[str, Any]:
    patch: dict[str, Any] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"Expected FIELD=JSON, got {value!r}")
        name, raw = value.split("=", 1)
        name = name.strip()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = raw
        patch[name] = parsed
    _validate_patch(patch)
    return patch


def apply_json_patch_object(base: dict[str, Any], patch_value: Any) -> dict[str, Any]:
    """Accept an explicit merge object or top-level RFC6902 operations."""
    if isinstance(patch_value, dict):
        result = dict(base)
        result.update(patch_value)
        return result
    if not isinstance(patch_value, list):
        raise ValueError("JSON patch must be an object or a list of operations")
    result = dict(base)
    for operation in patch_value:
        if not isinstance(operation, dict):
            raise ValueError("Each JSON patch operation must be an object")
        op = operation.get("op")
        path = str(operation.get("path", ""))
        if not path.startswith("/") or "/" in path[1:]:
            raise ValueError("Only top-level JSON patch paths are supported")
        field = path[1:]
        if field not in SESSION_FIELDS:
            raise ValueError(f"Unsupported session field: {field}")
        if op in {"add", "replace"}:
            result[field] = operation.get("value")
        elif op == "remove":
            result[field] = [] if field in _LIST_FIELDS else None
        else:
            raise ValueError(f"Unsupported JSON patch operation: {op}")
    return result


def load_patch_argument(value: str) -> Any:
    if value.lstrip().startswith(("{", "[")):
        return json.loads(value)
    candidate = Path(value)
    text = candidate.read_text(encoding="utf-8-sig") if candidate.exists() else value
    return json.loads(text)
