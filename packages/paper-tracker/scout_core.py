"""Deterministic, privacy-bounded primitives for broad economics idea scouting.

This module deliberately performs no model calls and no network requests.  The
idea-scout workflow supplies public search results; this module validates,
deduplicates, classifies, and serializes them without changing the weekly AI
paper tracker.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import json
import re
from collections import Counter
from typing import Any, Iterable, Mapping, Sequence

from tracker_core import normalize_title, stable_paper_id


IDEA_ORIGIN = "ai_generated"
DEFAULT_JOURNAL_MONTHS = 24
DEFAULT_WORKING_PAPER_MONTHS = 12
DEFAULT_CANDIDATES = 6
MAX_CANDIDATES = 8
MIN_HOTSPOT_PAPERS = 3
MIN_HOTSPOT_SOURCE_BREADTH = 2
MIN_WEIGHTED_HOTSPOT_ATTENTION = 1.6

DEFAULT_SOURCE_POLICY: dict[str, Any] = {
    "priority_retrieval_target_share": 0.8,
    "candidate_priority_min_share": 0.7,
    "candidate_per_item_priority_min_share": 0.5,
    "hotspot_excludes_open_discovery": True,
    "openalex_role": "discovery_index_only",
    "arxiv_role": "supplemental_low_prior",
    "abstract_access_required": True,
    "journal_rank_role": "retrieval_and_attention_prior_not_novelty",
    "weighted_hotspot_attention_min": MIN_WEIGHTED_HOTSPOT_ATTENTION,
    "separate_attention_from_entry_opportunity": True,
}

DEFAULT_TOPIC_BUDGET: dict[str, float] = {
    "labor": 0.35,
    "education": 0.35,
    "econometrics": 0.15,
    "meta_analysis": 0.15,
}

SOURCE_PACKS: dict[str, tuple[str, ...]] = {
    "econ_top5": (
        "American Economic Review",
        "Econometrica",
        "Journal of Political Economy",
        "Quarterly Journal of Economics",
        "Review of Economic Studies",
    ),
    "labor_field": (
        "Journal of Labor Economics",
        "Journal of Human Resources",
        "ILR Review",
        "Labour Economics",
    ),
    "education_field": (
        "Economics of Education Review",
        "Education Finance and Policy",
        "Journal of Human Resources",
    ),
    "econometrics_methods": (
        "Econometrica",
        "Journal of Econometrics",
        "Quantitative Economics",
        "Journal of Applied Econometrics",
        "Econometric Theory",
        "The Econometrics Journal",
        "Oxford Bulletin of Economics and Statistics",
    ),
    "evidence_synthesis": (
        "Journal of Economic Literature",
        "Journal of Economic Perspectives",
        "Annual Review of Economics",
        "Journal of Economic Surveys",
    ),
    "frontier_working_papers": (
        "NBER Labor Studies",
        "NBER Education",
        "IZA Discussion Papers",
        "CEPR Discussion Papers",
    ),
    "metascience_registries": (
        "AEA RCT Registry",
        "OSF Registries",
    ),
}

BLOCKED_DEFAULT_SOURCES: dict[str, str] = {
    "Journal of Business & Economic Statistics": "abstract_access_not_verified_2026-07-20",
}

# ISSN-L values make venue filtering auditable and avoid name/alias matches.
OPENALEX_JOURNAL_SOURCES: dict[str, tuple[tuple[str, str], ...]] = {
    "econ_top5": (
        ("American Economic Review", "0002-8282"),
        ("Econometrica", "0012-9682"),
        ("Journal of Political Economy", "0022-3808"),
        ("Quarterly Journal of Economics", "0033-5533"),
        ("Review of Economic Studies", "0034-6527"),
    ),
    "labor_field": (
        ("Journal of Labor Economics", "0734-306X"),
        ("Journal of Human Resources", "0022-166X"),
        ("ILR Review", "0019-7939"),
        ("Labour Economics", "0927-5371"),
    ),
    "education_field": (
        ("Economics of Education Review", "0272-7757"),
        ("Education Finance and Policy", "1557-3060"),
        ("Journal of Human Resources", "0022-166X"),
    ),
    "econometrics_methods": (
        ("Econometrica", "0012-9682"),
        ("Journal of Econometrics", "0304-4076"),
        ("Quantitative Economics", "1759-7323"),
        ("Journal of Applied Econometrics", "0883-7252"),
        ("Econometric Theory", "0266-4666"),
        ("The Econometrics Journal", "1368-4221"),
        ("Oxford Bulletin of Economics and Statistics", "0305-9049"),
    ),
    "evidence_synthesis": (
        ("Journal of Economic Literature", "0022-0515"),
        ("Journal of Economic Perspectives", "0895-3309"),
        ("Annual Review of Economics", "1941-1383"),
        ("Journal of Economic Surveys", "0950-0804"),
    ),
}

PUBLIC_SCOPE_TERMS: dict[str, tuple[str, ...]] = {
    "labor": (
        "labor economics", "human capital", "career", "occupation", "worker", "manager",
    ),
    "education": (
        "education economics", "college major", "student beliefs", "school", "credential",
    ),
    "metascience": (
        "economics metascience", "preregistration", "publication bias", "selective reporting",
    ),
    "econometrics": (
        "econometrics", "causal inference", "identification", "estimation", "measurement",
    ),
    "meta_analysis": (
        "meta-analysis", "systematic review", "evidence synthesis", "publication bias",
    ),
}

_EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
_WINDOWS_PATH_RE = re.compile(r"\b[A-Z]:[\\/]", re.IGNORECASE)
_PRIVATE_MARKERS = (
    "researcher_profile",
    "machine_paths",
    "personal knowledge skill",
    "jmp-idea-pipeline",
    "origin_candidate_id",
)


def stable_json_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def pattern_card_hash(card: Mapping[str, Any] | str) -> str:
    """Hash the locally approved style card without exposing its contents."""

    value: Any = card.strip() if isinstance(card, str) else dict(card)
    return stable_json_hash(value)


def validate_public_query(query: str, *, forbidden_fragments: Iterable[str] = ()) -> str:
    """Reject query strings that look like private profile text or local paths."""

    compact = " ".join(str(query).split())
    lowered = compact.casefold()
    forbidden = [*_PRIVATE_MARKERS, *(str(item).casefold() for item in forbidden_fragments)]
    if not compact:
        raise ValueError("Scout search query cannot be empty")
    if _EMAIL_RE.search(compact) or _WINDOWS_PATH_RE.search(compact):
        raise ValueError("Scout search queries must not contain email addresses or local paths")
    marker = next((item for item in forbidden if item and item in lowered), None)
    if marker:
        raise ValueError(f"Scout search query contains private marker: {marker}")
    return compact


def source_plan(
    scope: Sequence[str] | None = None,
    *,
    as_of: str | None = None,
    journal_months: int = DEFAULT_JOURNAL_MONTHS,
    working_paper_months: int = DEFAULT_WORKING_PAPER_MONTHS,
) -> dict[str, Any]:
    """Return the auditable default source/window plan for one scout run."""

    if journal_months <= 0 or working_paper_months <= 0:
        raise ValueError("Scout windows must be positive")
    topics = [item.casefold() for item in (scope or ["labor", "education"])]
    packs = [
        "econ_top5", "labor_field", "frontier_working_papers",
        "econometrics_methods", "evidence_synthesis",
    ]
    if "education" in topics:
        packs.append("education_field")
    if any(item in {"metascience", "science of science", "economics metascience"} for item in topics):
        packs.append("metascience_registries")
    date = dt.date.fromisoformat(as_of) if as_of else dt.date.today()
    return {
        "as_of": date.isoformat(),
        "scope": topics,
        "journal_months": journal_months,
        "working_paper_months": working_paper_months,
        "source_packs": list(dict.fromkeys(packs)),
        "sources": {
            pack: list(SOURCE_PACKS[pack])
            for pack in dict.fromkeys(packs)
        },
        "source_policy": dict(DEFAULT_SOURCE_POLICY),
        "topic_budget": dict(DEFAULT_TOPIC_BUDGET),
        "blocked_or_probe_required": dict(BLOCKED_DEFAULT_SOURCES),
    }


@dataclasses.dataclass(frozen=True)
class ScoutPaper:
    paper_id: str
    title: str
    authors: str
    published: str
    venue: str
    source_family: str
    url: str
    abstract: str
    evidence_level: str
    cluster: str
    identifiers: dict[str, str]
    suspected_version_of: str | None = None
    journal_rank_weight: float = 0.0
    journal_rank_tier: str = ""
    journal_rank_sources: tuple[str, ...] = ()
    abstract_access_route: str = ""
    abstract_access_verified: bool = False


# Institutional catalog weights are priors for retrieval and attention, not
# substitutes for paper-level design review.  The values harmonize the public
# Tianjin University A+/A/A-/B/B- and SUFE Top/First/Second/Third catalogs.
_VENUE_RANKS: dict[str, tuple[float, str]] = {
    "american economic review": (1.00, "top"),
    "econometrica": (1.00, "top"),
    "journal of political economy": (1.00, "top"),
    "quarterly journal of economics": (1.00, "top"),
    "review of economic studies": (1.00, "top"),
    "american economic journal applied economics": (0.86, "first"),
    "american economic journal economic policy": (0.86, "first"),
    "economic journal": (0.86, "first"),
    "journal of econometrics": (0.86, "first"),
    "journal of labor economics": (0.86, "first"),
    "journal of public economics": (0.86, "first"),
    "review of economics and statistics": (0.86, "first"),
    "quantitative economics": (0.79, "first_a_minus_consensus"),
    "econometric theory": (0.69, "second_a_minus_consensus"),
    "journal of applied econometrics": (0.69, "second_a_minus_consensus"),
    "journal of business and economic statistics": (0.69, "second_a_minus_consensus"),
    "journal of economic literature": (0.69, "second_a_minus_consensus"),
    "journal of human resources": (0.69, "second_a_minus_consensus"),
    "journal of economic perspectives": (0.62, "second_b_consensus"),
    "journal of population economics": (0.62, "second_b_consensus"),
    "oxford bulletin of economics and statistics": (0.52, "third_b_consensus"),
    "ilr review": (0.45, "third_b_minus_consensus"),
    "industrial and labor relations review": (0.45, "third_b_minus_consensus"),
    "industrial relations": (0.46, "third"),
    "labour economics": (0.45, "third_b_minus_consensus"),
    "economics of education review": (0.45, "third_b_minus_consensus"),
    "the econometrics journal": (0.45, "third_b_minus_consensus"),
    "econometrics journal": (0.45, "third_b_minus_consensus"),
    "annual review of economics": (0.44, "b_minus"),
    "education finance and policy": (0.55, "field_specialist_override"),
    "journal of economic surveys": (0.50, "evidence_synthesis_specialist"),
}


def _venue_key(value: str) -> str:
    compact = value.casefold().replace("&", " and ")
    compact = re.sub(r"[^a-z0-9]+", " ", compact)
    compact = " ".join(compact.split())
    aliases = {
        "aer": "american economic review",
        "aej applied economics": "american economic journal applied economics",
        "aej economic policy": "american economic journal economic policy",
        "jole": "journal of labor economics",
        "jhr": "journal of human resources",
        "labor economics": "labour economics",
    }
    return aliases.get(compact, compact)


def journal_rank_weight(paper: ScoutPaper) -> float:
    """Return a bounded venue/working-paper prior without rewarding volume."""

    if 0 < paper.journal_rank_weight <= 1:
        return paper.journal_rank_weight
    key = _venue_key(paper.venue)
    if key in _VENUE_RANKS:
        return _VENUE_RANKS[key][0]
    text = f"{paper.venue} {paper.source_family}".casefold()
    if "nber" in text:
        return 0.70
    if "cepr" in text:
        return 0.65
    if "iza" in text:
        return 0.60
    if source_quality_tier(paper) == "credible_economics":
        return 0.55
    if source_quality_tier(paper) == "priority_economics":
        return 0.70
    return 0.0


def journal_rank_tier(paper: ScoutPaper) -> str:
    if paper.journal_rank_tier:
        return paper.journal_rank_tier
    key = _venue_key(paper.venue)
    if key in _VENUE_RANKS:
        return _VENUE_RANKS[key][1]
    text = f"{paper.venue} {paper.source_family}".casefold()
    for marker, tier in (("nber", "frontier_wp_nber"), ("cepr", "frontier_wp_cepr"), ("iza", "frontier_wp_iza")):
        if marker in text:
            return tier
    return source_quality_tier(paper)


def paper_attention_weight(paper: ScoutPaper) -> float:
    evidence = {"title_only": 0.10, "metadata": 0.35, "abstract": 0.85, "targeted_full_text": 1.0}
    return journal_rank_weight(paper) * evidence[paper.evidence_level]


_PRIORITY_ECONOMICS_MARKERS = (
    "american economic review",
    "econometrica",
    "journal of political economy",
    "quarterly journal of economics",
    "review of economic studies",
    "journal of labor economics",
    "journal of human resources",
    "ilr review",
    "labour economics",
    "economics of education review",
    "education finance and policy",
    "nber working paper",
    "nber labor studies",
    "nber education",
    "iza discussion paper",
)

_CREDIBLE_ECONOMICS_MARKERS = (
    "american economic journal: applied economics",
    "american economic journal: economic policy",
    "review of economics and statistics",
    "journal of public economics",
    "cepr discussion paper",
    "aea rct registry",
    "official_journal",
    "public registry",
)

_OPEN_DISCOVERY_MARKERS = (
    "arxiv",
    "openalex",
    "ssrn",
    "repec",
)


def source_quality_tier(paper: ScoutPaper) -> str:
    """Classify research evidence by canonical venue, not discovery API.

    An OpenAlex-discovered QJE paper is still priority economics evidence,
    while an otherwise unverified OpenAlex/arXiv record remains discovery-only.
    """

    text = f"{paper.venue} {paper.source_family}".casefold()
    if any(marker in text for marker in _PRIORITY_ECONOMICS_MARKERS):
        return "priority_economics"
    if any(marker in text for marker in _CREDIBLE_ECONOMICS_MARKERS):
        return "credible_economics"
    if any(marker in text for marker in _OPEN_DISCOVERY_MARKERS):
        return "open_discovery"
    return "supplemental"


def assess_candidate_source_mix(
    candidates: Sequence[Mapping[str, Any]],
    papers: Sequence[ScoutPaper],
    *,
    aggregate_min_share: float,
    per_candidate_min_share: float,
    include_ranking_metrics: bool = True,
) -> dict[str, Any]:
    """Audit that candidate evidence is anchored in curated economics routes."""

    by_id = {paper.paper_id: paper for paper in papers}
    rows: list[dict[str, Any]] = []
    total = 0
    priority = 0
    for candidate in candidates:
        paper_ids = list(candidate.get("nearest_paper_ids", []))
        tiers = [source_quality_tier(by_id[paper_id]) for paper_id in paper_ids]
        rank_weights = [journal_rank_weight(by_id[paper_id]) for paper_id in paper_ids]
        priority_count = sum(tier in {"priority_economics", "credible_economics"} for tier in tiers)
        share = priority_count / len(tiers) if tiers else 0.0
        row = {
            "candidate_id": candidate.get("candidate_id"),
            "priority_count": priority_count,
            "total_count": len(tiers),
            "priority_share": round(share, 4),
            "passes": share >= per_candidate_min_share,
            "tiers": tiers,
        }
        if include_ranking_metrics:
            row.update({
                "rank_weights": [round(item, 4) for item in rank_weights],
                "mean_rank_weight": round(sum(rank_weights) / len(rank_weights), 4)
                if rank_weights else 0.0,
                "max_rank_weight": round(max(rank_weights), 4) if rank_weights else 0.0,
            })
        rows.append(row)
        total += len(tiers)
        priority += priority_count
    aggregate_share = priority / total if total else 0.0
    result = {
        "priority_count": priority,
        "total_count": total,
        "priority_share": round(aggregate_share, 4),
        "aggregate_passes": aggregate_share >= aggregate_min_share,
        "candidates": rows,
    }
    if include_ranking_metrics:
        all_rank_weights = [
            weight
            for candidate in candidates
            for weight in (
                journal_rank_weight(by_id[paper_id])
                for paper_id in candidate.get("nearest_paper_ids", [])
            )
        ]
        result["mean_rank_weight"] = (
            round(sum(all_rank_weights) / len(all_rank_weights), 4)
            if all_rank_weights else 0.0
        )
    failures = [row["candidate_id"] for row in rows if not row["passes"]]
    if failures or not result["aggregate_passes"]:
        reasons = []
        if failures:
            reasons.append("candidate floor failed: " + ", ".join(str(item) for item in failures))
        if not result["aggregate_passes"]:
            reasons.append(
                f"aggregate priority share {aggregate_share:.3f} below {aggregate_min_share:.3f}"
            )
        raise ValueError("Scout candidate source mix failed: " + "; ".join(reasons))
    return result


def normalize_paper(raw: Mapping[str, Any]) -> ScoutPaper:
    title = " ".join(str(raw.get("title", "")).split())
    if not title:
        raise ValueError("Scout paper needs a title")
    nested_identifiers = raw.get("identifiers", {})
    if not isinstance(nested_identifiers, Mapping):
        raise ValueError("Scout paper identifiers must be an object")
    identifiers = {
        key: str(raw.get(key, nested_identifiers.get(key, "")) or "")
        for key in ("doi", "arxiv_id", "openalex_id", "nber_id")
        if raw.get(key) or nested_identifiers.get(key)
    }
    abstract = " ".join(str(raw.get("abstract", "") or "").split())
    evidence_level = str(raw.get("evidence_level", "") or "")
    if not evidence_level:
        evidence_level = "abstract" if abstract else "title_only"
    if evidence_level not in {"title_only", "metadata", "abstract", "targeted_full_text"}:
        raise ValueError(f"Unsupported evidence_level: {evidence_level}")
    url = str(raw.get("url", "") or "")
    paper_id = stable_paper_id(title=title, url=url, **identifiers)
    provided_paper_id = str(raw.get("paper_id", "") or "")
    if provided_paper_id and provided_paper_id != paper_id:
        raise ValueError(
            f"Scout paper_id does not match stable identifiers: {provided_paper_id} != {paper_id}"
        )
    return ScoutPaper(
        paper_id=paper_id,
        title=title,
        authors=str(raw.get("authors", "") or ""),
        published=str(raw.get("published", "") or ""),
        venue=str(raw.get("venue", "") or ""),
        source_family=str(raw.get("source_family", raw.get("source", "unknown")) or "unknown"),
        url=url,
        abstract=abstract,
        evidence_level=evidence_level,
        cluster=str(raw.get("cluster", "unclustered") or "unclustered"),
        identifiers=identifiers,
        suspected_version_of=str(raw.get("suspected_version_of") or "") or None,
        journal_rank_weight=float(raw.get("journal_rank_weight", 0.0) or 0.0),
        journal_rank_tier=str(raw.get("journal_rank_tier", "") or ""),
        journal_rank_sources=tuple(str(item) for item in raw.get("journal_rank_sources", []) or []),
        abstract_access_route=str(raw.get("abstract_access_route", "") or ""),
        abstract_access_verified=bool(raw.get("abstract_access_verified", False))
        or evidence_level in {"abstract", "targeted_full_text"},
    )


def _paper_strength(paper: ScoutPaper) -> tuple[int, int, int]:
    evidence = {"title_only": 0, "metadata": 1, "abstract": 2, "targeted_full_text": 3}
    identifier_strength = 1 if paper.paper_id.startswith(("doi:", "openalex:", "nber:", "arxiv:")) else 0
    return evidence[paper.evidence_level], identifier_strength, len(paper.abstract)


def deduplicate_papers(raw_papers: Iterable[Mapping[str, Any]]) -> list[ScoutPaper]:
    """Collapse exact stable IDs; retain title-only version suspicions.

    A matching title is not enough to auto-merge a working paper and journal
    article.  We preserve both manifestations and mark the weaker identity as
    suspected so a human can confirm the relation.
    """

    by_id: dict[str, ScoutPaper] = {}
    for raw in raw_papers:
        paper = normalize_paper(raw)
        previous = by_id.get(paper.paper_id)
        if previous is None or _paper_strength(paper) > _paper_strength(previous):
            by_id[paper.paper_id] = paper

    title_groups: dict[str, list[ScoutPaper]] = {}
    for paper in by_id.values():
        normalized_title = normalize_title(paper.title)
        if len(normalized_title) >= 20:
            title_groups.setdefault(normalized_title, []).append(paper)
    for members in title_groups.values():
        if len(members) <= 1:
            continue
        strongest = max(members, key=_paper_strength)
        for member in members:
            if member.paper_id != strongest.paper_id:
                by_id[member.paper_id] = dataclasses.replace(
                    member, suspected_version_of=strongest.paper_id
                )
    return sorted(by_id.values(), key=lambda item: (item.cluster, item.published, item.paper_id))


def _published_date(value: str) -> dt.date | None:
    compact = str(value).strip()
    if not compact:
        return None
    try:
        if re.fullmatch(r"\d{4}", compact):
            return dt.date(int(compact), 1, 1)
        if re.fullmatch(r"\d{4}-\d{2}", compact):
            return dt.date.fromisoformat(f"{compact}-01")
        return dt.date.fromisoformat(compact[:10])
    except ValueError:
        return None


def _subtract_months(value: dt.date, months: int) -> dt.date:
    absolute = value.year * 12 + value.month - 1 - months
    year, zero_based_month = divmod(absolute, 12)
    month = zero_based_month + 1
    day = min(value.day, (dt.date(year + (month == 12), month % 12 + 1, 1) - dt.timedelta(days=1)).day)
    return dt.date(year, month, day)


def _working_paper(paper: ScoutPaper) -> bool:
    text = f"{paper.source_family} {paper.venue}".casefold()
    return any(marker in text for marker in (
        "working paper", "nber", "iza", "cepr", "ssrn", "discussion paper",
    ))


def classify_clusters(
    papers: Sequence[ScoutPaper],
    *,
    as_of: dt.date | None = None,
    journal_months: int = DEFAULT_JOURNAL_MONTHS,
    working_paper_months: int = DEFAULT_WORKING_PAPER_MONTHS,
    exclude_open_discovery: bool = False,
    include_ranking_metrics: bool = True,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[ScoutPaper]] = {}
    for paper in papers:
        grouped.setdefault(paper.cluster, []).append(paper)
    result: list[dict[str, Any]] = []
    for cluster, all_members in sorted(grouped.items()):
        if as_of is None:
            members = [
                item for item in all_members
                if not exclude_open_discovery or source_quality_tier(item) != "open_discovery"
            ]
            low_prior = [
                item for item in all_members
                if exclude_open_discovery and source_quality_tier(item) == "open_discovery"
            ]
            excluded: list[ScoutPaper] = []
        else:
            members = []
            excluded = []
            low_prior = []
            for item in all_members:
                published = _published_date(item.published)
                months = working_paper_months if _working_paper(item) else journal_months
                if published is not None and _subtract_months(as_of, months) <= published <= as_of:
                    if exclude_open_discovery and source_quality_tier(item) == "open_discovery":
                        low_prior.append(item)
                    else:
                        members.append(item)
                else:
                    excluded.append(item)
        venues = {item.venue.casefold() for item in members if item.venue}
        families = {item.source_family.casefold() for item in members if item.source_family}
        breadth = max(len(venues), len(families))
        weighted_attention = sum(paper_attention_weight(item) for item in members)
        label = (
            "hotspot"
            if (
                len(members) >= MIN_HOTSPOT_PAPERS
                and breadth >= MIN_HOTSPOT_SOURCE_BREADTH
                and (
                    not include_ranking_metrics
                    or weighted_attention >= MIN_WEIGHTED_HOTSPOT_ATTENTION
                )
            )
            else "emerging_signal"
        )
        row = {
            "cluster": cluster,
            "label": label,
            "paper_count": len(members),
            "total_paper_count": len(all_members),
            "source_breadth": breadth,
            "paper_ids": [item.paper_id for item in members],
            "out_of_window_or_undated_ids": [item.paper_id for item in excluded],
            "low_prior_support_ids": [item.paper_id for item in low_prior],
            "evidence_levels": dict(Counter(item.evidence_level for item in members)),
        }
        if include_ranking_metrics:
            rank_weights = sorted((journal_rank_weight(item) for item in members), reverse=True)
            frontier = rank_weights[:3]
            if len(members) >= 6 or weighted_attention >= 4.0:
                crowding_risk = "high"
            elif label == "hotspot":
                crowding_risk = "moderate"
            else:
                crowding_risk = "low_or_unknown"
            row.update({
                "tier_weighted_attention": round(weighted_attention, 4),
                "frontier_strength": round(sum(frontier) / len(frontier), 4) if frontier else 0.0,
                "high_rank_paper_count": sum(weight >= 0.8 for weight in rank_weights),
                "crowding_risk": crowding_risk,
                "opportunity_status": "requires_candidate_level_semantic_and_feasibility_review",
                "rank_tiers": dict(Counter(journal_rank_tier(item) for item in members)),
            })
        result.append(row)
    return result


_CANDIDATE_FIELDS = (
    "candidate_id",
    "title",
    "cluster",
    "mechanism",
    "unit",
    "exposure",
    "outcomes",
    "falsifiable_comparison",
    "data_identification",
    "why_now",
    "overlap",
    "largest_risk",
    "nearest_paper_ids",
    "is_ai_topic",
)


def validate_candidate(raw: Mapping[str, Any]) -> dict[str, Any]:
    candidate = dict(raw)
    missing = [field for field in _CANDIDATE_FIELDS if field not in candidate]
    if missing:
        raise ValueError(f"Scout candidate missing fields: {', '.join(missing)}")
    nearest = candidate["nearest_paper_ids"]
    if not isinstance(nearest, list) or not 2 <= len(nearest) <= 5:
        raise ValueError("Scout candidate needs 2-5 nearest_paper_ids")
    for field in (
        "title", "mechanism", "unit", "exposure", "outcomes", "falsifiable_comparison",
        "data_identification", "why_now", "overlap", "largest_risk",
    ):
        if not str(candidate[field]).strip():
            raise ValueError(f"Scout candidate field {field!r} cannot be empty")
    candidate["idea_origin"] = IDEA_ORIGIN
    candidate["is_ai_topic"] = bool(candidate["is_ai_topic"])
    candidate["score"] = float(candidate.get("score", 0.0))
    return candidate


def select_candidates(
    raw_candidates: Iterable[Mapping[str, Any]],
    *,
    limit: int = DEFAULT_CANDIDATES,
    min_non_ai_ratio: float = 0.5,
    max_per_cluster: int = 2,
) -> list[dict[str, Any]]:
    """Rank candidates while preserving topic and cluster diversity."""

    if not 1 <= limit <= MAX_CANDIDATES:
        raise ValueError(f"Candidate limit must be between 1 and {MAX_CANDIDATES}")
    if not 0 <= min_non_ai_ratio <= 1:
        raise ValueError("min_non_ai_ratio must be between zero and one")
    candidates = sorted(
        (validate_candidate(item) for item in raw_candidates),
        key=lambda item: (-item["score"], item["candidate_id"]),
    )
    selected: list[dict[str, Any]] = []
    per_cluster: Counter[str] = Counter()
    required_non_ai = int(limit * min_non_ai_ratio + 0.999999)
    available_non_ai = sum(not item["is_ai_topic"] for item in candidates)
    if available_non_ai < required_non_ai:
        raise ValueError(
            f"Scout candidate set has {available_non_ai} non-AI candidates; "
            f"at least {required_non_ai} are required"
        )
    for candidate in [item for item in candidates if not item["is_ai_topic"]]:
        if len(selected) >= required_non_ai:
            break
        if per_cluster[candidate["cluster"]] >= max_per_cluster:
            continue
        selected.append(candidate)
        per_cluster[candidate["cluster"]] += 1
    for candidate in candidates:
        if len(selected) >= limit:
            break
        if candidate in selected or per_cluster[candidate["cluster"]] >= max_per_cluster:
            continue
        selected.append(candidate)
        per_cluster[candidate["cluster"]] += 1
    return selected


def build_manifest(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Build a stable staged-run manifest from public retrieval results."""

    run_id = str(payload.get("run_id", ""))
    if not run_id.startswith("scout-"):
        raise ValueError("Scout run_id must start with 'scout-'")
    schema_version = str(payload.get("schema_version") or "1.1")
    include_ranking_metrics = schema_version != "1.0"
    queries = [validate_public_query(item) for item in payload.get("queries", [])]
    if not queries:
        raise ValueError("Scout manifest needs at least one public query")
    papers = deduplicate_papers(payload.get("papers", []))
    windows = dict(payload.get("windows", {
        "journals_months": DEFAULT_JOURNAL_MONTHS,
        "working_papers_months": DEFAULT_WORKING_PAPER_MONTHS,
    }))
    source_policy = dict(payload.get("source_policy", {}))
    if include_ranking_metrics:
        source_policy = {**DEFAULT_SOURCE_POLICY, **source_policy}
    candidates = select_candidates(
        payload.get("candidates", []),
        limit=int(payload.get("candidate_limit", DEFAULT_CANDIDATES)),
    ) if payload.get("candidates") else []
    style_hash = str(payload.get("style_hash", ""))
    if not re.fullmatch(r"[0-9a-f]{64}", style_hash):
        raise ValueError("Scout manifest needs a SHA-256 style_hash, not private style text")
    created_at = str(payload.get("created_at", ""))
    if not created_at:
        raise ValueError("Scout manifest needs a fixed created_at for resumable hashes")
    try:
        as_of = dt.date.fromisoformat(created_at[:10])
    except ValueError as exc:
        raise ValueError("Scout manifest created_at must begin with an ISO date") from exc
    clusters = classify_clusters(
        papers,
        as_of=as_of,
        journal_months=int(windows.get("journals_months", DEFAULT_JOURNAL_MONTHS)),
        working_paper_months=int(windows.get("working_papers_months", DEFAULT_WORKING_PAPER_MONTHS)),
        exclude_open_discovery=bool(source_policy.get("hotspot_excludes_open_discovery", False)),
        include_ranking_metrics=include_ranking_metrics,
    )
    paper_ids = {item.paper_id for item in papers}
    unknown_nearest = sorted({
        paper_id
        for candidate in candidates
        for paper_id in candidate["nearest_paper_ids"]
        if paper_id not in paper_ids
    })
    if unknown_nearest:
        raise ValueError(
            "Scout candidates cite paper IDs absent from the run manifest: "
            + ", ".join(unknown_nearest)
        )
    source_mix: dict[str, Any] | None = None
    if candidates and source_policy:
        source_mix = assess_candidate_source_mix(
            candidates,
            papers,
            aggregate_min_share=float(source_policy.get("candidate_priority_min_share", 0.7)),
            per_candidate_min_share=float(
                source_policy.get("candidate_per_item_priority_min_share", 0.5)
            ),
            include_ranking_metrics=include_ranking_metrics,
        )
    paper_rows = []
    for item in papers:
        row = dataclasses.asdict(item)
        if not include_ranking_metrics:
            for field in (
                "journal_rank_weight", "journal_rank_tier", "journal_rank_sources",
                "abstract_access_route", "abstract_access_verified",
            ):
                row.pop(field, None)
        paper_rows.append(row)
    manifest = {
        "schema_version": schema_version,
        "run_id": run_id,
        "created_at": created_at,
        "scope": list(payload.get("scope", ["labor", "education"])),
        "windows": windows,
        "style_hash": style_hash,
        "queries": queries,
        "source_health": dict(payload.get("source_health", {})),
        "papers": paper_rows,
        "clusters": clusters,
        "candidates": candidates,
    }
    if source_policy:
        manifest["source_policy"] = source_policy
    if source_mix is not None:
        manifest["candidate_source_mix"] = source_mix
    manifest["manifest_hash"] = stable_json_hash(manifest)
    return manifest
