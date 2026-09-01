"""Structured, provider-neutral archives for Paper Tracker discovery runs."""

from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping


SCHEMA = "ai-research-workbench.candidate-pool"
SCHEMA_VERSION = 1


def iso_week(value: dt.date | None = None) -> str:
    current = value or dt.date.today()
    info = current.isocalendar()
    return f"{info.year}-W{info.week:02d}"


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def write_json(path: Path, value: Any) -> None:
    data = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    _atomic_write(path, data)


def _value(paper: Any, name: str, default: Any = "") -> Any:
    if isinstance(paper, Mapping):
        return paper.get(name, default)
    return getattr(paper, name, default)


def serialize_paper(paper: Any, *, fetched_at: str) -> dict[str, Any]:
    source = str(_value(paper, "source"))
    url = str(_value(paper, "url"))
    identifiers = {
        key: str(value)
        for key, value in {
            "doi": _value(paper, "doi"),
            "arxiv_id": _value(paper, "arxiv_id"),
            "openalex_id": _value(paper, "openalex_id"),
        }.items()
        if value
    }
    return {
        "paper_id": str(_value(paper, "paper_id")),
        "title": str(_value(paper, "title")),
        "abstract": str(_value(paper, "abstract")),
        "authors": str(_value(paper, "authors")),
        "venue": str(_value(paper, "venue")),
        "url": url,
        "published": str(_value(paper, "published")),
        "source": source,
        "methodology": str(_value(paper, "methodology")),
        "tier": int(_value(paper, "tier", 2) or 2),
        "lane": str(_value(paper, "lane", "adjacent")),
        "identifiers": identifiers,
        "provenance": [
            {
                "source": source,
                "source_id": identifiers.get("openalex_id") or identifiers.get("arxiv_id") or identifiers.get("doi", ""),
                "fetched_at": fetched_at,
                "url": url,
            }
        ],
    }


def candidate_pool_payload(
    papers: Iterable[Any],
    *,
    week: str,
    github_run_id: str,
    source_health: Mapping[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    records = [serialize_paper(paper, fetched_at=generated_at) for paper in papers]
    base = {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "week": week,
        "github_run_id": github_run_id,
        "generated_at": generated_at,
        "source_health": dict(source_health),
        "papers": records,
    }
    canonical = json.dumps(base, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    base["content_hash"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return base


def _public_report(payload: Mapping[str, Any]) -> str:
    lines = [
        f"# Paper Tracker discovery — {payload['week']}",
        "",
        f"GitHub run: `{payload['github_run_id']}`",
        f"Candidates: {len(payload['papers'])}",
        "",
        "This report contains discovery provenance only. Personalized ranking reasons stay local.",
        "",
    ]
    for index, paper in enumerate(payload["papers"], 1):
        lines.extend(
            [
                f"## {index}. {paper['title']}",
                "",
                f"- Source: {paper['source']}",
                f"- Published: {paper['published']}",
                f"- URL: {paper['url']}",
                "",
            ]
        )
    return "\n".join(lines)


def write_discovery_archive(
    papers: Iterable[Any],
    *,
    source_health: Any,
    archive_root: str | Path = "archives",
    run_id: str | None = None,
    run_date: dt.date | None = None,
) -> dict[str, Any]:
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    week = iso_week(run_date)
    github_run_id = run_id or os.environ.get("GITHUB_RUN_ID") or f"local-{now.replace(':', '').replace('-', '')}"
    root = Path(archive_root) / week / github_run_id
    if dataclasses.is_dataclass(source_health):
        health = dataclasses.asdict(source_health)
    elif isinstance(source_health, Mapping):
        health = dict(source_health)
    else:
        health = {}
    payload = candidate_pool_payload(
        papers,
        week=week,
        github_run_id=github_run_id,
        source_health=health,
        generated_at=now,
    )
    pool_path = root / "candidate_pool.json"
    health_path = root / "source_health.json"
    report_path = root / "discovery_report.md"
    manifest_path = root / "manifest.json"
    write_json(pool_path, payload)
    write_json(health_path, health)
    _atomic_write(report_path, (_public_report(payload) + "\n").encode("utf-8"))
    manifest = {
        "schema": "ai-research-workbench.tracker-run",
        "schema_version": 1,
        "github_run_id": github_run_id,
        "week": week,
        "mode": "discovery-only",
        "status": "failed" if health.get("status") == "failed" else "succeeded",
        "started_at": health.get("started_at", now),
        "finished_at": health.get("completed_at", now),
        "candidate_count": len(payload["papers"]),
        "content_hash": payload["content_hash"],
        "artifacts": [str(pool_path), str(health_path), str(report_path)],
    }
    write_json(manifest_path, manifest)
    return {
        "root": str(root),
        "manifest_path": str(manifest_path),
        "candidate_pool_path": str(pool_path),
        "archive_source_health_path": str(health_path),
        "discovery_report_path": str(report_path),
        "manifest": manifest,
    }


def finalize_digest_archive(archive: Mapping[str, Any], *, report_path: str, status: str = "succeeded") -> None:
    manifest_path = Path(str(archive["manifest_path"]))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["mode"] = "digest-and-discovery"
    manifest["status"] = status
    manifest["finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    if report_path and report_path not in manifest["artifacts"]:
        manifest["artifacts"].append(report_path)
    write_json(manifest_path, manifest)
