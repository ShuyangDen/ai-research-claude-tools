"""Prepare and apply capacity-bounded paper-triage batches.

This module is deliberately content-agnostic.  An LLM workflow may enrich the
batch with abstracts and paper cards, but deterministic code owns candidate
selection, human decision validation, append-only taste events, and reversible
queue-state transitions.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


ACTIONS = ("deep", "targeted", "cluster-only", "skip", "backlog")
REASON_CODES = (
    "importance",
    "mechanism",
    "identification",
    "data",
    "measurement",
    "surprise",
    "feasibility",
    "contradiction",
    "duplicate",
    "low-fit",
    "time-cost",
)
ACTION_STATUS = {
    "deep": "in_progress",
    "targeted": "in_progress",
    "cluster-only": "clustered",
    "skip": "skipped",
    "backlog": "backlog",
}


@dataclasses.dataclass(frozen=True)
class TriageDecision:
    schema_version: str
    decision_id: str
    batch_id: str
    paper_id: str
    candidate_slug: str
    date: str
    recorded_at: str
    action: str
    reason_codes: list[str]
    rationale: str
    would_build_on: bool | None
    predicted_value: int | None
    selected_sections: list[str]
    cluster_id: str
    actor: str
    provenance: dict[str, Any]


@dataclasses.dataclass(frozen=True)
class TasteComparison:
    schema_version: str
    comparison_id: str
    batch_id: str
    recorded_at: str
    winner_paper_id: str
    loser_paper_id: str
    reason_codes: list[str]
    rationale: str
    actor: str
    provenance: dict[str, Any]


def _clean(value: object, limit: int = 800) -> str:
    return " ".join(str(value or "").replace("|", "/").split())[:limit]


def _unique(values: Iterable[object], *, allowed: set[str] | None = None) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = _clean(value, 120)
        if allowed is not None and cleaned not in allowed:
            raise ValueError(f"Unsupported value: {cleaned!r}")
        if cleaned and cleaned.casefold() not in seen:
            seen.add(cleaned.casefold())
            output.append(cleaned)
    return output


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    if not source.exists():
        return []
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        source.read_text(encoding="utf-8-sig").splitlines(), 1
    ):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at {source}:{line_number}: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"JSONL row at {source}:{line_number} must be an object")
        records.append(value)
    return records


def _queue_sort_key(record: Mapping[str, Any]) -> tuple[Any, ...]:
    rank = int(record.get("priority_rank", 0) or 0)
    return (
        int(record.get("tier", 2) or 2),
        rank if rank > 0 else 10**9,
        -float(record.get("score", 0.0) or 0.0),
        str(record.get("paper_id", "")),
    )


def select_candidates(
    records: Sequence[Mapping[str, Any]], *, max_papers: int = 10
) -> list[dict[str, Any]]:
    if not 1 <= max_papers <= 20:
        raise ValueError("max_papers must be between 1 and 20")
    active = [record for record in records if record.get("status") == "queued"]
    return [dict(record) for record in sorted(active, key=_queue_sort_key)[:max_papers]]


def prepare_batch(
    records: Sequence[Mapping[str, Any]],
    *,
    batch_id: str | None = None,
    max_papers: int = 10,
    created_at: str | None = None,
) -> dict[str, Any]:
    timestamp = created_at or dt.datetime.now(dt.timezone.utc).isoformat()
    identifier = batch_id or f"triage-{timestamp[:10].replace('-', '')}"
    candidates = select_candidates(records, max_papers=max_papers)
    return {
        "schema_version": "1.0",
        "batch_id": _clean(identifier, 120),
        "created_at": timestamp,
        "status": "awaiting_human_decisions",
        "candidate_count": len(candidates),
        "candidates": [
            {
                key: record.get(key)
                for key in (
                    "paper_id",
                    "candidate_slug",
                    "title",
                    "authors",
                    "venue",
                    "published",
                    "url",
                    "tier",
                    "lane",
                    "matched_signal",
                    "score",
                    "raw_score",
                    "priority_rank",
                    "added",
                    "expires_at",
                )
            }
            for record in candidates
        ],
    }


def render_batch_markdown(batch: Mapping[str, Any]) -> str:
    lines = [
        f"# Paper Batch Triage - {batch['batch_id']}",
        "",
        "This is a decision packet, not evidence that any paper was read.",
        "Enrich each row with a source-grounded paper card before asking for decisions.",
        "",
        "| rank | title | tier | lane | score | venue | link | decision |",
        "|------|-------|------|------|-------|-------|------|----------|",
    ]
    for candidate in batch.get("candidates", []):
        lines.append(
            "| "
            + " | ".join(
                [
                    _clean(candidate.get("priority_rank")),
                    _clean(candidate.get("title")),
                    _clean(candidate.get("tier")),
                    _clean(candidate.get("lane")),
                    _clean(candidate.get("score")),
                    _clean(candidate.get("venue")),
                    _clean(candidate.get("url")),
                    "pending",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "Allowed decisions: `deep`, `targeted`, `cluster-only`, `skip`, `backlog`.",
            "Record at least one reason code for every decision.",
            "",
        ]
    )
    return "\n".join(lines)


def build_decision(
    raw: Mapping[str, Any], *, batch_id: str, recorded_at: str | None = None
) -> TriageDecision:
    action = _clean(raw.get("action"), 40)
    if action not in ACTIONS:
        raise ValueError(f"action must be one of {ACTIONS}")
    paper_id = _clean(raw.get("paper_id"), 300)
    if not paper_id:
        raise ValueError("paper_id is required")
    reasons = _unique(raw.get("reason_codes", []), allowed=set(REASON_CODES))
    if not reasons:
        raise ValueError("at least one reason_code is required")
    value = raw.get("predicted_value")
    if value is not None and (not isinstance(value, int) or not 1 <= value <= 5):
        raise ValueError("predicted_value must be an integer from 1 to 5")
    would_build_on = raw.get("would_build_on")
    if would_build_on is not None and not isinstance(would_build_on, bool):
        raise ValueError("would_build_on must be true, false, or null")
    selected_sections = _unique(raw.get("selected_sections", []))
    cluster_id = _clean(raw.get("cluster_id"), 160)
    if action == "targeted" and not selected_sections:
        raise ValueError("targeted decisions require selected_sections")
    if action == "cluster-only" and not cluster_id:
        raise ValueError("cluster-only decisions require cluster_id")
    timestamp = recorded_at or dt.datetime.now(dt.timezone.utc).isoformat()
    material = json.dumps(
        {
            "batch_id": batch_id,
            "paper_id": paper_id,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return TriageDecision(
        schema_version="1.0",
        decision_id="triage:" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20],
        batch_id=batch_id,
        paper_id=paper_id,
        candidate_slug=_clean(raw.get("candidate_slug"), 160),
        date=timestamp[:10],
        recorded_at=timestamp,
        action=action,
        reason_codes=reasons,
        rationale=_clean(raw.get("rationale")),
        would_build_on=would_build_on,
        predicted_value=value,
        selected_sections=selected_sections,
        cluster_id=cluster_id,
        actor="human",
        provenance={"source": "paper-batch-triage"},
    )


def build_comparison(
    raw: Mapping[str, Any], *, batch_id: str, recorded_at: str | None = None
) -> TasteComparison:
    winner = _clean(raw.get("winner_paper_id"), 300)
    loser = _clean(raw.get("loser_paper_id"), 300)
    if not winner or not loser or winner == loser:
        raise ValueError("comparison needs distinct winner_paper_id and loser_paper_id")
    reasons = _unique(raw.get("reason_codes", []), allowed=set(REASON_CODES))
    if not reasons:
        raise ValueError("comparison needs at least one reason_code")
    timestamp = recorded_at or dt.datetime.now(dt.timezone.utc).isoformat()
    material = json.dumps(
        {"batch_id": batch_id, "winner": winner, "loser": loser},
        ensure_ascii=False,
        sort_keys=True,
    )
    return TasteComparison(
        schema_version="1.0",
        comparison_id="comparison:"
        + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20],
        batch_id=batch_id,
        recorded_at=timestamp,
        winner_paper_id=winner,
        loser_paper_id=loser,
        reason_codes=reasons,
        rationale=_clean(raw.get("rationale")),
        actor="human",
        provenance={"source": "paper-batch-triage"},
    )


def _merge_idempotent(
    existing: list[dict[str, Any]], records: Iterable[Any], *, id_field: str
) -> tuple[list[dict[str, Any]], int]:
    by_id = {str(record.get(id_field, "")): record for record in existing}
    added = 0
    for record in records:
        payload = dataclasses.asdict(record) if dataclasses.is_dataclass(record) else dict(record)
        identifier = str(payload[id_field])
        if identifier in by_id:
            existing_payload = dict(by_id[identifier])
            candidate_payload = dict(payload)
            for timestamp_field in ("date", "recorded_at"):
                existing_payload.pop(timestamp_field, None)
                candidate_payload.pop(timestamp_field, None)
            if existing_payload != candidate_payload:
                raise ValueError(f"Conflicting event for {identifier}")
            continue
        by_id[identifier] = payload
        existing.append(payload)
        added += 1
    return existing, added


def append_idempotent(
    path: str | Path, records: Iterable[Any], *, id_field: str
) -> int:
    target = Path(path)
    existing, added = _merge_idempotent(
        load_jsonl(target), records, id_field=id_field
    )
    content = "".join(
        json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in existing
    )
    _atomic_write(target, content)
    return added


def apply_queue_decisions(
    records: Sequence[Mapping[str, Any]], decisions: Sequence[TriageDecision]
) -> list[dict[str, Any]]:
    by_id = {decision.paper_id: decision for decision in decisions}
    output: list[dict[str, Any]] = []
    matched: set[str] = set()
    for source in records:
        record = dict(source)
        decision = by_id.get(str(record.get("paper_id", "")))
        if decision is not None:
            record["status"] = ACTION_STATUS[decision.action]
            record["triage_action"] = decision.action
            record["pinned"] = decision.action in {"deep", "targeted"}
            matched.add(decision.paper_id)
        output.append(record)
    missing = sorted(set(by_id) - matched)
    if missing:
        raise ValueError("Decisions reference papers absent from queue: " + ", ".join(missing))
    return output


def write_jsonl(path: str | Path, records: Sequence[Mapping[str, Any]]) -> None:
    content = "".join(
        json.dumps(dict(record), ensure_ascii=False, sort_keys=True) + "\n"
        for record in records
    )
    _atomic_write(Path(path), content)


def _load_json(path_or_json: str) -> Any:
    candidate = Path(path_or_json)
    text = candidate.read_text(encoding="utf-8-sig") if candidate.exists() else path_or_json
    return json.loads(text)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare and apply paper batch-triage decisions")
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare")
    prepare.add_argument("--queue-state", required=True)
    prepare.add_argument("--output-dir", default="papers/batch_triage")
    prepare.add_argument("--batch-id")
    prepare.add_argument("--max-papers", type=int, default=10)

    apply = sub.add_parser("apply")
    apply.add_argument("--batch", required=True)
    apply.add_argument("--decisions", required=True, help="JSON object/file with decisions and comparisons")
    apply.add_argument("--triage-log", default="tutor/triage_feedback.jsonl")
    apply.add_argument("--comparison-log", default="tutor/taste_comparisons.jsonl")
    apply.add_argument("--queue-state", required=True)
    apply.add_argument("--output-queue-state")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "prepare":
        batch = prepare_batch(
            load_jsonl(args.queue_state),
            batch_id=args.batch_id,
            max_papers=args.max_papers,
        )
        output_dir = Path(args.output_dir)
        json_path = output_dir / f"{batch['batch_id']}.json"
        markdown_path = output_dir / f"{batch['batch_id']}.md"
        _atomic_write(json_path, json.dumps(batch, ensure_ascii=False, indent=2) + "\n")
        _atomic_write(markdown_path, render_batch_markdown(batch))
        print(
            json.dumps(
                {"batch_id": batch["batch_id"], "json": str(json_path), "markdown": str(markdown_path)},
                ensure_ascii=False,
            )
        )
        return 0

    batch = _load_json(args.batch)
    payload = _load_json(args.decisions)
    if not isinstance(batch, dict) or not isinstance(payload, dict):
        raise ValueError("batch and decisions inputs must be JSON objects")
    batch_id = _clean(batch.get("batch_id"), 120)
    candidate_ids = {
        str(candidate.get("paper_id", "")) for candidate in batch.get("candidates", [])
    }
    decisions = [build_decision(item, batch_id=batch_id) for item in payload.get("decisions", [])]
    decision_ids = {decision.paper_id for decision in decisions}
    if len(decision_ids) != len(decisions):
        raise ValueError("Each paper may have only one decision per batch")
    if decision_ids != candidate_ids:
        missing = sorted(candidate_ids - decision_ids)
        extra = sorted(decision_ids - candidate_ids)
        raise ValueError(
            "Decisions must cover the whole batch; "
            f"missing={missing or 'none'}, extra={extra or 'none'}"
        )
    comparisons = [
        build_comparison(item, batch_id=batch_id) for item in payload.get("comparisons", [])
    ]
    if any(
        comparison.winner_paper_id not in candidate_ids
        or comparison.loser_paper_id not in candidate_ids
        for comparison in comparisons
    ):
        raise ValueError("Every comparison must reference two papers in the batch")
    queue = apply_queue_decisions(load_jsonl(args.queue_state), decisions)
    triage_records, triage_added = _merge_idempotent(
        load_jsonl(args.triage_log), decisions, id_field="decision_id"
    )
    comparison_records, comparisons_added = _merge_idempotent(
        load_jsonl(args.comparison_log), comparisons, id_field="comparison_id"
    )
    output_queue = args.output_queue_state or args.queue_state
    write_jsonl(args.triage_log, triage_records)
    write_jsonl(args.comparison_log, comparison_records)
    write_jsonl(output_queue, queue)
    print(
        json.dumps(
            {
                "batch_id": batch_id,
                "decisions_added": triage_added,
                "comparisons_added": comparisons_added,
                "queue_state": str(output_queue),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
