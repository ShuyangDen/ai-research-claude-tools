"""Durable, provenance-aware memory for observable research decisions.

The memory layer stores compact rationales and decision labels.  It deliberately
does not store hidden chain-of-thought or promote assistant inferences into the
researcher's profile.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from .contracts import assert_contract
from .util import atomic_write_bytes, file_lock, stable_hash, utc_now


REASONING_LOG = Path("ideas") / "memory" / "reasoning-events.jsonl"
IDEA_FEEDBACK_LOG = Path("ideas") / "memory" / "idea-feedback.jsonl"


def _semantic_id(prefix: str, value: dict[str, Any], *, excluded: Iterable[str]) -> str:
    material = {key: item for key, item in value.items() if key not in set(excluded)}
    return f"{prefix}:{stable_hash(material, length=20)}"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: JSONL row must be an object")
        rows.append(value)
    return rows


def _append_unique(
    path: Path,
    event: dict[str, Any],
    *,
    id_field: str,
    ignored_fields: Iterable[str] = ("recorded_at",),
) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(path):
        rows = _read_jsonl(path)
        ignored = set(ignored_fields)
        for row in rows:
            if row.get(id_field) != event[id_field]:
                continue
            existing = {key: value for key, value in row.items() if key not in ignored}
            candidate = {key: value for key, value in event.items() if key not in ignored}
            if existing != candidate:
                raise ValueError(f"Conflicting event for {event[id_field]}")
            return False
        payload = b"".join(
            (json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
            for row in [*rows, event]
        )
        atomic_write_bytes(path, payload)
    return True


def reasoning_log_path(idea_vault: str | Path) -> Path:
    return Path(idea_vault) / REASONING_LOG


def idea_feedback_log_path(idea_vault: str | Path) -> Path:
    return Path(idea_vault) / IDEA_FEEDBACK_LOG


def record_reasoning(idea_vault: str | Path, value: dict[str, Any]) -> dict[str, Any]:
    event = dict(value)
    occurrence_was_supplied = "occurred_at" in event
    event.setdefault("schema_version", "1.0")
    event.setdefault("recorded_at", utc_now())
    event.setdefault("occurred_at", event["recorded_at"])
    event.setdefault("alternatives_rejected", [])
    event.setdefault("decision", "")
    event.setdefault("transfer_rule", "")
    event.setdefault("intellectual_origin", "not_applicable")
    event.setdefault("source_pattern", "")
    event.setdefault("endorsement_rationale", "")
    event.setdefault("transferable_element", "")
    event.setdefault("transfer_boundary", "")
    event.setdefault("confidence", None)
    event.setdefault("source_refs", [])
    event.setdefault("provenance", {})
    if "reasoning_id" not in event:
        excluded = ["reasoning_id", "recorded_at"]
        # An omitted occurrence timestamp is a volatile recording default, not
        # semantic input. Excluding it keeps retries idempotent. Callers that
        # need two otherwise-identical events should supply occurred_at or an ID.
        if not occurrence_was_supplied:
            excluded.append("occurred_at")
        event["reasoning_id"] = _semantic_id("reasoning", event, excluded=excluded)
    if event.get("profile_eligible") and not (
        event.get("actor") == "human"
        and event.get("actor_basis") == "direct"
        and event.get("human_confirmed") is True
    ):
        raise ValueError(
            "profile_eligible reasoning must be direct, human, and human-confirmed"
        )
    if event.get("intellectual_origin") in {
        "external_exemplar",
        "hybrid_synthesis",
    }:
        required_attribution = (
            "source_pattern",
            "endorsement_rationale",
            "transferable_element",
            "transfer_boundary",
        )
        missing = [field for field in required_attribution if not event.get(field)]
        if not event.get("source_refs"):
            missing.append("source_refs")
        if missing:
            raise ValueError(
                "external exemplar needs attributed fields: " + ", ".join(missing)
            )
    assert_contract("reasoning-event", event)
    ignored = (
        ("recorded_at",)
        if occurrence_was_supplied
        else ("recorded_at", "occurred_at")
    )
    added = _append_unique(
        reasoning_log_path(idea_vault),
        event,
        id_field="reasoning_id",
        ignored_fields=ignored,
    )
    return {**event, "added": added}


def record_idea_feedback(idea_vault: str | Path, value: dict[str, Any]) -> dict[str, Any]:
    event = dict(value)
    event.setdefault("schema_version", "1.0")
    event.setdefault("recorded_at", utc_now())
    event.setdefault("idea_slug", None)
    event.setdefault("origin_run_id", None)
    event.setdefault("rationale", "")
    event.setdefault("reason_codes", [])
    event.setdefault("revival_conditions", [])
    event.setdefault("confidence", None)
    event.setdefault("source_refs", [])
    event.setdefault("provenance", {})
    event.setdefault(
        "feedback_id",
        _semantic_id(
            "idea-feedback",
            event,
            excluded=("feedback_id", "recorded_at"),
        ),
    )
    if event.get("profile_use") == "taste" and not (
        event.get("rater") == "researcher"
        and event.get("rater_basis") == "direct"
        and event.get("human_confirmed") is True
    ):
        raise ValueError("taste feedback must be direct and researcher-confirmed")
    if event.get("rater") == "advisor" and event.get("profile_use") == "taste":
        raise ValueError("advisor outcomes cannot overwrite researcher taste")
    assert_contract("idea-feedback", event)
    added = _append_unique(
        idea_feedback_log_path(idea_vault), event, id_field="feedback_id"
    )
    return {**event, "added": added}


def memory_summary(
    idea_vault: str | Path,
    *,
    limit: int = 50,
) -> dict[str, Any]:
    if limit < 1 or limit > 500:
        raise ValueError("limit must be between 1 and 500")
    reasoning = _read_jsonl(reasoning_log_path(idea_vault))
    feedback = _read_jsonl(idea_feedback_log_path(idea_vault))
    durable = [
        item
        for item in reasoning
        if item.get("profile_eligible")
        and item.get("durability") in {"repeated_pattern", "declared_constraint"}
    ]
    advisor = [item for item in feedback if item.get("rater") == "advisor"]
    feasibility = [
        item for item in feedback if item.get("profile_use") == "feasibility_only"
    ]
    external_exemplars = [
        item
        for item in reasoning
        if item.get("human_confirmed")
        and item.get("actor") == "human"
        and item.get("actor_basis") == "direct"
        and item.get("intellectual_origin")
        in {"external_exemplar", "hybrid_synthesis"}
    ]
    return {
        "schema_version": "1.0",
        "generated_at": utc_now(),
        "counts": {
            "reasoning_events": len(reasoning),
            "idea_feedback_events": len(feedback),
            "durable_reasoning_patterns": len(durable),
            "endorsed_external_exemplars": len(external_exemplars),
            "advisor_outcomes": len(advisor),
            "feasibility_outcomes": len(feasibility),
        },
        "idea_decisions": dict(Counter(str(item.get("decision")) for item in feedback)),
        "durable_reasoning": durable[-limit:],
        "endorsed_external_exemplars": external_exemplars[-limit:],
        "advisor_outcomes": advisor[-limit:],
        "feasibility_outcomes": feasibility[-limit:],
        "recent_reasoning": reasoning[-limit:],
        "recent_idea_feedback": feedback[-limit:],
    }
