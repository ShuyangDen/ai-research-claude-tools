"""Deterministic inventory diffing and token plans for economics frontier reviews.

The LLM workflow retrieves and interprets public research evidence.  This module
owns stable identities, change detection, and bounded worker packets. It performs
no network or model calls; validation, state transitions, and rendering live in
focused sibling modules.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import json
import math
import re
from collections import defaultdict
from typing import Any, Mapping, Sequence

from frontier_tokens import estimate_tokens
from scout_core import (
    ScoutPaper,
    deduplicate_papers,
    journal_rank_tier,
    journal_rank_weight,
    source_quality_tier,
    stable_json_hash,
    validate_public_query,
)


SCHEMA_VERSION = "2.0"
DEFAULT_SCOPE = ("labor", "education")
DEFAULT_WINDOW_MONTHS = 12
EVIDENCE_LEVELS = {"title_only", "metadata", "abstract", "targeted_full_text"}
ALLOWED_SCOPES = set(DEFAULT_SCOPE)
ROUTING_CONFIDENCE = {"low", "medium", "high"}
WINDOWS_RESERVED_NAMES = {
    "con", "prn", "aux", "nul",
    *(f"com{index}" for index in range(1, 10)),
    *(f"lpt{index}" for index in range(1, 10)),
}

TOKEN_MODES: dict[str, dict[str, int]] = {
    "lite": {
        "inventory_papers": 25,
        "max_clusters": 4,
        "router_batch_tokens": 6000,
        "worker_packet_tokens": 8500,
        "worker_packet_papers": 6,
        "targeted_full_text_per_cluster": 1,
        "partial_output_tokens_per_cluster": 1500,
        "orchestration_token_reserve": 2000,
        "run_input_token_ceiling": 30000,
    },
    "standard": {
        "inventory_papers": 50,
        "max_clusters": 6,
        "router_batch_tokens": 9000,
        "worker_packet_tokens": 12000,
        "worker_packet_papers": 8,
        "targeted_full_text_per_cluster": 2,
        "partial_output_tokens_per_cluster": 2500,
        "orchestration_token_reserve": 4000,
        "run_input_token_ceiling": 65000,
    },
    "deep": {
        "inventory_papers": 80,
        "max_clusters": 8,
        "router_batch_tokens": 12000,
        "worker_packet_tokens": 16000,
        "worker_packet_papers": 10,
        "targeted_full_text_per_cluster": 3,
        "partial_output_tokens_per_cluster": 4000,
        "orchestration_token_reserve": 8000,
        "run_input_token_ceiling": 125000,
    },
}


def _iso_datetime(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"Frontier review needs {field}")
    try:
        dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Frontier review {field} must be ISO-8601") from exc
    return text


def _slug(value: Any, field: str) -> str:
    text = str(value or "").strip().casefold()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", text):
        raise ValueError(f"Frontier {field} must be a lowercase hyphenated slug")
    if text in WINDOWS_RESERVED_NAMES:
        raise ValueError(f"Frontier {field} is a reserved Windows filename")
    return text


def _nonempty(value: Any, field: str) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        raise ValueError(f"Frontier {field} cannot be empty")
    return text


def _paper_fingerprint(paper: ScoutPaper) -> str:
    return stable_json_hash({
        "title": paper.title,
        "authors": paper.authors,
        "published": paper.published,
        "venue": paper.venue,
        "source_family": paper.source_family,
        "url": paper.url,
        "abstract": paper.abstract,
        "evidence_level": paper.evidence_level,
        "identifiers": paper.identifiers,
        "suspected_version_of": paper.suspected_version_of,
    })


def _paper_row(paper: ScoutPaper) -> dict[str, Any]:
    row = dataclasses.asdict(paper)
    row.update({
        "fingerprint": _paper_fingerprint(paper),
        "abstract_hash": hashlib.sha256(paper.abstract.encode("utf-8")).hexdigest(),
        "source_quality_tier": source_quality_tier(paper),
        "journal_rank_weight": round(journal_rank_weight(paper), 4),
        "journal_rank_tier": journal_rank_tier(paper),
        "estimated_abstract_tokens": estimate_tokens(paper.abstract),
    })
    return row


def _paper_priority(paper: ScoutPaper) -> tuple[Any, ...]:
    evidence = {"title_only": 0, "metadata": 1, "abstract": 2, "targeted_full_text": 3}
    return (
        evidence[paper.evidence_level],
        journal_rank_weight(paper),
        paper.published,
        paper.paper_id,
    )


def _published_interval(value: str) -> tuple[dt.date, dt.date, bool] | None:
    compact = str(value or "").strip()
    if not compact:
        return None
    try:
        if re.fullmatch(r"\d{4}", compact):
            year = int(compact)
            return dt.date(year, 1, 1), dt.date(year, 12, 31), True
        if re.fullmatch(r"\d{4}-\d{2}", compact):
            start = dt.date.fromisoformat(f"{compact}-01")
            next_month = dt.date(
                start.year + (start.month == 12),
                start.month % 12 + 1,
                1,
            )
            return start, next_month - dt.timedelta(days=1), True
        exact = dt.date.fromisoformat(compact[:10])
        return exact, exact, False
    except ValueError:
        return None


def _subtract_months(value: dt.date, months: int) -> dt.date:
    absolute = value.year * 12 + value.month - 1 - months
    year, zero_based_month = divmod(absolute, 12)
    month = zero_based_month + 1
    next_month = dt.date(year + (month == 12), month % 12 + 1, 1)
    day = min(value.day, (next_month - dt.timedelta(days=1)).day)
    return dt.date(year, month, day)


def _validate_previous_state(previous: Mapping[str, Any] | None) -> dict[str, Any]:
    if not previous:
        return {}
    state = dict(previous)
    if state.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported frontier state schema: {state.get('schema_version')!r}"
        )
    if not isinstance(state.get("papers", {}), Mapping):
        raise ValueError("Frontier state papers must be an object")
    if not isinstance(state.get("clusters", {}), Mapping):
        raise ValueError("Frontier state clusters must be an object")
    claimed_hash = str(state.get("state_hash", ""))
    if not claimed_hash:
        raise ValueError("Frontier state is missing state_hash")
    hash_input = {key: value for key, value in state.items() if key != "state_hash"}
    if stable_json_hash(hash_input) != claimed_hash:
        raise ValueError("Frontier state_hash does not match state content")
    return state


def _reconciliation_due(previous: Mapping[str, Any], created_at: str) -> bool:
    last = str(
        previous.get("last_reconciled_at")
        or previous.get("created_at")
        or ""
    )[:10]
    if not last:
        return False
    try:
        return (
            dt.date.fromisoformat(created_at[:10]) - dt.date.fromisoformat(last)
        ).days >= 90
    except ValueError:
        return False


def _stable_sample(values: Sequence[str], count: int, seed: str) -> list[str]:
    return sorted(
        values,
        key=lambda value: hashlib.sha256(f"{seed}:{value}".encode("utf-8")).hexdigest(),
    )[:count]


def _router_card(
    row: Mapping[str, Any], previous_row: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    card = {
        key: row.get(key)
        for key in (
            "paper_id",
            "title",
            "authors",
            "published",
            "venue",
            "source_family",
            "url",
            "abstract",
            "evidence_level",
            "source_quality_tier",
            "journal_rank_tier",
            "suspected_version_of",
            "fingerprint",
        )
    }
    previous = previous_row or {}
    card["previous_primary_cluster_id"] = previous.get("primary_cluster_id")
    card["previous_secondary_cluster_ids"] = list(
        previous.get("secondary_cluster_ids", []) or []
    )
    return card


def _chunk_cards(
    cards: Sequence[Mapping[str, Any]], *, token_cap: int, paper_cap: int | None = None
) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []
    current_tokens = 0
    for raw in cards:
        card = dict(raw)
        tokens = estimate_tokens(json.dumps(card, ensure_ascii=False, sort_keys=True))
        if tokens > token_cap:
            raise ValueError(
                f"One frontier paper card exceeds the packet token cap: {card.get('paper_id')}"
            )
        full = bool(current) and (
            current_tokens + tokens > token_cap
            or (paper_cap is not None and len(current) >= paper_cap)
        )
        if full:
            packets.append({"papers": current, "estimated_tokens": current_tokens})
            current = []
            current_tokens = 0
        current.append(card)
        current_tokens += tokens
    if current:
        packets.append({"papers": current, "estimated_tokens": current_tokens})
    return packets


def _validate_assignments(
    raw: Any, eligible_ids: set[str], *, max_clusters: int
) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("Frontier assignments must be a list")
    assignments: list[dict[str, Any]] = []
    primary_for: set[str] = set()
    cluster_ids: set[str] = set()
    for item in raw:
        if not isinstance(item, Mapping):
            raise ValueError("Each frontier assignment must be an object")
        paper_id = str(item.get("paper_id", ""))
        if paper_id not in eligible_ids:
            raise ValueError(f"Frontier assignment references an ineligible paper: {paper_id}")
        cluster_id = _slug(item.get("primary_cluster_id"), "primary_cluster_id")
        if paper_id in primary_for:
            raise ValueError(f"Frontier paper has more than one primary cluster: {paper_id}")
        primary_for.add(paper_id)
        secondary = [
            _slug(value, "secondary_cluster_id")
            for value in item.get("secondary_cluster_ids", [])
        ]
        if cluster_id in secondary:
            raise ValueError("A primary frontier cluster cannot also be secondary")
        cluster_ids.update((cluster_id, *secondary))
        confidence = str(item.get("routing_confidence", "medium"))
        if confidence not in ROUTING_CONFIDENCE:
            raise ValueError(f"Unsupported frontier routing confidence: {confidence}")
        assignments.append({
            "paper_id": paper_id,
            "primary_cluster_id": cluster_id,
            "secondary_cluster_ids": list(dict.fromkeys(secondary)),
            "routing_confidence": confidence,
            "routing_note": _nonempty(item.get("routing_note"), "routing_note"),
        })
    if len(cluster_ids) > max_clusters:
        raise ValueError(
            f"Frontier routing produced {len(cluster_ids)} primary clusters; cap is {max_clusters}"
        )
    return assignments


def build_update_plan(
    payload: Mapping[str, Any], previous_state: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Compare one retrieval inventory with durable state and build bounded packets."""

    previous = _validate_previous_state(previous_state)
    run_id = str(payload.get("run_id", ""))
    if not re.fullmatch(r"frontier-[A-Za-z0-9][A-Za-z0-9._-]*", run_id):
        raise ValueError("Frontier run_id must start with 'frontier-'")
    created_at = _iso_datetime(payload.get("created_at"), "created_at")
    mode = str(payload.get("token_mode", "standard")).casefold()
    if mode not in TOKEN_MODES:
        raise ValueError(f"Unsupported frontier token_mode: {mode}")
    budget = dict(TOKEN_MODES[mode])
    queries = [validate_public_query(item) for item in payload.get("queries", [])]
    if not queries:
        raise ValueError("Frontier review needs at least one recorded public query")
    scope = list(dict.fromkeys(str(item).casefold() for item in payload.get("scope", DEFAULT_SCOPE)))
    if not scope or set(scope) - ALLOWED_SCOPES:
        raise ValueError("Frontier scope must contain only labor and/or education")
    window_months = int(payload.get("window_months", DEFAULT_WINDOW_MONTHS))
    if not 1 <= window_months <= 60:
        raise ValueError("Frontier window_months must be between 1 and 60")
    as_of = dt.date.fromisoformat(created_at[:10])
    window_start = _subtract_months(as_of, window_months)
    if previous:
        previous_updated = dt.datetime.fromisoformat(
            str(previous.get("updated_at", "")).replace("Z", "+00:00")
        )
        current_created = dt.datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        if previous_updated.tzinfo is None:
            previous_updated = previous_updated.replace(tzinfo=dt.timezone.utc)
        if current_created.tzinfo is None:
            current_created = current_created.replace(tzinfo=dt.timezone.utc)
        if current_created <= previous_updated:
            raise ValueError("Frontier created_at must be later than the current state")
        if set(previous.get("scope", [])) != set(scope):
            raise ValueError("Frontier scope cannot change within an existing state root")
        scope = list(previous.get("scope", []))
        if int(previous.get("window_months", window_months)) != window_months:
            raise ValueError("Frontier window_months cannot change within an existing state root")

    all_papers = deduplicate_papers(payload.get("papers", []))
    in_window: list[ScoutPaper] = []
    out_of_window_ids: list[str] = []
    undated_ids: list[str] = []
    date_uncertain_ids: list[str] = []
    for paper in all_papers:
        published = _published_interval(paper.published)
        if published is None:
            undated_ids.append(paper.paper_id)
        else:
            if published[2]:
                date_uncertain_ids.append(paper.paper_id)
            if published[1] >= window_start and published[0] <= as_of:
                in_window.append(paper)
            else:
                out_of_window_ids.append(paper.paper_id)
    prioritized = sorted(in_window, key=_paper_priority, reverse=True)
    selected = prioritized[: budget["inventory_papers"]]
    deferred = prioritized[budget["inventory_papers"] :]
    rows = {_paper.paper_id: _paper_row(_paper) for _paper in selected}
    previous_papers = dict(previous.get("papers", {}))
    expired_previous_ids = sorted(
        paper_id
        for paper_id, row in previous_papers.items()
        if isinstance(row, Mapping)
        and row.get("frontier_status", "active") == "active"
        and (
            (published := _published_interval(str(row.get("published", "")))) is not None
            and not (published[1] >= window_start and published[0] <= as_of)
        )
    )
    new_ids: list[str] = []
    changed_ids: list[str] = []
    unchanged_ids: list[str] = []
    metadata_only_ids: list[str] = []
    evidence_downgraded_ids: list[str] = []
    for paper in selected:
        if paper.evidence_level not in EVIDENCE_LEVELS:
            raise ValueError(f"Unsupported frontier evidence level: {paper.evidence_level}")
        if paper.evidence_level in {"title_only", "metadata"} or not paper.abstract:
            metadata_only_ids.append(paper.paper_id)
            old = previous_papers.get(paper.paper_id)
            if (
                isinstance(old, Mapping)
                and old.get("evidence_level") in {"abstract", "targeted_full_text"}
                and old.get("abstract")
            ):
                evidence_downgraded_ids.append(paper.paper_id)
            continue
        old = previous_papers.get(paper.paper_id)
        if not isinstance(old, Mapping):
            new_ids.append(paper.paper_id)
        elif old.get("fingerprint") != rows[paper.paper_id]["fingerprint"]:
            changed_ids.append(paper.paper_id)
        else:
            unchanged_ids.append(paper.paper_id)

    due = bool(payload.get("force_reconcile", False)) or _reconciliation_due(previous, created_at)
    rate = float(payload.get("reconcile_sample_rate", 0.10))
    if not 0 <= rate <= 0.25:
        raise ValueError("Frontier reconcile_sample_rate must be between 0 and 0.25")
    sample_count = max(1, math.ceil(len(unchanged_ids) * rate)) if due and unchanged_ids else 0
    sampled_ids = _stable_sample(unchanged_ids, sample_count, run_id)
    routed_ids = [*new_ids, *changed_ids, *sampled_ids]
    router_cards = [
        _router_card(rows[paper_id], previous_papers.get(paper_id))
        for paper_id in routed_ids
    ]
    router_batches = _chunk_cards(
        router_cards, token_cap=budget["router_batch_tokens"]
    )
    for index, packet in enumerate(router_batches, start=1):
        packet["batch_id"] = f"router-{index:02d}"

    eligible_ids = {
        paper_id for paper_id, row in rows.items()
        if row["evidence_level"] in {"abstract", "targeted_full_text"} and row["abstract"]
    }
    assignments = _validate_assignments(
        payload.get("assignments"), eligible_ids, max_clusters=budget["max_clusters"]
    )
    assigned_by_cluster: dict[str, list[str]] = defaultdict(list)
    for item in assignments:
        for cluster_id in (
            item["primary_cluster_id"],
            *item["secondary_cluster_ids"],
        ):
            assigned_by_cluster[cluster_id].append(item["paper_id"])
    previous_clusters = dict(previous.get("clusters", {}))
    maintenance_by_cluster: dict[str, list[str]] = defaultdict(list)
    for item in assignments:
        old = previous_papers.get(item["paper_id"], {})
        if not isinstance(old, Mapping):
            continue
        old_memberships = {
            value
            for value in (
                old.get("primary_cluster_id"),
                *(old.get("secondary_cluster_ids", []) or []),
            )
            if value
        }
        new_memberships = {
            item["primary_cluster_id"],
            *item["secondary_cluster_ids"],
        }
        for cluster_id in old_memberships - new_memberships:
            maintenance_by_cluster[str(cluster_id)].append(item["paper_id"])
    for paper_id in expired_previous_ids:
        old = previous_papers.get(paper_id, {})
        for cluster_id in (
            old.get("primary_cluster_id") if isinstance(old, Mapping) else None,
            *((old.get("secondary_cluster_ids", []) or []) if isinstance(old, Mapping) else []),
        ):
            if cluster_id:
                maintenance_by_cluster[str(cluster_id)].append(paper_id)
    worker_packets: list[dict[str, Any]] = []
    reducer_packets: list[dict[str, Any]] = []
    all_worker_clusters = set(assigned_by_cluster) | set(maintenance_by_cluster)
    for cluster_id in sorted(all_worker_clusters):
        cluster_paper_ids = assigned_by_cluster[cluster_id]
        delta_ids = list(dict.fromkeys([
            *(
                paper_id for paper_id in cluster_paper_ids
                if paper_id in routed_ids
            ),
            *maintenance_by_cluster.get(cluster_id, []),
        ]))
        if not delta_ids:
            continue
        old_cluster = previous_clusters.get(cluster_id, {})
        compact_previous = None
        if isinstance(old_cluster, Mapping):
            compact_previous = {
                key: old_cluster.get(key)
                for key in (
                    "title",
                    "research_question",
                    "current_consensus",
                    "disagreements",
                    "progress",
                    "open_questions",
                    "confidence",
                    "synthesis_hash",
                    "paper_ids",
                    "aliases",
                    "status",
                )
                if old_cluster.get(key) not in (None, "", [])
            } or None
        previous_tokens = estimate_tokens(
            json.dumps(compact_previous or {}, ensure_ascii=False, sort_keys=True)
        )
        card_token_cap = budget["worker_packet_tokens"] - previous_tokens
        if card_token_cap <= 0:
            raise ValueError(
                f"Frontier previous cluster card exceeds the worker packet cap: {cluster_id}"
            )
        cards = [
            _router_card(
                rows[paper_id] if paper_id in rows else previous_papers[paper_id],
                previous_papers.get(paper_id),
            )
            for paper_id in delta_ids
        ]
        packets = _chunk_cards(
            cards,
            token_cap=card_token_cap,
            paper_cap=budget["worker_packet_papers"],
        )
        packet_count = len(packets)
        full_text_cap = budget["targeted_full_text_per_cluster"]
        base_quota, extra_quota = divmod(full_text_cap, packet_count)
        partial_base, partial_extra = divmod(
            budget["partial_output_tokens_per_cluster"], packet_count
        )
        packet_ids: list[str] = []
        partial_output_caps: list[int] = []
        for index, packet in enumerate(packets, start=1):
            packet_id = f"cluster-{cluster_id}-{index:02d}"
            packet_ids.append(packet_id)
            partial_output_cap = partial_base + (index <= partial_extra)
            partial_output_caps.append(partial_output_cap)
            worker_packets.append({
                "packet_id": packet_id,
                "cluster_id": cluster_id,
                "papers": packet["papers"],
                "previous_cluster_card": compact_previous,
                "estimated_tokens": packet["estimated_tokens"] + previous_tokens,
                "targeted_full_text_cap": base_quota + (index <= extra_quota),
                "output_contract": (
                    "partial_analysis" if packet_count > 1 else "final_cluster_synthesis"
                ),
                "output_token_cap": (
                    partial_output_cap
                    if packet_count > 1
                    else budget["worker_packet_tokens"]
                ),
                "maintenance_reason": (
                    "membership_change"
                    if cluster_id in maintenance_by_cluster
                    else None
                ),
            })
        if packet_count > 1:
            reducer_packets.append({
                "packet_id": f"reducer-{cluster_id}",
                "cluster_id": cluster_id,
                "input_packet_ids": packet_ids,
                "estimated_tokens": sum(partial_output_caps),
                "targeted_full_text_cap": 0,
                "output_contract": "final_cluster_synthesis",
                "output_token_cap": budget["worker_packet_tokens"],
            })

    estimated_input = budget["orchestration_token_reserve"] + sum(
        item["estimated_tokens"] for item in router_batches
    ) + sum(
        item["estimated_tokens"] for item in worker_packets
    ) + sum(item["estimated_tokens"] for item in reducer_packets)
    reserved_partial_output = sum(
        item["output_token_cap"]
        for item in worker_packets
        if item["output_contract"] == "partial_analysis"
    )
    estimated_plan_tokens = estimated_input + reserved_partial_output
    if estimated_plan_tokens > budget["run_input_token_ceiling"]:
        raise ValueError(
            f"Frontier packet plan reserves {estimated_plan_tokens} tokens; "
            f"{mode} ceiling is {budget['run_input_token_ceiling']}"
        )
    plan = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "created_at": created_at,
        "scope": scope,
        "window_months": window_months,
        "token_mode": mode,
        "budget": budget,
        "queries": queries,
        "source_health": dict(payload.get("source_health", {})),
        "inventory": {
            "retrieved_count": len(all_papers),
            "selected_count": len(selected),
            "out_of_window_ids": out_of_window_ids,
            "undated_ids": undated_ids,
            "date_uncertain_ids": date_uncertain_ids,
            "deferred_ids": [paper.paper_id for paper in deferred],
            "new_ids": new_ids,
            "changed_ids": changed_ids,
            "unchanged_ids": unchanged_ids,
            "reconcile_sample_ids": sampled_ids,
            "metadata_only_ids": metadata_only_ids,
            "evidence_downgraded_ids": evidence_downgraded_ids,
            "expired_previous_ids": expired_previous_ids,
        },
        "papers": list(rows.values()),
        "assignments": assignments,
        "router_batches": router_batches,
        "worker_packets": worker_packets,
        "reducer_packets": reducer_packets,
        "estimated_input_tokens": estimated_input,
        "reserved_partial_output_tokens": reserved_partial_output,
        "estimated_plan_tokens": estimated_plan_tokens,
        "reconciliation_due": due,
    }
    plan["plan_hash"] = stable_json_hash(plan)
    return plan
