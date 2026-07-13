"""Record durable paper-reading feedback for the recommendation loop.

The JSONL file is canonical. ``paper_preferences.md`` is a generated,
human-readable compatibility view consumed by the profile-sync workflow.
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
from typing import Iterable


READ_DEPTHS = ("full", "selective", "rough", "skipped")
RATINGS = ("high-value", "useful", "low-fit")
SCHEMA_VERSION = "1.0"


@dataclasses.dataclass(frozen=True)
class ReadingFeedback:
    schema_version: str
    feedback_id: str
    paper_id: str
    date: str
    slug: str
    queue_item_id: str | None
    recorded_at: str
    read_depth: str
    rating: str
    outcome: str
    usefulness: str
    surprise: str
    belief_changed: str
    idea_affected: list[str]
    reason: str
    actor: str
    provenance: dict[str, str]

    @property
    def event_id(self) -> str:
        """Compatibility alias for pre-1.0 callers."""

        return self.feedback_id

    @property
    def created_at(self) -> str:
        """Compatibility alias for pre-1.0 callers."""

        return self.recorded_at


def _clean(value: str, limit: int = 800) -> str:
    return " ".join((value or "").replace("|", "/").split())[:limit]


def _unique(values: Iterable[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = _clean(value, 120)
        key = cleaned.casefold()
        if cleaned and key not in seen:
            seen.add(key)
            output.append(cleaned)
    return output


def build_feedback(
    *,
    slug: str,
    paper_id: str,
    read_depth: str,
    rating: str,
    usefulness: str,
    surprise: str = "",
    belief_changed: str = "",
    idea_affected: Iterable[str] = (),
    date: str | None = None,
    source: str = "paper-reading-tutor",
    reason: str = "",
    actor: str = "human",
    run_id: str | None = None,
    queue_item_id: str | None = None,
) -> ReadingFeedback:
    if read_depth not in READ_DEPTHS:
        raise ValueError(f"read_depth must be one of {READ_DEPTHS}")
    if rating not in RATINGS:
        raise ValueError(f"rating must be one of {RATINGS}")
    event_date = date or dt.date.today().isoformat()
    dt.date.fromisoformat(event_date)
    cleaned_slug = _clean(slug, 160)
    if not cleaned_slug:
        raise ValueError("slug cannot be empty")
    cleaned_paper_id = _clean(paper_id, 300)
    if not cleaned_paper_id:
        raise ValueError("paper_id cannot be empty")
    provenance = {"source": _clean(source, 80)}
    if run_id:
        provenance["run_id"] = _clean(run_id, 200)
    normalized = {
        "schema_version": SCHEMA_VERSION,
        "paper_id": cleaned_paper_id,
        "date": event_date,
        "slug": cleaned_slug,
        "queue_item_id": _clean(queue_item_id, 300) or None,
        "read_depth": read_depth,
        "rating": rating,
        "outcome": "skipped" if read_depth == "skipped" else "completed",
        "usefulness": _clean(usefulness),
        "surprise": _clean(surprise),
        "belief_changed": _clean(belief_changed),
        "idea_affected": _unique(idea_affected),
        "reason": _clean(reason),
        "actor": _clean(actor, 80) or "human",
        "provenance": provenance,
    }
    if not normalized["usefulness"]:
        raise ValueError("usefulness cannot be empty; use 'none' for a low-fit/skip record")
    identity = (
        {"paper_id": cleaned_paper_id, "run_id": provenance["run_id"]}
        if provenance.get("run_id")
        else normalized
    )
    event_material = json.dumps(identity, ensure_ascii=False, sort_keys=True)
    feedback_id = "feedback:" + hashlib.sha256(event_material.encode("utf-8")).hexdigest()[:20]
    return ReadingFeedback(
        feedback_id=feedback_id,
        recorded_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        **normalized,
    )


def _normalize_loaded_payload(raw: dict[str, object]) -> dict[str, object]:
    """Upgrade pre-1.0 feedback rows without losing their human content."""

    payload = dict(raw)
    legacy_source = str(payload.pop("source", "paper-reading-tutor"))
    payload.setdefault("schema_version", SCHEMA_VERSION)
    payload.setdefault("feedback_id", payload.pop("event_id", ""))
    payload.setdefault("recorded_at", payload.pop("created_at", ""))
    recorded_at = str(payload.get("recorded_at", ""))
    payload.setdefault("date", recorded_at[:10] if recorded_at else dt.date.today().isoformat())
    slug = str(payload.get("slug", ""))
    payload.setdefault("paper_id", f"slug:{slug}")
    payload.setdefault("queue_item_id", None)
    rating_aliases = {"high_value": "high-value", "low_fit": "low-fit", "not_read": "low-fit"}
    payload["rating"] = rating_aliases.get(str(payload.get("rating", "")), payload.get("rating", ""))
    depth_aliases = {"abstract": "rough", "none": "skipped"}
    payload["read_depth"] = depth_aliases.get(str(payload.get("read_depth", "")), payload.get("read_depth", ""))
    payload.setdefault("outcome", "skipped" if payload.get("read_depth") == "skipped" else "completed")
    if "usefulness" not in payload:
        useful = payload.pop("useful_signals", [])
        payload["usefulness"] = ", ".join(str(item) for item in useful) or str(payload.get("reason", "none"))
    payload.setdefault("surprise", "; ".join(str(item) for item in payload.pop("contradictions", [])))
    payload.setdefault("belief_changed", str(payload.pop("idea_delta", "")))
    payload.setdefault("idea_affected", [])
    payload.setdefault("reason", "")
    payload.setdefault("actor", "human")
    provenance = payload.get("provenance")
    if not isinstance(provenance, dict):
        provenance = {}
    provenance.setdefault("source", legacy_source)
    payload["provenance"] = provenance
    allowed = {field.name for field in dataclasses.fields(ReadingFeedback)}
    extras = {key: payload.pop(key) for key in list(payload) if key not in allowed}
    if extras:
        provenance["legacy_fields"] = json.dumps(extras, ensure_ascii=False, sort_keys=True)
    return payload


def load_feedback(path: str | Path) -> list[ReadingFeedback]:
    source = Path(path)
    if not source.exists():
        return []
    records: list[ReadingFeedback] = []
    for line_number, line in enumerate(source.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise TypeError("feedback row must be a JSON object")
            records.append(ReadingFeedback(**_normalize_loaded_payload(raw)))
        except (json.JSONDecodeError, TypeError) as exc:
            raise ValueError(f"Invalid feedback record at {source}:{line_number}: {exc}") from exc
    return records


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def render_markdown(records: Iterable[ReadingFeedback]) -> str:
    ordered = sorted(
        records,
        key=lambda record: (record.date, record.recorded_at, record.feedback_id),
        reverse=True,
    )
    header = (
        "# Paper Preferences\n\n"
        "Derived view. Canonical event log: `reading_feedback.jsonl`.\n\n"
        "`rating`: `high-value` | `useful` | `low-fit`  \n"
        "`read_depth`: `full` | `selective` | `rough` | `skipped`\n\n"
        "| date | paper_id | slug | rating | read_depth | usefulness | surprise | belief_changed | idea_affected |\n"
        "|------|----------|------|--------|------------|------------|----------|----------------|---------------|\n"
    )
    rows = [
        "| "
        + " | ".join(
            [
                record.date,
                _clean(record.paper_id, 300),
                _clean(record.slug, 160),
                record.rating,
                record.read_depth,
                _clean(record.usefulness),
                _clean(record.surprise),
                _clean(record.belief_changed),
                ", ".join(record.idea_affected),
            ]
        )
        + " |"
        for record in ordered
    ]
    return header + "\n".join(rows) + ("\n" if rows else "")


def record_feedback(
    feedback: ReadingFeedback,
    *,
    jsonl_path: str | Path,
    markdown_path: str | Path,
) -> bool:
    """Append an event idempotently and regenerate the Markdown view."""

    records = load_feedback(jsonl_path)
    existing = next((record for record in records if record.feedback_id == feedback.feedback_id), None)
    if existing is not None:
        comparable_existing = dataclasses.asdict(existing)
        comparable_feedback = dataclasses.asdict(feedback)
        comparable_existing.pop("recorded_at", None)
        comparable_feedback.pop("recorded_at", None)
        if comparable_existing != comparable_feedback:
            raise ValueError(
                f"Conflicting feedback for {feedback.paper_id} in the same run; revise before appending"
            )
        _atomic_write(Path(markdown_path), render_markdown(records))
        return False
    records.append(feedback)
    canonical = "".join(
        json.dumps(dataclasses.asdict(record), ensure_ascii=False, sort_keys=True) + "\n"
        for record in records
    )
    _atomic_write(Path(jsonl_path), canonical)
    _atomic_write(Path(markdown_path), render_markdown(records))
    return True


def _default_paths() -> tuple[Path, Path]:
    tutor_dir = Path(__file__).resolve().parent
    return tutor_dir / "reading_feedback.jsonl", tutor_dir / "paper_preferences.md"


def build_parser() -> argparse.ArgumentParser:
    jsonl_default, markdown_default = _default_paths()
    parser = argparse.ArgumentParser(description="Record durable paper-reading feedback")
    parser.add_argument("--jsonl-path", default=str(jsonl_default))
    parser.add_argument("--markdown-path", default=str(markdown_default))
    subparsers = parser.add_subparsers(dest="command", required=True)

    record = subparsers.add_parser("record")
    record.add_argument("--slug", required=True)
    record.add_argument("--paper-id", required=True, help="Canonical DOI/arXiv/OpenAlex/NBER/URL/title ID")
    record.add_argument("--read-depth", required=True, choices=READ_DEPTHS)
    record.add_argument("--rating", required=True, choices=RATINGS)
    record.add_argument("--usefulness", required=True)
    record.add_argument("--surprise", default="")
    record.add_argument("--belief-changed", default="")
    record.add_argument("--idea-affected", action="append", default=[])
    record.add_argument("--date")
    record.add_argument("--source", default="paper-reading-tutor")
    record.add_argument("--reason", default="")
    record.add_argument("--actor", default="human")
    record.add_argument("--run-id")
    record.add_argument("--queue-item-id")

    subparsers.add_parser("render")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "render":
        records = load_feedback(args.jsonl_path)
        _atomic_write(Path(args.markdown_path), render_markdown(records))
        print(f"Rendered {len(records)} feedback records to {args.markdown_path}")
        return 0

    feedback = build_feedback(
        slug=args.slug,
        paper_id=args.paper_id,
        read_depth=args.read_depth,
        rating=args.rating,
        usefulness=args.usefulness,
        surprise=args.surprise,
        belief_changed=args.belief_changed,
        idea_affected=args.idea_affected,
        date=args.date,
        source=args.source,
        reason=args.reason,
        actor=args.actor,
        run_id=args.run_id,
        queue_item_id=args.queue_item_id,
    )
    added = record_feedback(
        feedback,
        jsonl_path=args.jsonl_path,
        markdown_path=args.markdown_path,
    )
    print(json.dumps({"feedback_id": feedback.feedback_id, "paper_id": feedback.paper_id, "added": added}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
