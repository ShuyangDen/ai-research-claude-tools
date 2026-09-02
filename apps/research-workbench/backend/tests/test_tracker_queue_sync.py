from __future__ import annotations

import json

import pytest

from research_workbench.tracker_queue_sync import (
    QueueMergeError,
    merge_queue_text,
    parse_queue_jsonl,
    render_reading_queue,
    serialize_queue,
)


def record(paper_id: str, **updates):  # type: ignore[no-untyped-def]
    value = {
        "paper_id": paper_id,
        "candidate_slug": paper_id.replace(":", "-"),
        "title": f"A sufficiently distinctive title for {paper_id}",
        "tier": 2,
        "lane": "adjacent",
        "matched_signal": "",
        "authors": "A. Author",
        "venue": "Working Paper",
        "url": f"https://example.test/{paper_id}?utm_source=digest",
        "published": "2026-08-01",
        "added": "2026-08-10",
        "last_seen": "2026-08-10",
        "status": "queued",
        "score": 70.0,
        "triage_action": "",
        "pinned": False,
        "identifiers": {},
        "schema_version": "1.1",
    }
    value.update(updates)
    return value


def test_merge_preserves_local_completion_and_adds_remote_recommendation() -> None:
    local = record(
        "doi:one",
        status="completed",
        triage_action="complete-full",
        pinned=True,
        user_updated_at="2026-09-02T12:00:00Z",
    )
    remote_existing = record(
        "doi:one",
        last_seen="2026-09-03",
        score=98.0,
        abstract="A much newer complete abstract.",
        abstract_evidence="complete",
    )
    remote_new = record("doi:two", last_seen="2026-09-03", score=95.0)

    merged_text, markdown, count = merge_queue_text(
        serialize_queue([local]), serialize_queue([remote_existing, remote_new])
    )
    merged = parse_queue_jsonl(merged_text, source="merged")

    assert count == 2
    first = next(item for item in merged if item["paper_id"] == "doi:one")
    assert first["status"] == "completed"
    assert first["triage_action"] == "complete-full"
    assert first["pinned"] is True
    assert first["score"] == 98.0
    assert first["abstract"] == "A much newer complete abstract."
    assert "doi-two" in markdown
    assert "doi-one" not in markdown


def test_merge_deduplicates_legacy_identity_by_url() -> None:
    local = record("title-sha256:old", status="in_progress")
    remote = record("doi:new", url="https://example.test/title-sha256:old", score=92.0)
    merged_text, _, count = merge_queue_text(serialize_queue([local]), serialize_queue([remote]))
    merged = parse_queue_jsonl(merged_text, source="merged")
    assert count == 1
    assert merged[0]["status"] == "in_progress"
    assert merged[0]["score"] == 92.0


def test_newer_explicit_user_timestamp_can_change_prior_decision() -> None:
    local = record("doi:one", status="completed", user_updated_at="2026-09-01T12:00:00Z")
    remote = record("doi:one", status="backlog", user_updated_at="2026-09-02T12:00:00Z")
    merged_text, _, _ = merge_queue_text(serialize_queue([local]), serialize_queue([remote]))
    assert parse_queue_jsonl(merged_text, source="merged")[0]["status"] == "backlog"


def test_generated_expiry_never_downgrades_a_local_active_choice() -> None:
    local = record("doi:one", status="queued")
    remote = record("doi:one", status="expired", last_seen="2026-09-03")
    merged_text, _, _ = merge_queue_text(serialize_queue([local]), serialize_queue([remote]))
    assert parse_queue_jsonl(merged_text, source="merged")[0]["status"] == "queued"


def test_invalid_queue_is_rejected_before_git_merge() -> None:
    with pytest.raises(QueueMergeError, match="Invalid queue JSON"):
        merge_queue_text("{not-json}\n", "")


def test_renderer_uses_only_active_records() -> None:
    rendered = render_reading_queue([record("doi:active"), record("doi:done", status="completed")])
    assert "doi-active" in rendered
    assert "doi-done" not in rendered
