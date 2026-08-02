"""Public-only OpenAlex discovery adapter for broad economics scouting."""

from __future__ import annotations

import datetime as dt
import os
from typing import Any, Callable, Mapping, Sequence

import requests

from scout_core import OPENALEX_JOURNAL_SOURCES, PUBLIC_SCOPE_TERMS, deduplicate_papers
from tracker_core import SourceHealthReport, request_with_retry


OPENALEX_URL = "https://api.openalex.org/works"


def _window_start(as_of: dt.date, months: int) -> dt.date:
    if months <= 0:
        raise ValueError("months must be positive")
    return as_of - dt.timedelta(days=months * 30)


def _abstract(item: Mapping[str, Any]) -> str:
    inverted = item.get("abstract_inverted_index") or {}
    positions: dict[int, str] = {}
    if isinstance(inverted, dict):
        for word, indexes in inverted.items():
            if isinstance(indexes, list):
                for index in indexes:
                    if isinstance(index, int) and index < 800:
                        positions[index] = str(word)
    return " ".join(positions[index] for index in sorted(positions))


def _paper(item: Mapping[str, Any], *, venue: str, pack: str) -> dict[str, Any]:
    ids = item.get("ids") or {}
    primary = item.get("primary_location") or {}
    source = primary.get("source") or {}
    abstract = _abstract(item)
    return {
        "title": str(item.get("title") or ""),
        "authors": ", ".join(
            str((entry.get("author") or {}).get("display_name") or "")
            for entry in (item.get("authorships") or [])[:8]
            if isinstance(entry, dict)
        ),
        "published": str(item.get("publication_date") or item.get("publication_year") or ""),
        "venue": str(source.get("display_name") or venue),
        "source_family": f"openalex:{pack}",
        "url": str(ids.get("doi") or ids.get("openalex") or item.get("id") or ""),
        "abstract": abstract,
        "evidence_level": "abstract" if abstract else "title_only",
        "cluster": "unclustered",
        "doi": str(ids.get("doi") or ""),
        "openalex_id": str(item.get("id") or ids.get("openalex") or ""),
    }


def discover_openalex(
    scopes: Sequence[str],
    *,
    as_of: str | None = None,
    journal_months: int = 24,
    per_query: int = 25,
    request_func: Callable[..., Any] = requests.get,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Fetch public journal records using only allowlisted scope primitives.

    Personal profile text cannot enter this interface: callers supply only
    enumerated scope names, and search terms come from PUBLIC_SCOPE_TERMS.
    """

    normalized_scopes = list(dict.fromkeys(str(scope).casefold() for scope in scopes))
    unknown = sorted(set(normalized_scopes) - set(PUBLIC_SCOPE_TERMS))
    if unknown:
        raise ValueError(f"Unsupported public scout scope(s): {', '.join(unknown)}")
    if not normalized_scopes:
        raise ValueError("At least one public scout scope is required")
    end = dt.date.fromisoformat(as_of) if as_of else dt.date.today()
    start = _window_start(end, journal_months)
    packs = ["econ_top5", "labor_field"]
    if "education" in normalized_scopes:
        packs.append("education_field")
    if "econometrics" in normalized_scopes:
        packs.append("econometrics_methods")
    if any(scope in {"meta_analysis", "metascience"} for scope in normalized_scopes):
        packs.append("evidence_synthesis")
    terms = list(dict.fromkeys(
        term for scope in normalized_scopes for term in PUBLIC_SCOPE_TERMS[scope]
    ))
    key = api_key if api_key is not None else os.environ.get("OPENALEX_API_KEY", "")
    health = SourceHealthReport(run_date=end.isoformat())
    raw_papers: list[dict[str, Any]] = []
    public_queries: list[str] = []

    for pack in dict.fromkeys(packs):
        for venue, issn_l in OPENALEX_JOURNAL_SOURCES[pack]:
            before = len(raw_papers)
            try:
                for term in terms:
                    public_queries.append(
                        f"OpenAlex venue_issn={issn_l} from={start.isoformat()} "
                        f"to={end.isoformat()} search={term}"
                    )
                    params = {
                        "filter": (
                            f"primary_location.source.issn:{issn_l},"
                            f"from_publication_date:{start.isoformat()},"
                            f"to_publication_date:{end.isoformat()}"
                        ),
                        "search": term,
                        "sort": "publication_date:desc",
                        "per-page": max(1, min(100, per_query)),
                        "select": (
                            "id,ids,title,publication_date,publication_year,"
                            "primary_location,authorships,abstract_inverted_index"
                        ),
                    }
                    if key:
                        params["api_key"] = key
                    response = request_with_retry(
                        "openalex",
                        OPENALEX_URL,
                        request_func=request_func,
                        params=params,
                        timeout=30,
                        headers={"User-Agent": "ai-research-tools-idea-scout/3.2"},
                    )
                    data = response.json()
                    raw_papers.extend(
                        _paper(item, venue=venue, pack=pack)
                        for item in data.get("results", [])
                        if isinstance(item, dict) and item.get("title")
                    )
                health.success(f"openalex:{venue}", len(raw_papers) - before, core=pack in {"econ_top5", "labor_field"})
            except Exception as exc:  # SourceHealthReport records a redacted summary.
                health.failure(f"openalex:{venue}", exc, core=pack in {"econ_top5", "labor_field"})
    health.finalize(failure_threshold=2)
    papers = deduplicate_papers(raw_papers)
    return {
        "as_of": end.isoformat(),
        "journal_months": journal_months,
        "scopes": normalized_scopes,
        "queries": public_queries,
        "source_health": {
            "status": health.status,
            "sources": health.sources,
            "errors": health.errors,
        },
        "papers": [
            {
                "paper_id": item.paper_id,
                "title": item.title,
                "authors": item.authors,
                "published": item.published,
                "venue": item.venue,
                "source_family": item.source_family,
                "url": item.url,
                "abstract": item.abstract,
                "evidence_level": item.evidence_level,
                "cluster": item.cluster,
                "identifiers": item.identifiers,
                "suspected_version_of": item.suspected_version_of,
            }
            for item in papers
        ],
    }
