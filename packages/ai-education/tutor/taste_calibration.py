"""Evaluate whether the recommendation profile predicts human paper rankings."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Iterable


def _unique(values: Iterable[object]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        paper_id = str(value or "").strip()
        if paper_id and paper_id not in seen:
            seen.add(paper_id)
            output.append(paper_id)
    return output


def precision_at_k(predicted: list[str], human: list[str], k: int) -> float:
    if k < 1:
        raise ValueError("k must be positive")
    denominator = min(k, len(human))
    if denominator == 0:
        return 0.0
    return len(set(predicted[:k]) & set(human[:k])) / denominator


def pairwise_agreement(predicted: list[str], human: list[str]) -> float:
    predicted_ids = set(predicted)
    shared = [paper_id for paper_id in human if paper_id in predicted_ids]
    if len(shared) < 2:
        return 0.0
    predicted_rank = {paper_id: index for index, paper_id in enumerate(predicted)}
    human_rank = {paper_id: index for index, paper_id in enumerate(human)}
    total = 0
    agreed = 0
    for left_index, left in enumerate(shared):
        for right in shared[left_index + 1 :]:
            total += 1
            model_order = predicted_rank[left] < predicted_rank[right]
            human_order = human_rank[left] < human_rank[right]
            agreed += int(model_order == human_order)
    return agreed / total if total else 0.0


def evaluate_rankings(
    predicted: Iterable[object], human: Iterable[object], *, k: int = 3
) -> dict[str, object]:
    model_ranking = _unique(predicted)
    human_ranking = _unique(human)
    shared = set(model_ranking) & set(human_ranking)
    if len(shared) < 2:
        raise ValueError("rankings need at least two shared paper IDs")
    return {
        "predicted_count": len(model_ranking),
        "human_count": len(human_ranking),
        "shared_count": len(shared),
        "precision_at_k": round(precision_at_k(model_ranking, human_ranking, k), 6),
        "pairwise_agreement": round(pairwise_agreement(model_ranking, human_ranking), 6),
        "k": k,
    }


def _load_array(value: str) -> list[object]:
    candidate = Path(value)
    text = candidate.read_text(encoding="utf-8-sig") if candidate.exists() else value
    parsed = json.loads(text)
    if not isinstance(parsed, list):
        raise ValueError("ranking input must be a JSON array or path to one")
    return parsed


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


def append_calibration(path: str | Path, event: dict[str, object]) -> bool:
    target = Path(path)
    existing: list[dict[str, object]] = []
    if target.exists():
        for line in target.read_text(encoding="utf-8-sig").splitlines():
            if line.strip():
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError("calibration log rows must be objects")
                existing.append(value)
    for item in existing:
        if item.get("calibration_id") != event["calibration_id"]:
            continue
        existing_payload = dict(item)
        candidate_payload = dict(event)
        existing_payload.pop("recorded_at", None)
        candidate_payload.pop("recorded_at", None)
        if existing_payload != candidate_payload:
            raise ValueError(f"Conflicting calibration event: {event['calibration_id']}")
        return False
    existing.append(event)
    _atomic_write(
        target,
        "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in existing),
    )
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate held-out paper ranking agreement")
    parser.add_argument("--predicted", required=True, help="JSON array or file")
    parser.add_argument("--human", required=True, help="JSON array or file")
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--profile-hash", default="")
    parser.add_argument("--log", default="tutor/taste_calibration.jsonl")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    predicted = _load_array(args.predicted)
    human = _load_array(args.human)
    metrics = evaluate_rankings(predicted, human, k=args.k)
    timestamp = dt.datetime.now(dt.timezone.utc).isoformat()
    material = json.dumps(
        {
            "batch_id": args.batch_id,
            "predicted": predicted,
            "human": human,
            "k": args.k,
            "profile_hash": args.profile_hash,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    event = {
        "schema_version": "1.0",
        "calibration_id": "calibration:"
        + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20],
        "batch_id": args.batch_id,
        "recorded_at": timestamp,
        "profile_hash": args.profile_hash,
        "metrics": metrics,
        "actor": "human",
    }
    event["added"] = append_calibration(args.log, event)
    print(json.dumps(event, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
