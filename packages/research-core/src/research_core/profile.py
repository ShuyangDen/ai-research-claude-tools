"""Projection helpers that keep profile-signal provenance lanes apart."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Iterable

from .util import SCHEMA_VERSION, stable_hash, utc_now


_PRIORITY_WEIGHT = {"low": 0.5, "medium": 0.75, "high": 1.0}
_SIGNAL_TYPES = ("declared", "portfolio", "inferred", "speculative", "negative")


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _signal_score(signal: dict[str, Any], now: datetime, half_life_days: float) -> float:
    confidence = float(signal.get("confidence", 1.0))
    priority = _PRIORITY_WEIGHT.get(str(signal.get("priority", "medium")), 0.75)
    signal_type = signal["signal_type"]
    if signal_type in {"declared", "portfolio"}:
        return priority * confidence if signal.get("human_approved") else 0.0
    observed = _parse_time(signal.get("observed_at")) or now
    age_days = max(0.0, (now - observed).total_seconds() / 86400.0)
    decay = math.pow(0.5, age_days / half_life_days)
    if signal_type == "inferred":
        return priority * confidence * decay
    if signal_type == "speculative":
        return min(0.25, priority * confidence * decay * 0.35)
    if signal_type == "negative":
        return -priority * confidence * decay
    raise ValueError(f"Unknown signal_type: {signal_type}")


def project_profile(
    signals: Iterable[dict[str, Any]],
    *,
    now: datetime | None = None,
    half_life_days: float = 90.0,
) -> dict[str, Any]:
    if half_life_days <= 0:
        raise ValueError("half_life_days must be positive")
    now = now or datetime.now(timezone.utc)
    latest: dict[str, dict[str, Any]] = {}
    for raw in signals:
        signal = dict(raw)
        # Accept the short-lived pre-1.0 field names without emitting them as
        # the canonical interface. This makes existing private projections
        # migratable instead of silently dropping them.
        if "signal_type" not in signal and "class" in signal:
            signal["signal_type"] = signal.pop("class")
        if "title" not in signal and "label" in signal:
            signal["title"] = signal.pop("label")
        if "observed_at" not in signal and "created_at" in signal:
            signal["observed_at"] = signal["created_at"]
        if "updated_at" not in signal and "created_at" in signal:
            signal["updated_at"] = signal["created_at"]
        signal.pop("created_at", None)
        if "confidence" not in signal and "weight" in signal:
            signal["confidence"] = max(0.0, min(1.0, abs(float(signal["weight"]))))
        signal.pop("weight", None)
        if "expires_at" not in signal and "expires_or_review_at" in signal:
            signal["expires_at"] = signal["expires_or_review_at"]
        signal.pop("expires_or_review_at", None)
        signal_id = str(signal.get("signal_id", ""))
        if not signal_id:
            raise ValueError("Each profile signal needs signal_id")
        if signal.get("signal_type") not in _SIGNAL_TYPES:
            raise ValueError(f"Unknown signal_type: {signal.get('signal_type')}")
        signal.setdefault("schema_version", SCHEMA_VERSION)
        signal.setdefault("status", "active")
        signal.setdefault("title", signal_id)
        signal.setdefault("mechanism", "")
        signal.setdefault("retrieval_terms", [])
        signal.setdefault("source_refs", [])
        signal.setdefault("human_approved", False)
        signal.setdefault("confidence", 1.0)
        signal.setdefault("priority", "medium")
        signal.setdefault("observed_at", utc_now())
        signal.setdefault("updated_at", signal["observed_at"])
        previous = latest.get(signal_id)
        if previous is None or str(signal.get("updated_at", "")) >= str(previous.get("updated_at", "")):
            latest[signal_id] = signal

    lanes: dict[str, list[dict[str, Any]]] = {
        "declared": [],
        "portfolio": [],
        "inferred": [],
        "speculative": [],
        "negative": [],
    }
    for signal in latest.values():
        if signal.get("status", "active") != "active":
            continue
        expires = _parse_time(signal.get("expires_at"))
        if expires is not None and expires < now:
            continue
        projected = dict(signal)
        projected["projection_score"] = round(_signal_score(signal, now, half_life_days), 6)
        projected["tier_1_eligible"] = bool(
            signal["signal_type"] in {"declared", "portfolio"}
            and signal.get("human_approved")
            and projected["projection_score"] > 0
        )
        lanes[signal["signal_type"]].append(projected)

    for values in lanes.values():
        values.sort(key=lambda item: (-abs(item["projection_score"]), item["signal_id"]))

    projection = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "half_life_days": half_life_days,
        "recommendation_lane_weights": {
            "exploit": 0.55,
            "adjacent": 0.20,
            "contradiction": 0.15,
            "methodology": 0.10,
        },
        "lanes": lanes,
        "tier_1_signal_ids": [
            item["signal_id"]
            for lane in ("declared", "portfolio")
            for item in lanes[lane]
            if item["tier_1_eligible"]
        ],
    }
    projection["projection_hash"] = stable_hash(
        {key: value for key, value in projection.items() if key != "generated_at"}
    )
    return projection


def new_profile_signal(
    *,
    signal_id: str,
    signal_type: str,
    title: str,
    mechanism: str,
    source_refs: list[dict[str, Any]],
    human_approved: bool = False,
    confidence: float = 1.0,
    priority: str = "medium",
) -> dict[str, Any]:
    if signal_type not in _SIGNAL_TYPES:
        raise ValueError(f"Unknown signal_type: {signal_type}")
    now = utc_now()
    return {
        "schema_version": SCHEMA_VERSION,
        "signal_id": signal_id,
        "signal_type": signal_type,
        "status": "active",
        "title": title,
        "mechanism": mechanism,
        "source_refs": source_refs,
        "human_approved": human_approved,
        "confidence": confidence,
        "priority": priority,
        "observed_at": now,
        "updated_at": now,
    }
