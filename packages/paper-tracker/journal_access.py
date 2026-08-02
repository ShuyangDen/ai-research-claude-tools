#!/usr/bin/env python3
"""Validate ranked economics journals and probe recent abstract availability.

The catalog is a retrieval prior, not a claim that every paper in a ranked
journal is strong.  A journal is eligible for default scouting only after a
dated probe demonstrates access to at least one recent abstract or to a
confirmed working-paper/version abstract.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import requests
import yaml


VERIFIED_ACCESS = {"verified_primary", "verified_fallback", "verified_version_abstract"}
FIELD_MULTIPLIERS = {
    "labor": 1.20,
    "education": 1.20,
    "econometrics": 1.10,
    "meta_analysis": 1.05,
    "metascience": 1.05,
    "general": 1.00,
}


def load_registry(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("Journal registry must be a YAML object")
    return value


def _date(value: str) -> dt.date:
    try:
        return dt.date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(f"Invalid ISO date in journal registry: {value}") from exc


def validate_registry(
    registry: Mapping[str, Any],
    *,
    as_of: dt.date,
    max_age_days: int | None = None,
) -> dict[str, Any]:
    policy = dict(registry.get("abstract_access_policy", {}))
    freshness = int(max_age_days or policy.get("freshness_days", 180))
    journals = list(registry.get("journals", []))
    if not journals:
        raise ValueError("Journal registry has no journals")
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for journal in journals:
        journal_id = str(journal.get("journal_id", ""))
        if not journal_id or journal_id in seen:
            raise ValueError(f"Missing or duplicate journal_id: {journal_id}")
        seen.add(journal_id)
        rank_weight = float(journal.get("rank_weight", 0))
        if not 0 < rank_weight <= 1:
            raise ValueError(f"Journal {journal_id} has invalid rank_weight")
        access = dict(journal.get("abstract_access", {}))
        checked = _date(str(access.get("checked_at", "")))
        age_days = (as_of - checked).days
        status = str(access.get("status", ""))
        verified = (
            status in VERIFIED_ACCESS
            and bool(access.get("route"))
            and bool(access.get("sample_title"))
            and age_days >= 0
            and age_days <= freshness
        )
        enabled = bool(journal.get("enabled_by_default", False))
        if enabled and not verified:
            failures.append(journal_id)
        rows.append({
            "journal_id": journal_id,
            "enabled_by_default": enabled,
            "abstract_verified": verified,
            "status": status,
            "age_days": age_days,
        })
    if failures:
        raise ValueError(
            "Default scout journals lack a fresh verified abstract route: "
            + ", ".join(failures)
        )
    return {
        "journal_count": len(rows),
        "enabled_count": sum(row["enabled_by_default"] for row in rows),
        "verified_count": sum(row["abstract_verified"] for row in rows),
        "rows": rows,
    }


def eligible_journals(
    registry: Mapping[str, Any],
    *,
    fields: Sequence[str],
    as_of: dt.date,
) -> list[dict[str, Any]]:
    validate_registry(registry, as_of=as_of)
    requested = {str(field).casefold() for field in fields}
    rows = []
    for journal in registry["journals"]:
        tags = {str(tag).casefold() for tag in journal.get("field_tags", [])}
        access = journal["abstract_access"]
        if not journal.get("enabled_by_default") or not (tags & requested or "general" in tags):
            continue
        multiplier = max(
            (FIELD_MULTIPLIERS.get(tag, 1.0) for tag in tags & requested),
            default=1.0,
        )
        row = dict(journal)
        row["retrieval_priority_score"] = round(float(journal["rank_weight"]) * multiplier, 4)
        row["abstract_access"] = dict(access)
        rows.append(row)
    return sorted(rows, key=lambda item: (-item["retrieval_priority_score"], item["journal_id"]))


def _clean_abstract(value: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", " ", value or "").split())


def probe_crossref(
    issn: str,
    *,
    from_date: str,
    rows: int = 20,
    request_func: Callable[..., Any] = requests.get,
) -> dict[str, Any]:
    """Probe a public Crossref route; callers persist reviewed results separately."""

    url = f"https://api.crossref.org/journals/{issn}/works"
    response = request_func(
        url,
        params={
            "filter": f"from-pub-date:{from_date}",
            "sort": "published",
            "order": "desc",
            "rows": max(1, min(rows, 100)),
            "select": "DOI,title,abstract,published,URL",
        },
        timeout=30,
        headers={"User-Agent": "ai-research-tools-journal-audit/3.2"},
    )
    response.raise_for_status()
    items = list((response.json().get("message") or {}).get("items") or [])
    sample = next((item for item in items if _clean_abstract(str(item.get("abstract", "")))), None)
    return {
        "issn": issn,
        "connected": True,
        "records_checked": len(items),
        "abstract_found": sample is not None,
        "sample_doi": str(sample.get("DOI", "")) if sample else None,
        "sample_title": str((sample.get("title") or [""])[0]) if sample else None,
        "route": "crossref",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ranked economics journal access audit")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("registry", type=Path)
    validate.add_argument("--as-of", required=True)
    plan = sub.add_parser("plan")
    plan.add_argument("registry", type=Path)
    plan.add_argument("--field", action="append", required=True)
    plan.add_argument("--as-of", required=True)
    probe = sub.add_parser("probe-crossref")
    probe.add_argument("issn")
    probe.add_argument("--from-date", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "probe-crossref":
        result = probe_crossref(args.issn, from_date=args.from_date)
    else:
        registry = load_registry(args.registry)
        as_of = dt.date.fromisoformat(args.as_of)
        if args.command == "validate":
            result = validate_registry(registry, as_of=as_of)
        else:
            result = {"journals": eligible_journals(registry, fields=args.field, as_of=as_of)}
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
