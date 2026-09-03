"""Obsidian projections for the economics frontier-review state."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping


DEFAULT_WINDOW_MONTHS = 12


def paper_filename(paper_id: str) -> str:
    return hashlib.sha256(paper_id.encode("utf-8")).hexdigest()[:20] + ".md"


def _md(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def extract_human_notes(text: str) -> str:
    marker = "## Human Notes"
    if marker not in text:
        return ""
    return text.split(marker, 1)[1].strip()


def render_paper_note(paper: Mapping[str, Any]) -> str:
    identifiers = paper.get("identifiers", {}) or {}
    lines = [
        "---",
        "schema_version: 2",
        "tags: [frontier-paper, economics]",
        f"paper_id: {json.dumps(str(paper['paper_id']), ensure_ascii=False)}",
        f"evidence_level: {paper.get('evidence_level', 'metadata')}",
        f"first_seen_at: {paper.get('first_seen_at', '')}",
        f"last_seen_at: {paper.get('last_seen_at', '')}",
        f"abstract_hash: {paper.get('abstract_hash', '')}",
        "---",
        "",
        f"# {paper.get('title', 'Untitled paper')}",
        "",
        f"- **Authors:** {paper.get('authors', '')}",
        f"- **Date / venue:** {paper.get('published', '')} — {paper.get('venue', '')}",
        f"- **Status:** {paper.get('source_family', '')}; {paper.get('journal_rank_tier', '')}",
        f"- **Public URL:** {paper.get('url', '')}",
        f"- **Identifiers:** {_md(json.dumps(identifiers, ensure_ascii=False, sort_keys=True))}",
        f"- **Primary cluster:** {paper.get('primary_cluster_id') or 'unassigned'}",
        "",
        "## Abstract Evidence",
        "",
        paper.get("abstract", "") or "Abstract unavailable; no substantive claim may rely on this record.",
        "",
        "## Provenance Boundary",
        "",
        "This is an agent-screened frontier record, not a human-read canonical source note. "
        "Claims are bounded by the recorded evidence level.",
        "",
    ]
    if paper.get("evidence_downgrade_at"):
        lines.extend([
            "## Retrieval Warning",
            "",
            "The latest retrieval returned weaker evidence. The last verified abstract is retained "
            "until a replacement can be verified.",
            f"Latest retrieval level: `{paper.get('latest_retrieval_evidence_level')}` at "
            f"`{paper.get('evidence_downgrade_at')}`.",
            "",
        ])
    return "\n".join(lines)


def _paper_links(ids: Iterable[str], papers: Mapping[str, Mapping[str, Any]]) -> str:
    links = []
    for paper_id in ids:
        paper = papers.get(paper_id, {})
        links.append(f"[[../papers/{paper_filename(paper_id)[:-3]}|{_md(paper.get('title', paper_id))}]]")
    return "; ".join(links)


def render_cluster_note(
    cluster: Mapping[str, Any], papers: Mapping[str, Mapping[str, Any]], *, human_notes: str = ""
) -> str:
    lines = [
        "---",
        "schema_version: 2",
        "tags: [frontier-cluster, economics]",
        f"cluster_id: {cluster['cluster_id']}",
        f"status: {cluster.get('status', 'active')}",
        f"confidence: {cluster.get('confidence', 'provisional')}",
        f"evidence_basis: {cluster.get('evidence_basis', 'abstract_only')}",
        f"first_seen_at: {cluster.get('first_seen_at', '')}",
        f"last_updated_at: {cluster.get('last_updated_at', '')}",
        "---",
        "",
        f"# {cluster.get('title', cluster['cluster_id'])}",
        "",
        "## Research Question",
        "",
        str(cluster.get("research_question", "")),
        "",
        "## Current Consensus",
        "",
    ]
    for item in cluster.get("current_consensus", []):
        lines.append(
            f"- {_md(item.get('claim', ''))} — "
            f"{_paper_links(item.get('supporting_paper_ids', []), papers)}"
        )
    lines.extend([
        "",
        "## Disagreements and Boundaries",
        "",
        "| Type | Tension | Relationship | Side A | Side B | Status |",
        "|------|---------|--------------|--------|--------|--------|",
    ])
    disagreements = cluster.get("disagreements", [])
    if disagreements:
        for item in disagreements:
            lines.append(
                "| " + " | ".join((
                    _md(item["type"]),
                    _md(item["statement"]),
                    _md(item["relationship"]),
                    _md(_paper_links(item["side_a_paper_ids"], papers)),
                    _md(_paper_links(item["side_b_paper_ids"], papers)),
                    _md(item["resolution_status"]),
                )) + " |"
            )
    else:
        lines.append("| — | No source-supported disagreement established | — | — | — | open |")
    lines.extend([
        "",
        "## Progress",
        "",
        "| Dimension | Earlier frontier | Current movement | Evidence |",
        "|-----------|------------------|------------------|----------|",
    ])
    for item in cluster.get("progress", []):
        lines.append(
            "| " + " | ".join((
                _md(item["dimension"]),
                _md(item["before"]),
                _md(item["now"]),
                _md(_paper_links(item["supporting_paper_ids"], papers)),
            )) + " |"
        )
    if not cluster.get("progress"):
        lines.append("| — | Not established | Not established | — |")
    lines.extend(["", "## Open Questions", ""])
    lines.extend(
        f"- {item}" for item in cluster.get("open_questions", [])
    )
    if not cluster.get("open_questions"):
        lines.append("- None stated from current evidence.")
    lines.extend([
        "",
        "## Evidence Boundary",
        "",
        f"- Basis: `{cluster.get('evidence_basis', 'abstract_only')}`",
        f"- Confidence: `{cluster.get('confidence', 'provisional')}`",
        f"- Source breadth: {cluster.get('source_breadth', 0)}",
        f"- Tier-weighted attention: {cluster.get('tier_weighted_attention', 0)}",
        f"- Evidence levels: `{json.dumps(cluster.get('evidence_levels', {}), sort_keys=True)}`",
        f"- Note: {cluster.get('evidence_note', '')}",
        f"- Latest change: {cluster.get('change_summary', '')}",
        "",
        "## Targeted Full-Text Provenance",
        "",
        "| Paper | Public version | Match | Sections | Checked claims |",
        "|-------|----------------|-------|----------|----------------|",
    ])
    for check in cluster.get("full_text_checks", []):
        lines.append(
            "| " + " | ".join((
                _md(_paper_links([check["paper_id"]], papers)),
                _md(check["version_url"]),
                _md(check["matched_by"]),
                _md("; ".join(check["sections"])),
                _md("; ".join(check["checked_claims"])),
            )) + " |"
        )
    if not cluster.get("full_text_checks"):
        lines.append("| — | Abstract-only synthesis | — | — | — |")
    lines.extend([
        "",
        "## Included Papers",
        "",
    ])
    lines.extend(
        f"- {_paper_links([paper_id], papers)}"
        for paper_id in cluster.get("paper_ids", [])
    )
    lines.extend(["", "## Human Notes", "", human_notes.strip(), ""])
    return "\n".join(lines)


def render_index(state: Mapping[str, Any]) -> str:
    lines = [
        "---",
        "schema_version: 2",
        "tags: [research-frontier, economics]",
        f"updated_at: {state.get('updated_at', '')}",
        "derived: true",
        "---",
        "",
        "# Economics Research Frontier",
        "",
        "Incremental, source-grounded map of recent labor and education economics. "
        "Abstract-only syntheses remain provisional; paper records here are not human-read source notes.",
        "",
        "| Cluster | Confidence | Evidence | Breadth | Attention | Papers | Updated |",
        "|---------|------------|----------|---------|-----------|--------|---------|",
    ]
    for cluster_id, cluster in state.get("clusters", {}).items():
        if cluster.get("status", "active") == "superseded":
            continue
        lines.append(
            f"| [[clusters/{cluster_id}|{_md(cluster.get('title', cluster_id))}]] "
            f"| {_md(cluster.get('confidence', 'provisional'))} "
            f"| {_md(cluster.get('evidence_basis', 'abstract_only'))} "
            f"| {cluster.get('source_breadth', 0)} "
            f"| {cluster.get('tier_weighted_attention', 0)} "
            f"| {len(cluster.get('paper_ids', []))} "
            f"| {_md(cluster.get('last_updated_at', ''))} |"
        )
    lines.extend([
        "",
        "## State",
        "",
        f"- Last run: `{state.get('last_run_id', '')}`",
        f"- Active / historical papers: "
        f"{sum(row.get('frontier_status', 'active') == 'active' for row in state.get('papers', {}).values())} "
        f"/ {len(state.get('papers', {}))}",
        f"- Run count: {state.get('run_count', 0)}",
        f"- Last reconciliation: `{state.get('last_reconciled_at', '')}`",
        "",
    ])
    return "\n".join(lines)


def render_run_report(manifest: Mapping[str, Any], state: Mapping[str, Any]) -> str:
    inventory = manifest.get("inventory", {})
    lines = [
        f"# Frontier Review Run — {manifest.get('run_id', '')}",
        "",
        f"- Created: {manifest.get('created_at', '')}",
        f"- Scope: {', '.join(manifest.get('scope', []))}",
        f"- Window: {manifest.get('window_months', DEFAULT_WINDOW_MONTHS)} months",
        f"- Token mode: {manifest.get('token_mode', '')}",
        f"- Planned abstract/router input: {manifest.get('estimated_input_tokens', 0)} tokens",
        f"- Reserved partial-worker output: {manifest.get('reserved_partial_output_tokens', 0)} tokens",
        f"- Targeted full-text input: {manifest.get('full_text_input_tokens', 0)} tokens",
        f"- Synthesis output estimate: {manifest.get('synthesis_output_tokens', 0)} tokens",
        f"- Estimated total: {manifest.get('estimated_total_tokens', 0)} tokens",
        "",
        "## Incremental Work",
        "",
        f"- Retrieved / selected: {inventory.get('retrieved_count', 0)} / {inventory.get('selected_count', 0)}",
        f"- New: {len(inventory.get('new_ids', []))}",
        f"- Changed: {len(inventory.get('changed_ids', []))}",
        f"- Reused without rereading: {len(inventory.get('unchanged_ids', []))}",
        f"- Reconciliation sample: {len(inventory.get('reconcile_sample_ids', []))}",
        f"- Abstract unavailable / metadata only: {len(inventory.get('metadata_only_ids', []))}",
        f"- Evidence downgrades retained from memory: {len(inventory.get('evidence_downgraded_ids', []))}",
        f"- Out of window / undated: {len(inventory.get('out_of_window_ids', []))} / {len(inventory.get('undated_ids', []))}",
        f"- Coarse publication dates retained with uncertainty: {len(inventory.get('date_uncertain_ids', []))}",
        f"- Deferred by token mode: {len(inventory.get('deferred_ids', []))}",
        "",
        "## Updated Clusters",
        "",
    ]
    for cluster_id in manifest.get("updated_cluster_ids", []):
        cluster = state.get("clusters", {}).get(cluster_id, {})
        lines.append(
            f"- [[../../clusters/{cluster_id}|{cluster.get('title', cluster_id)}]] "
            f"— {cluster.get('change_summary', '')}"
        )
    if not manifest.get("updated_cluster_ids"):
        lines.append("- No cluster synthesis changed.")
    lines.extend([
        "",
        "## Papers Processed This Run",
        "",
    ])
    touched = [
        *inventory.get("new_ids", []),
        *inventory.get("changed_ids", []),
        *inventory.get("reconcile_sample_ids", []),
    ]
    for paper_id in dict.fromkeys(touched):
        paper = state.get("papers", {}).get(paper_id, {})
        lines.append(f"- {paper.get('title', paper_id)} — `{paper_id}`")
    if not touched:
        lines.append("- No new or changed abstract evidence.")
    lines.extend([
        "",
        "## Coverage and Limits",
        "",
        f"- Source health: `{json.dumps(manifest.get('source_health', {}), ensure_ascii=False, sort_keys=True)}`",
        f"- Targeted full-text checks: {manifest.get('full_text_check_count', 0)}",
        "- A missing abstract never supports a substantive finding.",
        "- A working-paper version is used only after an explicit version match and section-level provenance record.",
        "",
        "## Targeted Full-Text Checks",
        "",
        "| Cluster | Paper ID | Public version | Sections | Checked claims |",
        "|---------|----------|----------------|----------|----------------|",
    ])
    for check in manifest.get("full_text_checks", []):
        lines.append(
            "| " + " | ".join((
                _md(check.get("cluster_id")),
                _md(check.get("paper_id")),
                _md(check.get("version_url")),
                _md("; ".join(check.get("sections", []))),
                _md("; ".join(check.get("checked_claims", []))),
            )) + " |"
        )
    if not manifest.get("full_text_checks"):
        lines.append("| — | — | No targeted full-text checks | — | — |")
    lines.append("")
    return "\n".join(lines)
