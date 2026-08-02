"""Deterministic provenance rules for research ideas and profile feedback."""

from __future__ import annotations

from typing import Any


IDEA_ORIGINS = ("human", "hybrid", "ai_generated")
LEGACY_ORIGIN = "legacy_unclassified"
ADVANCE_OUTCOME = "ADVANCE-S3"


def normalize_idea_origin(value: str | None) -> str:
    """Return the canonical origin, preserving missing legacy provenance."""

    if value is None or not str(value).strip():
        return LEGACY_ORIGIN
    normalized = str(value).strip().casefold().replace("-", "_")
    if normalized == LEGACY_ORIGIN:
        return LEGACY_ORIGIN
    if normalized not in IDEA_ORIGINS:
        raise ValueError(
            f"Unknown idea_origin {value!r}; expected one of {', '.join(IDEA_ORIGINS)}"
        )
    return normalized


def assert_origin_unchanged(previous: str | None, current: str | None) -> str:
    """Validate the immutable origin contract and return the canonical value."""

    before = normalize_idea_origin(previous)
    after = normalize_idea_origin(current)
    if before != after:
        raise ValueError(f"idea_origin is immutable: {before!r} -> {after!r}")
    return after


def idea_profile_eligible(
    idea_origin: str | None,
    *,
    s2_gate_outcome: str | None,
    signal_type: str,
) -> bool:
    """Whether an idea-derived signal may influence researcher personalization.

    Human, hybrid, and legacy ideas retain the existing projector behavior.
    AI-generated ideas are quarantined until the authoritative S2 outcome is
    ADVANCE-S3, and then only a portfolio signal may enter the feedback loop.
    """

    origin = normalize_idea_origin(idea_origin)
    if origin != "ai_generated":
        return True
    return s2_gate_outcome == ADVANCE_OUTCOME and signal_type == "portfolio"


def annotate_profile_signal(
    signal: dict[str, Any],
    *,
    idea_origin: str | None,
    s2_gate_outcome: str | None,
    origin_run_id: str | None = None,
    origin_candidate_id: str | None = None,
) -> dict[str, Any]:
    """Attach provenance and apply the AI-feedback quarantine to one signal."""

    result = dict(signal)
    origin = normalize_idea_origin(idea_origin)
    result["idea_origin"] = origin
    result["s2_gate_outcome"] = s2_gate_outcome
    result["origin_run_id"] = origin_run_id
    result["origin_candidate_id"] = origin_candidate_id
    eligible = idea_profile_eligible(
        origin,
        s2_gate_outcome=s2_gate_outcome,
        signal_type=str(result.get("signal_type", "")),
    )
    result["profile_eligible"] = eligible
    if not eligible:
        result["human_approved"] = False
        result["retrieval_terms"] = []
    return result
