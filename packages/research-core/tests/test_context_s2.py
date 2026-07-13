from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_core.contracts import validate_contract
from research_core.idea_context import build_idea_context, write_context_manifest
from research_core.s2check import HUMAN_FIELDS, apply_ready, check_s2, compute_scope_hash, parse_frontmatter


FIXTURES = Path(__file__).parent / "fixtures"


def test_idea_context_is_bounded_diverse_provenance_bearing_and_profile_free(workflow_fixture: Path) -> None:
    idea_vault = workflow_fixture / "idea-vault"
    pkb_vault = workflow_fixture / "pkb"
    result = build_idea_context(
        idea_vault=idea_vault,
        pkb_vault=pkb_vault,
        slug="demo",
        objective="Find contradictory evidence, causal identification methods, and data for AI tutoring feedback",
        mode="literature",
    )
    assert result["retrieval_order"] == [
        "target_idea",
        "authoritative_s2_gate",
        "latest_session",
        "explicit_objective_and_mode",
        "pkb_wiki_index",
        "pkb_wiki_pages",
        "pkb_sources",
        "related_ideas",
    ]
    assert result["scope_hash"] == "authoritative-scope-v2"
    assert result["session_stale"] is False
    assert len(result["packets"]) <= 8
    assert result["stats"]["full_source_count"] <= 3
    assert result["packets"][0]["source_ref"]["source_type"] == "s2_gate"
    assert {"nearest", "contradict", "method", "data"} <= {packet["category"] for packet in result["packets"]}
    serialized = json.dumps(result, ensure_ascii=False)
    assert "SECRET_PROFILE_ONLY_TOKEN" not in serialized
    assert "researcher_profile.md" not in serialized
    for packet in result["packets"]:
        assert Path(packet["source_ref"]["path"]).exists()
        assert len(packet["source_ref"]["content_hash"]) == 64
        assert packet["claim_id"].startswith("claim:")
        assert validate_contract("claim-card", packet) == []
    assert validate_contract("context-manifest", result) == []
    assert result["context_id"] == build_idea_context(
        idea_vault=idea_vault,
        pkb_vault=pkb_vault,
        slug="demo",
        objective="Find contradictory evidence, causal identification methods, and data for AI tutoring feedback",
        mode="literature",
    )["context_id"]


def test_context_write_is_confined_to_session_workspace(workflow_fixture: Path) -> None:
    idea_vault = workflow_fixture / "idea-vault"
    result = build_idea_context(
        idea_vault=idea_vault,
        pkb_vault=workflow_fixture / "pkb",
        slug="demo",
        objective="Clarify the nearest literature",
    )
    workspace = idea_vault / "ideas" / "sessions" / "runs" / "demo"
    path = write_context_manifest(result, workspace=workspace)
    assert path.exists()
    assert json.loads(path.read_text(encoding="utf-8"))["context_id"] == result["context_id"]
    with pytest.raises(ValueError):
        write_context_manifest(result, workspace=idea_vault / "ideas")


def _ready_sidecar(tmp_path: Path) -> Path:
    source = (FIXTURES / "s2-ready.md").read_text(encoding="utf-8")
    provisional = source.replace("__SCOPE_HASH__", "pending")
    scope_hash = compute_scope_hash(provisional)
    assert scope_hash
    path = tmp_path / "idea-vault" / "ideas" / "reviews" / "demo-s2-gate.md"
    path.parent.mkdir(parents=True)
    path.write_text(source.replace("__SCOPE_HASH__", scope_hash), encoding="utf-8")
    idea = path.parent.parent / "demo.md"
    idea.write_text("---\ns2_gate_outcome: pending\n---\n# Demo\n", encoding="utf-8")
    return path


def test_s2_check_blocks_dirty_scope_and_unread_threat(tmp_path: Path) -> None:
    path = _ready_sidecar(tmp_path)
    text = path.read_text(encoding="utf-8")
    text = text.replace("gate_dirty: false", "gate_dirty: true").replace("scope_hash:", "scope_hash: wrong #")
    text = text.replace("read and verified", "unread")
    path.write_text(text, encoding="utf-8")
    report = check_s2(path)
    codes = {item["code"] for item in report["blockers"]}
    assert {"gate.dirty", "scope.hash_mismatch", "reading.unread_high_threat"} <= codes
    assert report["ready"] is False
    with pytest.raises(ValueError):
        apply_ready(path, report)


def test_s2_apply_ready_changes_only_generated_fields(tmp_path: Path) -> None:
    path = _ready_sidecar(tmp_path)
    report = check_s2(path)
    assert report["ready"] is True, report["blockers"]
    before, _, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
    applied = apply_ready(path, report)
    after, _, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
    assert applied["ready"] is True
    assert {field: before.get(field) for field in HUMAN_FIELDS} == {field: after.get(field) for field in HUMAN_FIELDS}
    assert after["ai_readiness"] == "READY_FOR_HUMAN_DECISION"
    assert after["gate_status"] == "ready_for_human_decision"
    assert after["gate_phase"] == "adjudication"
    assert after["readiness_checked_at"]
