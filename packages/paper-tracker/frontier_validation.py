"""Evidence and synthesis validation for economics frontier reviews."""

from __future__ import annotations

import json
import re
from typing import Any, Mapping
from urllib.parse import urlparse

from frontier_tokens import estimate_tokens


SYNTHESIS_EVIDENCE = {"abstract_only", "mixed_with_targeted_full_text"}
DISAGREEMENT_TYPES = {
    "result",
    "mechanism",
    "measurement",
    "identification",
    "external_validity",
    "policy_interpretation",
    "scope_boundary",
}
PROGRESS_DIMENSIONS = {
    "question",
    "data",
    "measurement",
    "identification",
    "mechanism",
    "finding",
    "policy",
}
VERSION_MATCH_METHODS = {
    "stable_id",
    "doi",
    "explicit_author_version",
    "verified_title_authors",
}
CLUSTER_STATUSES = {"active", "provisional", "superseded"}
RESOLUTION_STATUSES = {"open", "boundary_explains_difference", "resolved", "mixed"}
WINDOWS_RESERVED_NAMES = {
    "con", "prn", "aux", "nul",
    *(f"com{index}" for index in range(1, 10)),
    *(f"lpt{index}" for index in range(1, 10)),
}


def _slug(value: Any, field: str) -> str:
    text = str(value or "").strip().casefold()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", text):
        raise ValueError(f"Frontier {field} must be a lowercase hyphenated slug")
    if text in WINDOWS_RESERVED_NAMES:
        raise ValueError(f"Frontier {field} is a reserved Windows filename")
    return text


def _nonempty(value: Any, field: str) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        raise ValueError(f"Frontier {field} cannot be empty")
    return text


def _paper_ids(raw: Any, known: set[str], field: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(raw, list):
        raise ValueError(f"Frontier {field} must be a list")
    values = list(dict.fromkeys(str(item) for item in raw))
    if not allow_empty and not values:
        raise ValueError(f"Frontier {field} cannot be empty")
    unknown = sorted(set(values) - known)
    if unknown:
        raise ValueError(f"Frontier {field} references unknown papers: {', '.join(unknown)}")
    return values


def _normalized_identity(value: Any) -> str:
    return "".join(
        character
        for character in str(value or "").casefold()
        if character.isalnum()
    )


def _normalized_doi(value: Any) -> str:
    text = str(value or "").strip().casefold()
    return re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", text)


def _public_http_url(value: Any, field: str) -> str:
    url = _nonempty(value, field)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Frontier {field} must be a public HTTP(S) URL")
    return url


def _validate_version_match(
    item: Mapping[str, Any], paper: Mapping[str, Any], matched_by: str
) -> dict[str, Any]:
    details = {
        "version_title": str(item.get("version_title", "") or ""),
        "version_authors": str(item.get("version_authors", "") or ""),
        "version_doi": str(item.get("version_doi", "") or ""),
        "version_paper_id": str(item.get("version_paper_id", "") or ""),
        "match_evidence_url": str(item.get("match_evidence_url", "") or ""),
    }
    if matched_by == "stable_id":
        if details["version_paper_id"] != paper.get("paper_id"):
            raise ValueError("Frontier stable_id match must equal the stored paper_id")
    elif matched_by == "doi":
        stored_doi = _normalized_doi((paper.get("identifiers", {}) or {}).get("doi"))
        if not stored_doi or _normalized_doi(details["version_doi"]) != stored_doi:
            raise ValueError("Frontier DOI match must equal the stored DOI")
    else:
        stored_title = _normalized_identity(paper.get("title"))
        stored_authors = _normalized_identity(paper.get("authors"))
        version_title = _normalized_identity(details["version_title"])
        version_authors = _normalized_identity(details["version_authors"])
        same_title = bool(stored_title and version_title) and version_title == stored_title
        same_authors = bool(stored_authors and version_authors) and version_authors == stored_authors
        if not same_title or not same_authors:
            raise ValueError("Frontier title/author match must equal stored bibliographic fields")
        if matched_by == "explicit_author_version":
            details["match_evidence_url"] = _public_http_url(
                details["match_evidence_url"], "match_evidence_url"
            )
    return details


def _validate_full_text_checks(
    raw: Any,
    known_papers: Mapping[str, Mapping[str, Any]],
    cluster_paper_ids: set[str],
    *,
    cap: int,
) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("Frontier full_text_checks must be a list")
    if len(raw) > cap:
        raise ValueError(f"Frontier full-text checks exceed the per-cluster cap of {cap}")
    checks: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, Mapping):
            raise ValueError("Each frontier full-text check must be an object")
        paper_id = str(item.get("paper_id", ""))
        if paper_id not in cluster_paper_ids:
            raise ValueError(
                f"Frontier full-text check references a paper outside the cluster: {paper_id}"
            )
        if paper_id in seen:
            raise ValueError(f"Frontier full-text check is duplicated: {paper_id}")
        seen.add(paper_id)
        matched_by = str(item.get("matched_by", ""))
        if matched_by not in VERSION_MATCH_METHODS:
            raise ValueError("Frontier full-text check needs a verified version match method")
        paper = known_papers.get(paper_id)
        if not isinstance(paper, Mapping):
            raise ValueError(f"Frontier full-text check lacks stored paper metadata: {paper_id}")
        sections = [_nonempty(value, "full_text section") for value in item.get("sections", [])]
        if not sections:
            raise ValueError("Frontier full-text check needs targeted section names")
        checked_claims = [
            _nonempty(value, "checked claim") for value in item.get("checked_claims", [])
        ]
        if not checked_claims:
            raise ValueError("Frontier full-text check needs checked claims")
        evidence_input_tokens = int(item.get("evidence_input_tokens", 0))
        if evidence_input_tokens <= 0:
            raise ValueError("Frontier full-text check needs positive evidence_input_tokens")
        match_details = _validate_version_match(item, paper, matched_by)
        checks.append({
            "paper_id": paper_id,
            "version_url": _public_http_url(item.get("version_url"), "version_url"),
            "matched_by": matched_by,
            "sections": sections,
            "checked_claims": checked_claims,
            "evidence_input_tokens": evidence_input_tokens,
            **match_details,
        })
    return checks


def validate_cluster_synthesis(
    raw: Mapping[str, Any],
    known_papers: Mapping[str, Mapping[str, Any]] | set[str],
    *,
    full_text_cap: int = 0,
    synthesis_token_cap: int | None = None,
) -> dict[str, Any]:
    if isinstance(known_papers, Mapping):
        paper_rows = {
            str(paper_id): row
            for paper_id, row in known_papers.items()
            if isinstance(row, Mapping)
        }
        known_paper_ids = {
            paper_id
            for paper_id, row in paper_rows.items()
            if row.get("evidence_level") in {"abstract", "targeted_full_text"}
            and row.get("abstract")
        }
    else:
        known_paper_ids = set(known_papers)
        paper_rows = {paper_id: {"paper_id": paper_id} for paper_id in known_paper_ids}
    cluster_id = _slug(raw.get("cluster_id"), "cluster_id")
    status = str(raw.get("status", "active"))
    if status not in CLUSTER_STATUSES:
        raise ValueError(f"Unsupported frontier cluster status: {status}")
    paper_ids = _paper_ids(
        raw.get("paper_ids"),
        known_paper_ids,
        "cluster paper_ids",
        allow_empty=status == "superseded",
    )
    cluster_paper_ids = set(paper_ids)
    consensus: list[dict[str, Any]] = []
    for item in raw.get("current_consensus", []):
        if not isinstance(item, Mapping):
            raise ValueError("Each frontier consensus claim must be an object")
        consensus.append({
            "claim": _nonempty(item.get("claim"), "consensus claim"),
            "supporting_paper_ids": _paper_ids(
                item.get("supporting_paper_ids"),
                cluster_paper_ids,
                "consensus support",
            ),
        })
    if not consensus and status != "superseded":
        raise ValueError("Frontier current_consensus needs paper-supported claim objects")
    disagreements: list[dict[str, Any]] = []
    for item in raw.get("disagreements", []):
        if not isinstance(item, Mapping):
            raise ValueError("Each frontier disagreement must be an object")
        kind = str(item.get("type", ""))
        if kind not in DISAGREEMENT_TYPES:
            raise ValueError(f"Unsupported frontier disagreement type: {kind}")
        side_a = _paper_ids(
            item.get("side_a_paper_ids", []), cluster_paper_ids, "disagreement side A"
        )
        side_b = _paper_ids(
            item.get("side_b_paper_ids", []), cluster_paper_ids, "disagreement side B"
        )
        if set(side_a) & set(side_b):
            raise ValueError("The same paper cannot support both sides of a disagreement")
        resolution_status = str(item.get("resolution_status", "open"))
        if resolution_status not in RESOLUTION_STATUSES:
            raise ValueError(
                f"Unsupported frontier disagreement resolution: {resolution_status}"
            )
        disagreements.append({
            "type": kind,
            "statement": _nonempty(item.get("statement"), "disagreement statement"),
            "relationship": _nonempty(item.get("relationship"), "disagreement relationship"),
            "side_a_paper_ids": side_a,
            "side_b_paper_ids": side_b,
            "resolution_status": resolution_status,
        })
    progress: list[dict[str, Any]] = []
    for item in raw.get("progress", []):
        if not isinstance(item, Mapping):
            raise ValueError("Each frontier progress item must be an object")
        dimension = str(item.get("dimension", ""))
        if dimension not in PROGRESS_DIMENSIONS:
            raise ValueError(f"Unsupported frontier progress dimension: {dimension}")
        progress.append({
            "dimension": dimension,
            "before": _nonempty(item.get("before"), "progress before"),
            "now": _nonempty(item.get("now"), "progress now"),
            "supporting_paper_ids": _paper_ids(
                item.get("supporting_paper_ids"), cluster_paper_ids, "progress support"
            ),
        })
    evidence_basis = str(raw.get("evidence_basis", "abstract_only"))
    if evidence_basis not in SYNTHESIS_EVIDENCE:
        raise ValueError(f"Unsupported frontier synthesis evidence: {evidence_basis}")
    full_text_checks = _validate_full_text_checks(
        raw.get("full_text_checks"),
        paper_rows,
        cluster_paper_ids,
        cap=full_text_cap,
    )
    if evidence_basis == "mixed_with_targeted_full_text" and not full_text_checks:
        raise ValueError("Mixed frontier synthesis must record targeted full-text checks")
    if evidence_basis == "abstract_only" and full_text_checks:
        raise ValueError("Abstract-only frontier synthesis cannot contain full-text checks")
    confidence = str(raw.get("confidence", "provisional"))
    if confidence not in {"provisional", "moderate", "high"}:
        raise ValueError(f"Unsupported frontier confidence: {confidence}")
    if confidence == "high" and evidence_basis == "abstract_only":
        raise ValueError("Abstract-only frontier synthesis cannot claim high confidence")
    result = {
        "cluster_id": cluster_id,
        "title": _nonempty(raw.get("title"), "cluster title"),
        "aliases": list(dict.fromkeys(
            _nonempty(value, "cluster alias") for value in raw.get("aliases", [])
        )),
        "status": status,
        "research_question": _nonempty(raw.get("research_question"), "research question"),
        "current_consensus": consensus,
        "disagreements": disagreements,
        "progress": progress,
        "open_questions": [
            _nonempty(value, "open question") for value in raw.get("open_questions", [])
        ],
        "paper_ids": paper_ids,
        "evidence_basis": evidence_basis,
        "evidence_note": _nonempty(raw.get("evidence_note"), "evidence note"),
        "full_text_checks": full_text_checks,
        "confidence": confidence,
        "change_summary": _nonempty(raw.get("change_summary"), "change summary"),
    }
    if synthesis_token_cap is not None:
        serialized = json.dumps(result, ensure_ascii=False, sort_keys=True)
        estimated_tokens = estimate_tokens(serialized)
        if estimated_tokens > synthesis_token_cap:
            raise ValueError(
                "Frontier cluster synthesis exceeds its token cap: "
                f"{cluster_id} ({estimated_tokens} > {synthesis_token_cap})"
            )
    return result
