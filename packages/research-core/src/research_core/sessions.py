"""Compact idea-session sidecars; never merged into the canonical idea automatically."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from .util import SCHEMA_VERSION, atomic_write_json, file_lock, read_json, slug_is_safe, utc_now


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
