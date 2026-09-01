from __future__ import annotations

import dataclasses
import json
import sys
from datetime import date
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_DIR))

from tracker_archive import candidate_pool_payload, write_discovery_archive  # noqa: E402


@dataclasses.dataclass
class Paper:
    paper_id: str
    title: str
    abstract: str
    source: str
    url: str
    published: str
    authors: str = ""
    venue: str = ""
    methodology: str = ""
    tier: int = 2
    lane: str = "adjacent"
    doi: str = ""
    arxiv_id: str = ""
    openalex_id: str = ""


def test_candidate_pool_hash_is_deterministic_and_keeps_abstract() -> None:
    papers = [Paper("doi:10/x", "A paper", "Full abstract", "openalex", "https://example.test", "2026-08-20")]
    kwargs = {
        "week": "2026-W35",
        "github_run_id": "123",
        "source_health": {"status": "ok"},
        "generated_at": "2026-08-24T12:00:00Z",
    }
    first = candidate_pool_payload(papers, **kwargs)
    second = candidate_pool_payload(papers, **kwargs)
    assert first["content_hash"] == second["content_hash"]
    assert first["papers"][0]["abstract"] == "Full abstract"
    assert "relevance_reason" not in first["papers"][0]


def test_archive_layout_and_repeat_run_are_atomic(tmp_path: Path) -> None:
    paper = Paper("arxiv:2608.1", "Test", "Abstract", "arxiv", "https://arxiv.org/abs/2608.1", "2026-08-20")
    health = {"status": "ok", "started_at": "2026-08-24T01:00:00Z", "completed_at": "2026-08-24T01:01:00Z"}
    first = write_discovery_archive(
        [paper], source_health=health, archive_root=tmp_path, run_id="987", run_date=date(2026, 8, 24)
    )
    second = write_discovery_archive(
        [paper], source_health=health, archive_root=tmp_path, run_id="987", run_date=date(2026, 8, 24)
    )
    root = tmp_path / "2026-W35" / "987"
    assert Path(first["root"]) == root
    assert first["manifest"]["content_hash"] == second["manifest"]["content_hash"]
    assert {"manifest.json", "candidate_pool.json", "source_health.json", "discovery_report.md"} <= {
        path.name for path in root.iterdir()
    }
    payload = json.loads((root / "candidate_pool.json").read_text(encoding="utf-8"))
    assert payload["github_run_id"] == "987"


def test_failed_source_health_is_preserved_in_manifest(tmp_path: Path) -> None:
    archive = write_discovery_archive(
        [],
        source_health={"status": "failed", "errors": ["openalex failed"]},
        archive_root=tmp_path,
        run_id="failed-run",
        run_date=date(2026, 8, 24),
    )
    assert archive["manifest"]["status"] == "failed"
    assert archive["manifest"]["candidate_count"] == 0
