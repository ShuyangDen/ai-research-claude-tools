from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


ACTIVE_QUEUE_STATUSES = {"queued", "in_progress"}
USER_FIELDS = {
    "status",
    "triage_action",
    "pinned",
    "cluster_id",
    "read_depth",
    "rating",
    "feedback",
    "completed_at",
    "skipped_at",
    "user_updated_at",
}
STATUS_RANK = {
    "": 0,
    "expired": 5,
    "queued": 10,
    "backlog": 20,
    "clustered": 40,
    "in_progress": 50,
    "dismissed": 60,
    "skipped": 60,
    "completed": 70,
}
ACTION_RANK = {
    "": 0,
    "backlog": 10,
    "cluster-only": 20,
    "targeted": 30,
    "deep": 40,
    "complete-rough": 50,
    "complete-full": 60,
}


class QueueMergeError(ValueError):
    """Raised when canonical queue JSONL cannot be safely parsed."""


def parse_queue_jsonl(text: str, *, source: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise QueueMergeError(f"Invalid queue JSON in {source} line {line_number}: {exc}") from exc
        if not isinstance(value, dict) or not str(value.get("paper_id", "")).strip():
            raise QueueMergeError(f"Queue record in {source} line {line_number} has no paper_id")
        records.append(value)
    return records


def _normalized_url(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    parsed = urlsplit(raw)
    query = urlencode(
        sorted(
            (key, item)
            for key, item in parse_qsl(parsed.query, keep_blank_values=True)
            if not key.casefold().startswith("utm_")
        )
    )
    return urlunsplit((parsed.scheme.casefold(), parsed.netloc.casefold(), parsed.path.rstrip("/"), query, ""))


def _normalized_title(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def _aliases(record: dict[str, Any]) -> set[str]:
    aliases = {f"paper:{str(record.get('paper_id', '')).casefold()}"}
    identifiers = record.get("identifiers")
    if isinstance(identifiers, dict):
        aliases.update(
            f"identifier:{key.casefold()}:{str(value).strip().casefold()}"
            for key, value in identifiers.items()
            if str(value).strip()
        )
    url = _normalized_url(record.get("url"))
    title = _normalized_title(record.get("title"))
    if url:
        aliases.add(f"url:{url}")
    if len(title) >= 20:
        aliases.add(f"title:{title}")
    return aliases


def _nonempty(value: Any) -> bool:
    return value not in (None, "", [], {})


def _newer_record(local: dict[str, Any], remote: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    local_seen = str(local.get("last_seen", ""))
    remote_seen = str(remote.get("last_seen", ""))
    # The remote side carries the latest scheduled recommendation metadata;
    # prefer it on equal discovery dates while merging user state separately.
    return (remote, local) if remote_seen >= local_seen else (local, remote)


def _user_source(local: dict[str, Any], remote: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], bool]:
    local_time = str(local.get("user_updated_at", ""))
    remote_time = str(remote.get("user_updated_at", ""))
    if local_time or remote_time:
        return (remote, local, True) if remote_time > local_time else (local, remote, True)
    local_rank = STATUS_RANK.get(str(local.get("status", "")).casefold(), 5)
    remote_rank = STATUS_RANK.get(str(remote.get("status", "")).casefold(), 5)
    if remote_rank > local_rank:
        return remote, local, False
    if local_rank > remote_rank:
        return local, remote, False
    local_action = ACTION_RANK.get(str(local.get("triage_action", "")).casefold(), 5)
    remote_action = ACTION_RANK.get(str(remote.get("triage_action", "")).casefold(), 5)
    return (remote, local, False) if remote_action > local_action else (local, remote, False)


def merge_queue_record(local: dict[str, Any], remote: dict[str, Any]) -> dict[str, Any]:
    newest, older = _newer_record(local, remote)
    merged = dict(newest)
    for key, value in older.items():
        if not _nonempty(merged.get(key)) and _nonempty(value):
            merged[key] = value

    merged["paper_id"] = str(local.get("paper_id") or remote.get("paper_id"))
    added = [str(item.get("added", "")) for item in (local, remote) if str(item.get("added", ""))]
    seen = [str(item.get("last_seen", "")) for item in (local, remote) if str(item.get("last_seen", ""))]
    if added:
        merged["added"] = min(added)
    if seen:
        merged["last_seen"] = max(seen)

    local_abstract = str(local.get("abstract", "") or "")
    remote_abstract = str(remote.get("abstract", "") or "")
    local_complete = str(local.get("abstract_evidence", "")) == "complete"
    remote_complete = str(remote.get("abstract_evidence", "")) == "complete"
    abstract_source = local if local_complete and not remote_complete else remote if remote_complete and not local_complete else (
        local if len(local_abstract) >= len(remote_abstract) else remote
    )
    for key in ("abstract", "abstract_evidence", "abstract_word_count", "abstract_source", "abstract_fetched_at"):
        if key in abstract_source:
            merged[key] = abstract_source[key]

    identifiers: dict[str, Any] = {}
    for item in (older.get("identifiers"), newest.get("identifiers")):
        if isinstance(item, dict):
            identifiers.update(item)
    if identifiers:
        merged["identifiers"] = identifiers

    provenance: list[Any] = []
    seen_provenance: set[str] = set()
    for item in [*(local.get("provenance") or []), *(remote.get("provenance") or [])]:
        marker = json.dumps(item, ensure_ascii=False, sort_keys=True)
        if marker not in seen_provenance:
            provenance.append(item)
            seen_provenance.add(marker)
    if provenance:
        merged["provenance"] = provenance

    user, other_user, timestamped = _user_source(local, remote)
    for field in USER_FIELDS:
        if field in user:
            merged[field] = user[field]
        elif field in other_user:
            merged[field] = other_user[field]
    if not timestamped:
        merged["pinned"] = bool(local.get("pinned")) or bool(remote.get("pinned"))
        timestamps = [str(item.get("user_updated_at", "")) for item in (local, remote) if str(item.get("user_updated_at", ""))]
        if timestamps:
            merged["user_updated_at"] = max(timestamps)
    return merged


def merge_queue_records(local: Iterable[dict[str, Any]], remote: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    alias_index: dict[str, str] = {}

    def insert(record: dict[str, Any]) -> None:
        paper_id = str(record.get("paper_id", "")).strip()
        match = next((alias_index[alias] for alias in _aliases(record) if alias in alias_index), "")
        key = match or paper_id
        records[key] = merge_queue_record(records[key], record) if key in records else dict(record)
        for alias in _aliases(records[key]):
            alias_index[alias] = key

    for record in local:
        insert(record)
    for record in remote:
        insert(record)
    return sorted(records.values(), key=lambda item: (str(item.get("added", "")), str(item.get("paper_id", ""))))


def serialize_queue(records: Iterable[dict[str, Any]]) -> str:
    return "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records)


def _markdown_safe(value: Any) -> str:
    return str(value or "").replace("|", "/").replace("\n", " ").strip()


def render_reading_queue(records: Iterable[dict[str, Any]]) -> str:
    active = [record for record in records if str(record.get("status", "")) in ACTIVE_QUEUE_STATUSES]
    active.sort(
        key=lambda item: (
            int(item.get("tier", 2) or 2),
            str(item.get("added", "")),
            str(item.get("candidate_slug", "")),
        )
    )
    header = (
        "# Reading Queue\n\n"
        "Derived compatibility view. Canonical state: `queue_state.jsonl`.\n\n"
        "Capacity-limited view: Tier 1 has at most 3 active papers and Tier 2 "
        "has at most 5 by default. Tier 3 remains searchable outside the active queue.\n\n"
        "| candidate-slug | title | tier | lane | score | status | action | authors | venue | url | added | expires |\n"
        "|----------------|-------|------|------|-------|--------|--------|---------|-------|-----|-------|---------|\n"
    )
    rows = []
    for record in active:
        try:
            score = f"{float(record.get('score', 0) or 0):.1f}"
        except (TypeError, ValueError):
            score = "0.0"
        values = (
            record.get("candidate_slug"), record.get("title"), record.get("tier", 2),
            record.get("lane"), score, record.get("status"), record.get("triage_action"),
            record.get("authors"), record.get("venue"), record.get("url"),
            record.get("added"), record.get("expires_at"),
        )
        rows.append("| " + " | ".join(_markdown_safe(value) for value in values) + " |")
    return header + "\n".join(rows) + ("\n" if rows else "")


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def merge_queue_text(local_text: str, remote_text: str) -> tuple[str, str, int]:
    records = merge_queue_records(
        parse_queue_jsonl(local_text, source="local queue"),
        parse_queue_jsonl(remote_text, source="remote queue"),
    )
    return serialize_queue(records), render_reading_queue(records), len(records)


def refresh_queue_view(root: Path) -> int:
    state = root / "queue_state.jsonl"
    if not state.exists():
        return 0
    records = parse_queue_jsonl(state.read_text(encoding="utf-8-sig"), source=str(state))
    atomic_write_text(root / "reading_queue.md", render_reading_queue(records))
    return len(records)
