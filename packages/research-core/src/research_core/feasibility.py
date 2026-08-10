"""Deterministic checks for the two-week idea feasibility gate."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from .s2check import extract_section, parse_frontmatter, replace_frontmatter_fields
from .util import atomic_write_text, read_text, utc_now


REQUIRED_SECTIONS = (
    "Estimand",
    "Identification",
    "Data Access",
    "Minimum Viable Artifact",
    "Nearest-Paper Threat",
    "Two-Week Sprint Plan",
    "Human Decision",
)
PROTECTED_HUMAN_FIELDS = (
    "human_decision",
    "human_decision_by",
    "human_decision_date",
)
PLACEHOLDERS = ("[TODO]", "TBD", "TO BE DECIDED", "UNKNOWN")
GENERATED_READY_FIELDS = {
    "gate_status": "ready_for_human_decision",
    "ai_readiness": "READY_FOR_HUMAN_DECISION",
}


def _block(blockers: list[dict[str, str]], code: str, message: str, locator: str) -> None:
    blockers.append({"code": code, "message": message, "locator": locator})


def _substantive(section: str | None) -> bool:
    if not section:
        return False
    normalized = " ".join(section.split()).upper()
    return len(normalized) >= 30 and not any(marker in normalized for marker in PLACEHOLDERS)


def check_feasibility(sidecar_path: str | Path) -> dict[str, Any]:
    sidecar = Path(sidecar_path)
    text = read_text(sidecar)
    frontmatter, _, _ = parse_frontmatter(text)
    blockers: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    if frontmatter.get("gate_schema_version") not in {"1", "1.0"}:
        _block(blockers, "schema.unsupported", "Feasibility gate schema version 1 is required", "gate_schema_version")
    if not frontmatter.get("idea_slug"):
        _block(blockers, "idea.missing", "idea_slug is required", "idea_slug")

    for section_name in REQUIRED_SECTIONS:
        section = extract_section(text, section_name)
        if section is None:
            _block(blockers, "section.missing", f"Required section is missing: {section_name}", section_name)
        elif section_name != "Human Decision" and not _substantive(section):
            _block(blockers, "section.incomplete", f"Section is incomplete: {section_name}", section_name)

    access_status = frontmatter.get("data_access_status", "unknown").casefold()
    if access_status not in {"sample_acquired", "tested"}:
        _block(
            blockers,
            "data.not_acquired",
            "A named dataset plus an acquired/tested sample is required before the gate can be ready",
            "data_access_status",
        )

    artifact_value = frontmatter.get("minimum_artifact_path", "").strip()
    if not artifact_value:
        _block(blockers, "artifact.missing", "minimum_artifact_path is required", "minimum_artifact_path")
    else:
        artifact = Path(artifact_value)
        if not artifact.is_absolute():
            artifact = sidecar.parent / artifact
        if not artifact.exists():
            _block(blockers, "artifact.not_found", f"Minimum artifact does not exist: {artifact}", "minimum_artifact_path")

    sprint_started = frontmatter.get("sprint_started", "")
    deadline = frontmatter.get("sprint_deadline", "")
    if not sprint_started:
        _block(blockers, "sprint.start_missing", "A sprint start date is required", "sprint_started")
    if not deadline:
        _block(blockers, "deadline.missing", "A two-week sprint deadline is required", "sprint_deadline")
    elif sprint_started:
        try:
            parsed_start = date.fromisoformat(sprint_started)
            parsed_deadline = date.fromisoformat(deadline)
            sprint_days = (parsed_deadline - parsed_start).days
            if not 1 <= sprint_days <= 14:
                _block(
                    blockers,
                    "deadline.outside_window",
                    "Sprint deadline must be 1-14 days after sprint_started",
                    "sprint_deadline",
                )
            if parsed_deadline < date.today() and frontmatter.get("human_decision", "pending") == "pending":
                warnings.append(
                    {
                        "code": "deadline.overdue",
                        "message": f"Sprint deadline passed on {deadline}; make a continue/pivot/kill decision",
                        "locator": "sprint_deadline",
                    }
                )
        except ValueError:
            _block(
                blockers,
                "deadline.invalid",
                f"Invalid sprint date range: {sprint_started} to {deadline}",
                "sprint_deadline",
            )

    decision = frontmatter.get("human_decision", "pending")
    if decision not in {"pending", "continue", "pivot", "kill"}:
        _block(blockers, "decision.invalid", f"Unsupported human_decision: {decision}", "human_decision")
    if decision != "pending" and (
        not frontmatter.get("human_decision_by") or not frontmatter.get("human_decision_date")
    ):
        _block(blockers, "decision.incomplete", "Human decision needs actor and date", "human_decision")

    ready = not blockers
    return {
        "schema_version": "1.0",
        "sidecar": str(sidecar.resolve()),
        "checked_at": utc_now(),
        "ready": ready,
        "blockers": blockers,
        "warnings": warnings,
        "protected_human_fields": {
            field: frontmatter.get(field) for field in PROTECTED_HUMAN_FIELDS
        },
        "proposed_generated_fields": GENERATED_READY_FIELDS if ready else {},
    }


def apply_ready(sidecar_path: str | Path, report: dict[str, Any] | None = None) -> dict[str, Any]:
    sidecar = Path(sidecar_path)
    report = report or check_feasibility(sidecar)
    if not report["ready"]:
        raise ValueError("Feasibility gate is not ready; refusing generated-field update")
    original = read_text(sidecar)
    before, _, _ = parse_frontmatter(original)
    human_before = {field: before.get(field) for field in PROTECTED_HUMAN_FIELDS}
    replacements = dict(GENERATED_READY_FIELDS)
    replacements["readiness_checked_at"] = utc_now()
    updated = replace_frontmatter_fields(original, replacements)
    after, _, _ = parse_frontmatter(updated)
    human_after = {field: after.get(field) for field in PROTECTED_HUMAN_FIELDS}
    if human_before != human_after:
        raise RuntimeError("Protected human fields changed; update aborted")
    atomic_write_text(sidecar, updated)
    return check_feasibility(sidecar)
