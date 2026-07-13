"""Deterministic S2 readiness checks with tightly bounded optional mutation."""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

from .util import atomic_write_text, read_text, stable_hash, utc_now


HUMAN_FIELDS = (
    "scope_approved_by",
    "scope_approved_date",
    "human_gap_status",
    "human_decision",
    "human_decision_by",
    "human_decision_date",
)

GENERATED_READY_FIELDS = {
    "ai_readiness": "READY_FOR_HUMAN_DECISION",
    "gate_status": "ready_for_human_decision",
    "gate_phase": "adjudication",
}

REQUIRED_SECTIONS = (
    "Frozen S1 Original",
    "PKB-A Context Recall",
    "Human-Approved Scope Card",
    "PKB-B Local Evidence Search",
    "Search Protocol and Coverage Matrix",
    "Append-Only Search Log",
    "Candidate, Version, and Screening Ledger",
    "Human Reading Queue and Evidence Table",
    "Typed Relationship Ledger",
    "Synthesis Claim Ledger",
    "Integrated Literature Review",
    "Nearest-Neighbor Matrix",
    "Already-Done Memo",
    "Researchability / Exogenous-Shock / Data-Path Triage",
    "Stopping and Readiness Certificate",
    "Human Gate Decision",
    "Decision / Invalidation History",
)


def parse_frontmatter(text: str) -> tuple[dict[str, str], int, int]:
    lines = text.lstrip("\ufeff").splitlines()
    delimiters = [index for index, line in enumerate(lines[:100]) if line.strip() == "---"]
    if len(delimiters) < 2:
        return {}, -1, -1
    start, end = delimiters[0], delimiters[1]
    values: dict[str, str] = {}
    for line in lines[start + 1:end]:
        if ":" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split(":", 1)
        value = re.sub(r"\s+#.*$", "", value).strip().strip('"\'')
        values[key.strip()] = value
    return values, start, end


def extract_section(text: str, title: str) -> str | None:
    lines = text.splitlines()
    start: int | None = None
    level = 0
    for index, line in enumerate(lines):
        match = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
        if match and title.casefold() in match.group(2).casefold():
            start, level = index + 1, len(match.group(1))
            break
    if start is None:
        return None
    end = len(lines)
    for index in range(start, len(lines)):
        match = re.match(r"^(#{1,6})\s+", lines[index].strip())
        if match and len(match.group(1)) <= level:
            end = index
            break
    return "\n".join(lines[start:end]).strip()


def compute_scope_hash(text: str) -> str | None:
    scope = extract_section(text, "Human-Approved Scope Card") or extract_section(text, "Scope Card")
    if not scope:
        return None
    normalized_lines = []
    for line in scope.splitlines():
        stripped = re.sub(r"\s+", " ", line.strip())
        if stripped:
            normalized_lines.append(stripped)
    return stable_hash({"scope_card": "\n".join(normalized_lines)})


def _table_rows(section: str | None) -> list[list[str]]:
    if not section:
        return []
    rows: list[list[str]] = []
    for line in section.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells or all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        rows.append(cells)
    return rows


def _truthy(value: str) -> bool:
    return value.strip().casefold() in {"true", "yes", "1", "y"}


def _block(blockers: list[dict[str, str]], code: str, message: str, locator: str) -> None:
    if not any(item["code"] == code and item["locator"] == locator for item in blockers):
        blockers.append({"code": code, "message": message, "locator": locator})


def _check_routes(text: str, blockers: list[dict[str, str]]) -> None:
    section = extract_section(text, "Search Protocol and Coverage Matrix")
    rows = _table_rows(section)
    for cells in rows[1:]:
        if len(cells) < 7:
            continue
        route, required, status, waiver = cells[0], cells[4].casefold(), cells[5].casefold(), cells[6].casefold()
        is_required = required == "yes" or required.startswith("yes for")
        if not is_required:
            continue
        complete = any(marker in status for marker in ("complete", "done", "closed", "waived"))
        waived = "waiv" in waiver and len(waiver) > 6
        if not complete and not waived:
            _block(blockers, "route.incomplete", f"Required search route is incomplete: {route}", route)


def _check_known_item_recall(text: str, blockers: list[dict[str, str]]) -> None:
    section = extract_section(text, "Known-Item Recall Test")
    if not section:
        _block(blockers, "known_item.missing", "Known-item recall section is missing", "Known-Item Recall Test")
        return
    match = re.search(r"Human recall check\s*:\s*(.+)", section, flags=re.I)
    if not match:
        _block(blockers, "known_item.unresolved", "Known-item recall has no human result", "Known-Item Recall Test")
        return
    result = match.group(1).strip().casefold()
    if result.startswith("pass") or ("waiv" in result and "reason" not in result):
        return
    _block(blockers, "known_item.failed", "Known-item recall did not pass or receive a reasoned waiver", "Known-Item Recall Test")


def _check_reading_queue(text: str, blockers: list[dict[str, str]]) -> None:
    section = extract_section(text, "Human Reading Queue")
    for cells in _table_rows(section)[1:]:
        if len(cells) < 5:
            continue
        row = " | ".join(cells).casefold()
        status = cells[3].casefold()
        high_threat = "must-read" in row or "high-threat" in row or "high threat" in row or "nearest threat" in row
        unread = not any(marker in status for marker in ("read", "verified", "complete", "waived")) or any(
            marker in status for marker in ("unread", "pending", "not read")
        )
        if high_threat and unread:
            _block(blockers, "reading.unread_high_threat", f"Unread high-threat item: {cells[0]}", cells[0])


def _check_evidence(text: str, blockers: list[dict[str, str]]) -> None:
    section = extract_section(text, "Field-Level Evidence Table")
    for cells in _table_rows(section)[1:]:
        if len(cells) < 10:
            continue
        row = " | ".join(cells).casefold()
        source_level = cells[5].casefold()
        locator = cells[6].strip()
        human_verified = cells[8].casefold()
        decisive = "decisive" in row or "nearest" in row or "novelty" in row
        if decisive and source_level in {"metadata", "abstract"}:
            _block(blockers, "evidence.abstract_only_decisive", f"Decisive claim is only {source_level}: {cells[0]}", cells[0])
        if decisive and (not locator or locator.casefold() in {"nr", "unknown", "n/a"}):
            _block(blockers, "evidence.missing_locator", f"Decisive claim lacks a locator: {cells[0]}", cells[0])
        if decisive and human_verified not in {"yes", "true", "verified", "waived"}:
            _block(blockers, "evidence.not_human_verified", f"Decisive claim lacks human verification: {cells[0]}", cells[0])


def _check_versions(text: str, blockers: list[dict[str, str]]) -> None:
    section = extract_section(text, "Work Family / Manifestation Ledger")
    for cells in _table_rows(section)[1:]:
        row = " | ".join(cells).casefold()
        if "version-conflict" in row or "version conflict" in row:
            if not any(marker in row for marker in ("resolved", "confirmed", "not material", "waived")):
                label = cells[0] if cells else "version row"
                _block(blockers, "version.unresolved_conflict", f"Unresolved version conflict: {label}", label)


def _check_certificate(text: str, blockers: list[dict[str, str]]) -> tuple[int, int]:
    section = extract_section(text, "Stopping and Readiness Certificate")
    if not section:
        _block(blockers, "certificate.missing", "Stopping and Readiness Certificate is missing", "certificate")
        return 0, 0
    items = re.findall(r"^-\s*\[([ xX])\]\s*(.+)$", section, flags=re.M)
    for mark, description in items:
        if mark.casefold() != "x":
            _block(blockers, "certificate.unchecked", f"Unchecked readiness item: {description}", description)
    return sum(mark.casefold() == "x" for mark, _ in items), len(items)


def _check_human_fields(frontmatter: dict[str, str], blockers: list[dict[str, str]]) -> None:
    decision = frontmatter.get("human_decision", "pending")
    if decision not in {"", "pending", "null", "none"}:
        if not frontmatter.get("human_decision_by") or not frontmatter.get("human_decision_date"):
            _block(blockers, "human_fields.incomplete_decision", "Human decision lacks actor or date", "frontmatter")
    if frontmatter.get("scope_approved_by") and not frontmatter.get("scope_approved_date"):
        _block(blockers, "human_fields.incomplete_scope_approval", "Scope approval lacks a date", "frontmatter")


def _check_cache_conflict(frontmatter: dict[str, str], idea_path: Path | None, blockers: list[dict[str, str]]) -> None:
    if idea_path is None or not idea_path.exists():
        return
    idea_frontmatter, _, _ = parse_frontmatter(read_text(idea_path))
    idea_decision = idea_frontmatter.get("s2_gate_outcome")
    gate_decision = frontmatter.get("human_decision")
    if idea_decision and gate_decision and idea_decision not in {"null", "none"} and idea_decision != gate_decision:
        _block(blockers, "cache.conflict", "Idea cache and gate human decision disagree", str(idea_path))


def check_s2(sidecar_path: str | Path, *, idea_path: str | Path | None = None) -> dict[str, Any]:
    sidecar_path = Path(sidecar_path)
    text = read_text(sidecar_path)
    frontmatter, _, _ = parse_frontmatter(text)
    blockers: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    if not frontmatter:
        _block(blockers, "frontmatter.missing", "No YAML-like frontmatter found", "frontmatter")
    if frontmatter.get("gate_schema_version") not in {"2", "2.0"}:
        _block(blockers, "schema.unsupported", "Gate schema version 2 is required", "gate_schema_version")
    if _truthy(frontmatter.get("gate_dirty", "false")):
        _block(blockers, "gate.dirty", f"Gate is dirty: {frontmatter.get('dirty_reasons', '')}", "gate_dirty")

    for required in REQUIRED_SECTIONS:
        if extract_section(text, required) is None:
            _block(blockers, "section.missing", f"Required section is missing: {required}", required)

    computed_scope_hash = compute_scope_hash(text)
    recorded_scope_hash = frontmatter.get("scope_hash")
    if not recorded_scope_hash:
        _block(blockers, "scope.hash_missing", "scope_hash is missing", "scope_hash")
    elif computed_scope_hash and recorded_scope_hash != computed_scope_hash:
        _block(blockers, "scope.hash_mismatch", "Recorded scope_hash does not match the Scope Card", "scope_hash")

    refresh_due = frontmatter.get("refresh_due")
    if refresh_due:
        try:
            if date.fromisoformat(refresh_due) < date.today():
                _block(blockers, "gate.stale", f"Search refresh was due on {refresh_due}", "refresh_due")
        except ValueError:
            _block(blockers, "gate.invalid_refresh_date", f"Invalid refresh_due date: {refresh_due}", "refresh_due")

    _check_routes(text, blockers)
    _check_known_item_recall(text, blockers)
    _check_reading_queue(text, blockers)
    _check_evidence(text, blockers)
    _check_versions(text, blockers)
    checked, total = _check_certificate(text, blockers)
    _check_human_fields(frontmatter, blockers)

    derived_idea_path: Path | None
    if idea_path is not None:
        derived_idea_path = Path(idea_path)
    elif sidecar_path.parent.name == "reviews":
        slug = frontmatter.get("idea_slug") or sidecar_path.stem.removesuffix("-s2-gate")
        derived_idea_path = sidecar_path.parent.parent / f"{slug}.md"
    else:
        derived_idea_path = None
    _check_cache_conflict(frontmatter, derived_idea_path, blockers)

    ready = not blockers
    return {
        "schema_version": "1.0",
        "sidecar": str(sidecar_path.resolve()),
        "checked_at": utc_now(),
        "ready": ready,
        "computed_scope_hash": computed_scope_hash,
        "recorded_scope_hash": recorded_scope_hash,
        "certificate": {"checked": checked, "total": total},
        "blockers": blockers,
        "warnings": warnings,
        "protected_human_fields": {field: frontmatter.get(field) for field in HUMAN_FIELDS},
        "proposed_generated_fields": GENERATED_READY_FIELDS if ready else {},
    }


def _replace_frontmatter_fields(text: str, replacements: dict[str, str]) -> str:
    lines = text.lstrip("\ufeff").splitlines()
    delimiters = [index for index, line in enumerate(lines[:100]) if line.strip() == "---"]
    if len(delimiters) < 2:
        raise ValueError("Cannot update a sidecar without frontmatter")
    start, end = delimiters[0], delimiters[1]
    remaining = dict(replacements)
    for index in range(start + 1, end):
        if ":" not in lines[index] or lines[index].lstrip().startswith("#"):
            continue
        key = lines[index].split(":", 1)[0].strip()
        if key in remaining:
            comment = ""
            original_value = lines[index].split(":", 1)[1]
            if "#" in original_value:
                comment = "  #" + original_value.split("#", 1)[1]
            lines[index] = f"{key}: {remaining.pop(key)}{comment}"
    for key, value in remaining.items():
        lines.insert(end, f"{key}: {value}")
        end += 1
    return "\n".join(lines) + "\n"


def apply_ready(sidecar_path: str | Path, report: dict[str, Any] | None = None) -> dict[str, Any]:
    sidecar_path = Path(sidecar_path)
    report = report or check_s2(sidecar_path)
    if not report["ready"]:
        raise ValueError("S2 gate is not ready; refusing to update generated readiness fields")
    original = read_text(sidecar_path)
    before, _, _ = parse_frontmatter(original)
    human_before = {field: before.get(field) for field in HUMAN_FIELDS}
    replacements = dict(GENERATED_READY_FIELDS)
    replacements["readiness_checked_at"] = utc_now()
    updated = _replace_frontmatter_fields(original, replacements)
    after, _, _ = parse_frontmatter(updated)
    human_after = {field: after.get(field) for field in HUMAN_FIELDS}
    if human_before != human_after:
        raise RuntimeError("Protected human fields changed; update aborted")
    atomic_write_text(sidecar_path, updated)
    return check_s2(sidecar_path)
