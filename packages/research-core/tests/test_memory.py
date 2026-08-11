from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from research_core.contracts import validate_contract
from research_core.memory import memory_summary, record_idea_feedback, record_reasoning


AXES = {
    "intrinsic_interest": "positive",
    "importance": "unknown",
    "mechanism": "positive",
    "novelty": "unknown",
    "identification": "unknown",
    "data_feasibility": "negative",
    "time_to_signal": "negative",
    "salvage_value": "negative",
    "jmp_fit": "negative",
    "advisor_fit": "negative",
}


def test_direct_human_reasoning_is_idempotent_and_profile_eligible(tmp_path: Path) -> None:
    event = {
        "occurred_at": "2026-08-11T18:00:00Z",
        "actor": "human",
        "actor_basis": "direct",
        "context_type": "feasibility",
        "context_id": "school-phone-ban-enforcement-cost",
        "trigger": "Large data build before any informative result",
        "thinking_moves": ["data_feasibility", "time_cost", "option_value"],
        "reasoning_summary": "Prefer staged evidence before irreversible collection.",
        "decision": "Use an early feasibility gate.",
        "alternatives_rejected": ["Collect the full linked dataset first"],
        "transfer_rule": "Require a cheap first signal and a salvageable artifact.",
        "durability": "declared_constraint",
        "human_confirmed": True,
        "profile_eligible": True,
        "confidence": 5,
        "source_refs": [{"type": "idea", "slug": "school-phone-ban-enforcement-cost"}],
        "provenance": {"source": "conversation"},
    }

    first = record_reasoning(tmp_path, event)
    second = record_reasoning(tmp_path, event)

    assert first["added"] is True
    assert second["added"] is False
    assert validate_contract(
        "reasoning-event", {key: value for key, value in first.items() if key != "added"}
    ) == []
    assert memory_summary(tmp_path)["counts"]["durable_reasoning_patterns"] == 1


def test_reasoning_retry_without_timestamps_is_idempotent(tmp_path: Path) -> None:
    event = {
        "actor": "human",
        "actor_basis": "direct",
        "context_type": "idea_discussion",
        "context_id": "retry-demo",
        "trigger": "The same observable decision is retried.",
        "thinking_moves": ["scope_narrowing"],
        "reasoning_summary": "Narrow the estimand before collecting more data.",
        "decision": "narrow",
        "alternatives_rejected": [],
        "transfer_rule": "",
        "durability": "candidate_specific",
        "human_confirmed": True,
        "profile_eligible": False,
        "source_refs": [],
        "provenance": {},
    }

    with patch(
        "research_core.memory.utc_now",
        side_effect=["2026-08-11T19:00:00Z", "2026-08-11T19:01:00Z"],
    ):
        first = record_reasoning(tmp_path, event)
        second = record_reasoning(tmp_path, event)

    assert first["reasoning_id"] == second["reasoning_id"]
    assert second["added"] is False


def test_endorsed_external_idea_pattern_preserves_authorship(tmp_path: Path) -> None:
    event = {
        "actor": "human",
        "actor_basis": "direct",
        "context_type": "paper_reading",
        "context_id": "paper-demo",
        "trigger": "The paper turns a familiar policy object into a strategic-choice variable.",
        "thinking_moves": ["source_pattern_recognition", "selective_adoption"],
        "reasoning_summary": "The learner endorsed the author's question-forming move.",
        "intellectual_origin": "external_exemplar",
        "source_pattern": "Reinterpret a formal compliance artifact as an endogenous strategic choice.",
        "endorsement_rationale": "It reveals a hidden behavioral margin in a familiar institution.",
        "transferable_element": "Ask which apparently passive administrative objects are chosen strategically.",
        "transfer_boundary": "Transfer the question-forming move, not the paper's topic or claim of originality.",
        "decision": "retain as an idea-generation exemplar",
        "alternatives_rejected": [],
        "transfer_rule": "Use endorsed external question-forming moves as attributed exemplars.",
        "durability": "repeated_pattern",
        "human_confirmed": True,
        "profile_eligible": True,
        "source_refs": [{"type": "paper", "paper_id": "paper-demo"}],
        "provenance": {"source": "paper_reading"},
    }

    result = record_reasoning(tmp_path, event)

    assert result["added"] is True
    assert result["intellectual_origin"] == "external_exemplar"
    assert result["source_refs"][0]["paper_id"] == "paper-demo"
    assert memory_summary(tmp_path)["counts"]["endorsed_external_exemplars"] == 1


def test_external_exemplar_requires_attribution_and_transfer_fields(tmp_path: Path) -> None:
    event = {
        "actor": "human",
        "actor_basis": "direct",
        "context_type": "paper_reading",
        "context_id": "paper-demo",
        "trigger": "Good author idea",
        "thinking_moves": ["source_pattern_recognition"],
        "reasoning_summary": "The learner likes it.",
        "intellectual_origin": "external_exemplar",
        "decision": "retain",
        "alternatives_rejected": [],
        "transfer_rule": "",
        "durability": "candidate_specific",
        "human_confirmed": True,
        "profile_eligible": False,
        "source_refs": [],
        "provenance": {},
    }

    with pytest.raises(ValueError, match="source_pattern"):
        record_reasoning(tmp_path, event)


def test_inferred_or_advisor_reasoning_cannot_become_taste(tmp_path: Path) -> None:
    event = {
        "actor": "advisor",
        "actor_basis": "researcher_reported",
        "context_type": "advisor_feedback",
        "context_id": "candidate-x",
        "trigger": "Advisor rejection",
        "thinking_moves": ["data_feasibility"],
        "reasoning_summary": "The data plan is too costly.",
        "decision": "reject",
        "alternatives_rejected": [],
        "transfer_rule": "",
        "durability": "candidate_specific",
        "human_confirmed": True,
        "profile_eligible": True,
        "source_refs": [],
        "provenance": {},
    }

    with pytest.raises(ValueError, match="direct, human"):
        record_reasoning(tmp_path, event)


def test_advisor_feedback_stays_in_feasibility_lane(tmp_path: Path) -> None:
    event = {
        "candidate_id": "candidate-phone-ban-enforcement-burden",
        "idea_slug": "school-phone-ban-enforcement-cost",
        "origin_run_id": "scout-20260720-pattern-refresh",
        "stage": "quick_scan",
        "rater": "advisor",
        "rater_basis": "researcher_reported",
        "decision": "delete",
        "axes": AXES,
        "rationale": "High-cost data collection with a long time to first signal.",
        "reason_codes": [
            "data_collection_cost",
            "time_to_signal",
            "salvage_value",
            "jmp_timeline",
            "advisor_fit",
        ],
        "revival_conditions": ["A ready linked dataset or a cheap pilot"],
        "confidence": 5,
        "human_confirmed": True,
        "profile_use": "feasibility_only",
        "source_refs": [],
        "provenance": {"source": "researcher_reported_advisor"},
    }

    result = record_idea_feedback(tmp_path, event)
    assert result["added"] is True
    assert memory_summary(tmp_path)["counts"]["advisor_outcomes"] == 1
    bad = dict(event, candidate_id="candidate-y", profile_use="taste")
    with pytest.raises(ValueError, match="taste feedback"):
        record_idea_feedback(tmp_path, bad)


def test_memory_cli_records_json_file(tmp_path: Path) -> None:
    from research_core.cli import main

    payload = {
        "actor": "human",
        "actor_basis": "direct",
        "context_type": "idea_discussion",
        "context_id": "demo",
        "trigger": "A proxy may not match the construct.",
        "thinking_moves": ["measurement_reframing"],
        "reasoning_summary": "Separate the proxy from the latent object.",
        "decision": "revise measurement",
        "alternatives_rejected": [],
        "transfer_rule": "Audit construct validity before causal interpretation.",
        "durability": "repeated_pattern",
        "human_confirmed": True,
        "profile_eligible": True,
        "source_refs": [],
        "provenance": {"source": "test"},
    }
    source = tmp_path / "event.json"
    source.write_text(json.dumps(payload), encoding="utf-8")
    assert main(["memory", "record-reasoning", str(source), "--idea-vault", str(tmp_path)]) == 0
    assert (tmp_path / "ideas" / "memory" / "reasoning-events.jsonl").exists()
