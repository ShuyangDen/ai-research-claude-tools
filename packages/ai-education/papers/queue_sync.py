"""Merge the paper tracker's canonical queue with local reading state.

The tracker owns ``queue_state.jsonl``.  ``reading_queue.md`` is only a
compatibility view.  This helper lets the standalone AI Education project mark
completed/skipped papers in canonical state without importing tracker code.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import json
import os
import re
import tempfile
import unicodedata
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit


TERMINAL_STATUSES = {"completed", "dismissed", "skipped"}
QUEUE_FIELDS = {
    "schema_version",
    "paper_id",
    "candidate_slug",
    "title",
    "tier",
    "lane",
    "matched_signal",
    "authors",
    "venue",
    "url",
    "published",
    "added",
    "last_seen",
    "status",
    "score",
    "source",
    "identifiers",
}

_DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
_ARXIV_RE = re.compile(
    r"(?:arxiv:|arxiv\.org/(?:abs|pdf)/)(?P<id>(?:\d{4}\.\d{4,5}|[a-z-]+/\d{7})(?:v\d+)?)",
    re.IGNORECASE,
)
_OPENALEX_RE = re.compile(r"openalex\.org/(?P<id>W\d+)", re.IGNORECASE)
_NBER_RE = re.compile(r"nber\.org/(?:papers/)?(?P<id>w\d{3,})", re.IGNORECASE)
_TRACKING_QUERY_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid", "ref", "source"}


@dataclasses.dataclass
class QueueRecord:
    paper_id: str
    candidate_slug: str
    title: str
    tier: int
    lane: str
    matched_signal: str
    authors: str
    venue: str
    url: str
    published: str
    added: str
    last_seen: str
    status: str = "queued"
    score: float = 0.0
    source: str = ""
    identifiers: dict[str, str] = dataclasses.field(default_factory=dict)
    schema_version: str = "1.0"


def normalize_url(value: str) -> str:
    if not value:
        return ""
    parts = urlsplit(value.strip())
    scheme = parts.scheme.casefold()
    if scheme not in {"http", "https"} or not parts.netloc:
        return value.strip().casefold()
    host = (parts.hostname or "").casefold()
    port = parts.port
    netloc = host
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{host}:{port}"
    path = re.sub(r"/{2,}", "/", parts.path or "/")
    if path != "/":
        path = path.rstrip("/")
    query = [
        (key, item_value)
        for key, item_value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.casefold().startswith("utm_") and key.casefold() not in _TRACKING_QUERY_KEYS
    ]
    query.sort()
    return urlunsplit((scheme, netloc, path, urlencode(query), ""))


def normalize_title(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value or "").casefold()
    normalized = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", normalized)
    return " ".join(normalized.split())


def stable_paper_id(title: str, url: str = "") -> str:
    decoded = unquote(url or "")
    doi = _DOI_RE.search(decoded)
    if doi:
        return "doi:" + doi.group(0).rstrip(".,;)]}").casefold()
    arxiv = _ARXIV_RE.search(decoded)
    if arxiv:
        return "arxiv:" + re.sub(r"v\d+$", "", arxiv.group("id").casefold())
    openalex = _OPENALEX_RE.search(decoded)
    if openalex:
        return "openalex:" + openalex.group("id").upper()
    nber = _NBER_RE.search(decoded)
    if nber:
        return "nber:" + nber.group("id").casefold()
    normalized_url = normalize_url(url)
    material = normalized_url or normalize_title(title)
    kind = "url-sha256" if normalized_url else "title-sha256"
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]
    return f"{kind}:{digest}"


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9\s-]", "", title.casefold())
    return re.sub(r"\s+", "-", slug.strip())[:60] or "untitled-paper"


def _record_from_mapping(raw: dict[str, object]) -> QueueRecord:
    title = str(raw.get("title", "") or "")
    url = str(raw.get("url", "") or "")
    tier = int(raw.get("tier", 2) or 2)
    paper_id = str(raw.get("paper_id", "") or stable_paper_id(title, url))
    return QueueRecord(
        paper_id=paper_id,
        candidate_slug=str(raw.get("candidate_slug", "") or _slugify(title)),
        title=title,
        tier=tier,
        lane=str(raw.get("lane", "") or ("methodology" if tier == 3 else "adjacent")),
        matched_signal=str(raw.get("matched_signal", "") or "legacy"),
        authors=str(raw.get("authors", "") or ""),
        venue=str(raw.get("venue", "") or ""),
        url=url,
        published=str(raw.get("published", "") or ""),
        added=str(raw.get("added", "") or dt.date.today().isoformat()),
        last_seen=str(raw.get("last_seen", "") or raw.get("added", "") or dt.date.today().isoformat()),
        status=str(raw.get("status", "") or "queued"),
        score=float(raw.get("score", 0.0) or 0.0),
        source=str(raw.get("source", "") or ""),
        identifiers={str(k): str(v) for k, v in dict(raw.get("identifiers", {}) or {}).items()},
    )


def load_state(path: str | Path) -> list[QueueRecord]:
    source = Path(path)
    if not source.exists():
        return []
    records: list[QueueRecord] = []
    for line_number, line in enumerate(source.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise TypeError("record is not an object")
            records.append(_record_from_mapping({k: v for k, v in payload.items() if k in QUEUE_FIELDS}))
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid queue state at {source}:{line_number}: {exc}") from exc
    return records


def parse_markdown(path: str | Path) -> list[QueueRecord]:
    source = Path(path)
    if not source.exists():
        return []
    header: list[str] = []
    records: list[QueueRecord] = []
    for line in source.read_text(encoding="utf-8-sig").splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.split("|")[1:-1]]
        lowered = [cell.casefold() for cell in cells]
        if "candidate-slug" in lowered:
            header = lowered
            continue
        if not header or all(re.fullmatch(r":?-+:?", cell) for cell in cells):
            continue
        values = dict(zip(header, cells))
        if not values.get("title"):
            continue
        tier_match = re.search(r"\d+", values.get("tier", "2"))
        tier = int(tier_match.group(0)) if tier_match else 2
        direction = values.get("direction", "")
        records.append(
            _record_from_mapping(
                {
                    "candidate_slug": values.get("candidate-slug", ""),
                    "title": values.get("title", ""),
                    "tier": tier,
                    "authors": values.get("authors", ""),
                    "venue": values.get("venue", ""),
                    "url": values.get("url", ""),
                    "added": values.get("added", ""),
                    "matched_signal": f"manual:{direction}" if direction else "legacy",
                    "source": "manual" if direction else "legacy-markdown",
                }
            )
        )
    return records


def _completed_state(completed_path: str | Path, feedback_path: str | Path | None) -> tuple[set[str], set[str], dict[str, str]]:
    completed_slugs: set[str] = set()
    completed_urls: set[str] = set()
    completed = Path(completed_path)
    if completed.exists():
        text = completed.read_text(encoding="utf-8-sig")
        completed_urls.update(normalize_url(url.rstrip(".,;)")) for url in re.findall(r"https?://[^\s|]+", text))
        for line in text.splitlines():
            if not line.lstrip().startswith("|") or re.match(r"^\s*\|\s*:?-+", line):
                continue
            cells = [cell.strip() for cell in line.split("|")[1:-1]]
            if len(cells) >= 2 and cells[1].casefold() != "slug":
                completed_slugs.add(cells[1].casefold())

    feedback_status: dict[str, str] = {}
    if feedback_path and Path(feedback_path).exists():
        for line_number, line in enumerate(Path(feedback_path).read_text(encoding="utf-8-sig").splitlines(), 1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
                paper_id = str(event.get("paper_id", "")).strip().casefold()
                slug = str(event.get("slug", "")).strip().casefold()
                depth = str(event.get("read_depth", "")).strip().casefold()
                status = "skipped" if depth == "skipped" else "completed"
                if paper_id:
                    feedback_status[f"id:{paper_id}"] = status
                if slug and (not paper_id or paper_id.startswith("slug:")):
                    feedback_status[f"slug:{slug}"] = status
            except (json.JSONDecodeError, AttributeError) as exc:
                raise ValueError(f"Invalid reading feedback at {feedback_path}:{line_number}: {exc}") from exc
    return completed_slugs, completed_urls, feedback_status


def merge_queue(
    *,
    state_path: str | Path,
    remote_markdown_path: str | Path,
    local_markdown_path: str | Path,
    completed_path: str | Path,
    feedback_path: str | Path | None = None,
) -> tuple[list[QueueRecord], dict[str, int]]:
    records = load_state(state_path)
    migrated = 0
    if not records:
        records = parse_markdown(remote_markdown_path)
        migrated = len(records)

    by_id = {record.paper_id: record for record in records}
    by_url = {normalize_url(record.url): record.paper_id for record in records if normalize_url(record.url)}
    by_title = {normalize_title(record.title): record.paper_id for record in records if normalize_title(record.title)}
    by_slug = {record.candidate_slug.casefold(): record.paper_id for record in records}
    local_added = 0

    for local in parse_markdown(local_markdown_path):
        match_id = by_id.get(local.paper_id) and local.paper_id
        match_id = match_id or by_url.get(normalize_url(local.url))
        match_id = match_id or by_title.get(normalize_title(local.title))
        match_id = match_id or by_slug.get(local.candidate_slug.casefold())
        if match_id:
            current = by_id[match_id]
            current.url = current.url or local.url
            current.authors = current.authors or local.authors
            current.venue = current.venue or local.venue
            continue
        records.append(local)
        by_id[local.paper_id] = local
        if normalize_url(local.url):
            by_url[normalize_url(local.url)] = local.paper_id
        by_title[normalize_title(local.title)] = local.paper_id
        by_slug[local.candidate_slug.casefold()] = local.paper_id
        local_added += 1

    completed_slugs, completed_urls, feedback_status = _completed_state(completed_path, feedback_path)
    terminal_updates = 0
    for record in records:
        status = feedback_status.get(f"id:{record.paper_id.casefold()}")
        status = status or feedback_status.get(f"slug:{record.candidate_slug.casefold()}")
        if not status and (
            record.candidate_slug.casefold() in completed_slugs
            or normalize_url(record.url) in completed_urls
        ):
            status = "completed"
        if status and record.status != status:
            record.status = status
            terminal_updates += 1

    return records, {
        "migrated": migrated,
        "local_added": local_added,
        "terminal_updates": terminal_updates,
        "active": sum(record.status not in TERMINAL_STATUSES for record in records),
        "total": len(records),
    }


def _atomic_write(path: str | Path, content: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, target)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def write_state(path: str | Path, records: Iterable[QueueRecord]) -> None:
    content = "".join(
        json.dumps(dataclasses.asdict(record), ensure_ascii=False, sort_keys=True) + "\n"
        for record in sorted(records, key=lambda item: (item.added, item.paper_id))
    )
    _atomic_write(path, content)


def render_markdown(records: Iterable[QueueRecord]) -> str:
    active = [record for record in records if record.status not in TERMINAL_STATUSES]

    def sort_key(record: QueueRecord) -> tuple[int, int, str]:
        try:
            ordinal = dt.date.fromisoformat(record.added[:10]).toordinal()
        except (TypeError, ValueError):
            ordinal = 0
        return record.tier, -ordinal, record.candidate_slug

    active.sort(key=sort_key)
    header = (
        "# Reading Queue\n\n"
        "Derived compatibility view. Canonical state: `queue_state.jsonl`.\n\n"
        "Tier 1 = priority read. Tier 2 = adjacent/general fit. Tier 3 = methodology.\n\n"
        "| candidate-slug | title | tier | authors | venue | url | added |\n"
        "|----------------|-------|------|---------|-------|-----|-------|\n"
    )

    def safe(value: object) -> str:
        return str(value or "").replace("|", "/").replace("\n", " ").strip()

    rows = [
        "| " + " | ".join(
            [
                safe(record.candidate_slug),
                safe(record.title),
                str(record.tier),
                safe(record.authors),
                safe(record.venue),
                safe(record.url),
                safe(record.added),
            ]
        ) + " |"
        for record in active
    ]
    return header + "\n".join(rows) + ("\n" if rows else "")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Merge canonical and local reading queue state")
    parser.add_argument("--state", required=True, help="Downloaded canonical queue_state.jsonl (may not exist)")
    parser.add_argument("--remote-markdown", required=True, help="Downloaded legacy reading_queue.md fallback")
    parser.add_argument("--local-markdown", default="papers/reading_queue.md")
    parser.add_argument("--completed", default="tutor/completed_papers.md")
    parser.add_argument("--feedback", default="tutor/reading_feedback.jsonl")
    parser.add_argument("--output-state", default="papers/queue_state.jsonl")
    parser.add_argument("--output-markdown", default="papers/reading_queue.md")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    records, summary = merge_queue(
        state_path=args.state,
        remote_markdown_path=args.remote_markdown,
        local_markdown_path=args.local_markdown,
        completed_path=args.completed,
        feedback_path=args.feedback,
    )
    write_state(args.output_state, records)
    _atomic_write(args.output_markdown, render_markdown(records))
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
