"""Deterministic, bounded idea-context retrieval with provenance.

The retriever intentionally does not read researcher_profile.md. The target idea,
its authoritative S2 gate, the latest session sidecar, and the explicit objective
define the retrieval query.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .util import (
    SCHEMA_VERSION,
    atomic_write_json,
    atomic_write_text,
    ensure_within,
    read_json,
    read_text,
    sha256_file,
    slug_is_safe,
    stable_hash,
    utc_now,
)


CATEGORIES = ("support", "contradict", "method", "data", "nearest")
_CATEGORY_ORDER = {
    "literature": ("nearest", "contradict", "support", "method", "data"),
    "challenge": ("contradict", "nearest", "method", "data", "support"),
    "method": ("method", "contradict", "data", "nearest", "support"),
    "data": ("data", "method", "contradict", "nearest", "support"),
    "mechanism": ("support", "contradict", "nearest", "method", "data"),
    "nearest": ("nearest", "contradict", "support", "method", "data"),
    "general": ("support", "contradict", "method", "data", "nearest"),
}

_STOPWORDS = {
    "about", "after", "again", "against", "also", "and", "are", "because", "been",
    "before", "being", "between", "could", "does", "from", "have", "into", "more",
    "most", "other", "should", "that", "their", "there", "these", "they", "this",
    "through", "under", "using", "what", "when", "where", "which", "while", "with",
    "would", "研究", "论文", "问题", "当前", "这个", "是否", "以及", "通过",
}

_CATEGORY_MARKERS = {
    "contradict": (
        "contradict", "counter", "however", "null", "fails", "failure", "threat", "against",
        "not support", "weakness", "limitation", "批评", "反例", "冲突", "威胁", "不支持", "不足",
    ),
    "method": (
        "method", "identification", "instrument", "difference-in-differences", "did", "rct",
        "regression discontinuity", "estimator", "causal design", "方法", "识别", "工具变量", "随机",
    ),
    "data": (
        "dataset", "data source", "sample", "administrative data", "panel", "survey", "measurement",
        "outcome variable", "数据", "样本", "测量", "数据库",
    ),
    "nearest": (
        "nearest", "closest", "already done", "duplicate", "overlap", "work family", "最接近",
        "最近邻", "重复", "版本",
    ),
}


@dataclass
class Candidate:
    source_type: str
    path: Path
    claim: str
    locator: str
    category: str
    score: float
    matched_terms: list[str]
    full_source: bool = False


def _frontmatter(text: str) -> dict[str, str]:
    lines = text.lstrip("\ufeff").splitlines()
    delimiters = [index for index, line in enumerate(lines[:100]) if line.strip() == "---"]
    if len(delimiters) < 2:
        return {}
    start, end = delimiters[0], delimiters[1]
    result: dict[str, str] = {}
    for line in lines[start + 1:end]:
        if ":" in line:
            key, value = line.split(":", 1)
            value = re.sub(r"\s+#.*$", "", value).strip().strip('"\'')
            result[key.strip()] = value
    return result


def _extract_section(text: str, heading_patterns: Iterable[str]) -> tuple[str, int, int] | None:
    lines = text.splitlines()
    patterns = [re.compile(pattern, re.I) for pattern in heading_patterns]
    start: int | None = None
    level: int | None = None
    for index, line in enumerate(lines):
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if match and any(pattern.search(match.group(2)) for pattern in patterns):
            start = index
            level = len(match.group(1))
            break
    if start is None or level is None:
        return None
    end = len(lines)
    for index in range(start + 1, len(lines)):
        match = re.match(r"^(#{1,6})\s+", lines[index])
        if match and len(match.group(1)) <= level:
            end = index
            break
    return "\n".join(lines[start + 1:end]).strip(), start + 2, end


def _tokens(text: str) -> list[str]:
    normalized = text.casefold().replace("–", "-").replace("—", "-")
    tokens = re.findall(r"[a-z0-9][a-z0-9_-]{2,}|[\u4e00-\u9fff]{2,}", normalized)
    result: list[str] = []
    for token in tokens:
        if token in _STOPWORDS:
            continue
        result.append(token)
        if re.fullmatch(r"[\u4e00-\u9fff]{5,}", token):
            result.extend(token[index:index + 2] for index in range(len(token) - 1))
    return result


def _add_query_terms(target: Counter[str], text: str, weight: float) -> None:
    for token in _tokens(text):
        target[token] = max(target[token], weight)


def _score(text: str, query: Counter[str]) -> tuple[float, list[str]]:
    token_counts = Counter(_tokens(text))
    matched = [token for token in query if token_counts[token]]
    score = sum(query[token] * min(3, token_counts[token]) for token in matched)
    return float(score), sorted(matched, key=lambda item: (-query[item], item))[:8]


def _category(text: str, *, fallback: str = "support") -> str:
    lowered = text.casefold()
    best = fallback
    best_count = 0
    for category, markers in _CATEGORY_MARKERS.items():
        count = sum(marker in lowered for marker in markers)
        if count > best_count:
            best, best_count = category, count
    return best


def _best_paragraph(text: str, query: Counter[str]) -> tuple[str, str, float, list[str]]:
    lines = text.splitlines()
    blocks: list[tuple[int, int, str]] = []
    start: int | None = None
    content: list[str] = []
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped == "---" or stripped.startswith("#"):
            if content and start is not None:
                blocks.append((start, index - 1, " ".join(content)))
            start, content = None, []
            continue
        if start is None:
            start = index
        content.append(re.sub(r"^[-*+]\s+", "", stripped))
    if content and start is not None:
        blocks.append((start, len(lines), " ".join(content)))
    if not blocks:
        return "", "line 1", 0.0, []
    ranked = []
    for block_start, block_end, block in blocks:
        score, matched = _score(block, query)
        ranked.append((score, -block_start, block_start, block_end, block, matched))
    score, _, block_start, block_end, block, matched = max(ranked)
    claim = re.sub(r"\s+", " ", block).strip()
    if len(claim) > 700:
        claim = claim[:697].rstrip() + "..."
    locator = f"lines {block_start}-{block_end}" if block_end != block_start else f"line {block_start}"
    return claim, locator, score, matched


def _artifact_ref(path: Path, source_type: str, locator: str) -> dict[str, Any]:
    return {
        "artifact_id": f"sha256:{sha256_file(path)}",
        "path": str(path.resolve()),
        "locator": locator,
        "source_type": source_type,
        "content_hash": sha256_file(path),
    }


def _latest_session(session_dir: Path, slug: str) -> Path | None:
    if not session_dir.exists():
        return None
    # Session identity is exact. Prefix globbing can leak state from an idea
    # such as ``ai`` into ``ai-teachers-session.json``.
    exact = session_dir / f"{slug}-session.json"
    return exact if exact.is_file() else None


def _scope_from_gate(gate_text: str) -> tuple[str, str]:
    frontmatter = _frontmatter(gate_text)
    section = _extract_section(gate_text, [r"scope card", r"revised searchable scope"])
    scope_text = section[0] if section else gate_text[:4000]
    scope_hash = frontmatter.get("scope_hash") or stable_hash({"scope": scope_text})
    return scope_hash, scope_text


def _make_candidate(path: Path, source_type: str, query: Counter[str], *, full_source: bool = False) -> Candidate | None:
    try:
        text = read_text(path)
    except (OSError, UnicodeDecodeError):
        return None
    claim, locator, score, matched = _best_paragraph(text, query)
    if not claim or score <= 0:
        return None
    category = _category(f"{path.stem} {claim}")
    source_bonus = {"wiki": 3.0, "source": 2.0, "related_idea": 1.0}.get(source_type, 0.0)
    return Candidate(source_type, path, claim, locator, category, score + source_bonus, matched, full_source)


def _gate_candidate(path: Path, text: str, query: Counter[str]) -> Candidate | None:
    section = _extract_section(text, [r"nearest-neighbor", r"already-done memo", r"closest paper"])
    if not section:
        return None
    section_text, start, end = section
    claim, inner_locator, score, matched = _best_paragraph(section_text, query)
    if not claim:
        claim = re.sub(r"\s+", " ", section_text)[:700]
    return Candidate(
        "s2_gate",
        path,
        claim,
        f"lines {start}-{end} ({inner_locator})",
        "nearest",
        max(100.0, score + 50.0),
        matched,
    )


def _select_diverse(candidates: list[Candidate], mode: str, limit: int, max_full_sources: int) -> list[Candidate]:
    if limit < 1:
        raise ValueError("max_packets must be at least 1")
    if max_full_sources < 0:
        raise ValueError("max_full_sources cannot be negative")
    candidates = sorted(candidates, key=lambda item: (-item.score, item.source_type, str(item.path)))
    selected: list[Candidate] = []
    selected_keys: set[tuple[str, str]] = set()
    full_count = 0

    def add(candidate: Candidate) -> bool:
        nonlocal full_count
        key = (str(candidate.path.resolve()), candidate.locator)
        if key in selected_keys:
            return False
        if candidate.full_source and full_count >= max_full_sources:
            return False
        selected.append(candidate)
        selected_keys.add(key)
        full_count += int(candidate.full_source)
        return True

    for category in _CATEGORY_ORDER.get(mode, _CATEGORY_ORDER["general"]):
        if len(selected) >= limit:
            break
        candidate = next((item for item in candidates if item.category == category and (str(item.path.resolve()), item.locator) not in selected_keys), None)
        if candidate:
            add(candidate)
    for candidate in candidates:
        if len(selected) >= limit:
            break
        add(candidate)
    return selected[:limit]


def build_idea_context(
    *,
    idea_vault: str | Path,
    pkb_vault: str | Path,
    slug: str,
    objective: str,
    mode: str = "general",
    max_packets: int = 8,
    max_full_sources: int = 3,
) -> dict[str, Any]:
    if not slug_is_safe(slug):
        raise ValueError(f"Unsafe idea slug: {slug!r}")
    objective = objective.strip()
    if not objective:
        raise ValueError("An explicit objective is required")
    idea_vault = Path(idea_vault)
    pkb_vault = Path(pkb_vault)
    idea_path = idea_vault / "ideas" / f"{slug}.md"
    if not idea_path.exists():
        raise FileNotFoundError(idea_path)

    retrieval_order: list[str] = []
    authoritative_inputs: list[dict[str, Any]] = []
    idea_text = read_text(idea_path)
    retrieval_order.append("target_idea")
    authoritative_inputs.append({**_artifact_ref(idea_path, "idea", "full file"), "authority": "canonical_idea"})

    gate_path = idea_vault / "ideas" / "reviews" / f"{slug}-s2-gate.md"
    gate_text = ""
    scope_hash: str | None = None
    scope_text = ""
    if gate_path.exists():
        gate_text = read_text(gate_path)
        scope_hash, scope_text = _scope_from_gate(gate_text)
        authoritative_inputs.append({**_artifact_ref(gate_path, "s2_gate", "full file"), "authority": "authoritative_s2_gate"})
    retrieval_order.append("authoritative_s2_gate")

    session_dir = idea_vault / "ideas" / "sessions"
    session_path = _latest_session(session_dir, slug)
    session: dict[str, Any] = {}
    if session_path:
        try:
            session = read_json(session_path)
            authoritative_inputs.append({**_artifact_ref(session_path, "idea_session", "full file"), "authority": "latest_session"})
        except (OSError, ValueError, json.JSONDecodeError):
            session = {}
    retrieval_order.append("latest_session")

    if scope_hash is None:
        scope_hash = session.get("scope_hash") or stable_hash({"idea": idea_text})

    query: Counter[str] = Counter()
    _add_query_terms(query, objective, 8.0)
    _add_query_terms(query, mode, 7.0)
    if gate_text:
        _add_query_terms(query, scope_text, 6.0)
    session_text = " ".join(
        str(session.get(field, ""))
        for field in ("objective", "agreed", "contested", "open_questions", "candidate_delta", "next_decision")
    )
    _add_query_terms(query, session_text, 4.0)
    idea_scope = _extract_section(idea_text, [r"original idea", r"research question", r"scope"])
    _add_query_terms(query, idea_scope[0] if idea_scope else idea_text[:6000], 2.0)
    retrieval_order.append("explicit_objective_and_mode")

    candidates: list[Candidate] = []
    if gate_text:
        candidate = _gate_candidate(gate_path, gate_text, query)
        if candidate:
            candidates.append(candidate)

    wiki_dir = pkb_vault / "wiki"
    wiki_index = wiki_dir / "index.md"
    wiki_names: list[str] = []
    if wiki_index.exists():
        index_text = read_text(wiki_index)
        entries = re.findall(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\](?:\s*[-—–:]\s*(.*))?", index_text)
        ranked_entries = []
        for name, summary in entries:
            entry_score, _ = _score(f"{name} {summary}", query)
            ranked_entries.append((entry_score, name.strip()))
        wiki_names = [name for score, name in sorted(ranked_entries, key=lambda item: (-item[0], item[1])) if score > 0][:24]
    retrieval_order.append("pkb_wiki_index")

    linked_source_names: set[str] = set()
    seen_wiki: set[Path] = set()
    for name in wiki_names:
        path = wiki_dir / f"{name}.md"
        try:
            ensure_within(path, wiki_dir)
        except ValueError:
            continue
        if path.exists():
            seen_wiki.add(path.resolve())
            text = read_text(path)
            linked_source_names.update(re.findall(r"sources[/\\]([^`\])>\n]+?\.md)", text, flags=re.I))
            candidate = _make_candidate(path, "wiki", query)
            if candidate:
                candidates.append(candidate)
    if wiki_dir.exists():
        for path in sorted(wiki_dir.glob("*.md")):
            if path.name in {"index.md", "log.md"} or path.resolve() in seen_wiki:
                continue
            candidate = _make_candidate(path, "wiki", query)
            if candidate and candidate.score >= 8:
                candidates.append(candidate)
    retrieval_order.append("pkb_wiki_pages")

    sources_dir = pkb_vault / "sources"
    source_paths: list[Path] = []
    for name in sorted(linked_source_names):
        path = sources_dir / name
        try:
            ensure_within(path, sources_dir)
        except ValueError:
            continue
        if path.exists():
            source_paths.append(path)
    if sources_dir.exists():
        for path in sorted(sources_dir.glob("*.md")):
            if path not in source_paths:
                source_paths.append(path)
    source_candidates: list[Candidate] = []
    for path in source_paths:
        candidate = _make_candidate(path, "source", query, full_source=True)
        if candidate:
            if path.name in linked_source_names:
                candidate.score += 4.0
            source_candidates.append(candidate)
    candidates.extend(sorted(source_candidates, key=lambda item: -item.score)[: max(12, max_full_sources * 4)])
    retrieval_order.append("pkb_sources")

    ideas_dir = idea_vault / "ideas"
    if ideas_dir.exists():
        for path in sorted(ideas_dir.glob("*.md")):
            if path == idea_path or path.name.startswith("_") or path.name in {"index.md", "log.md", "idea-map.md"}:
                continue
            candidate = _make_candidate(path, "related_idea", query)
            if candidate and candidate.score >= 5:
                candidates.append(candidate)
    retrieval_order.append("related_ideas")

    selected = _select_diverse(candidates, mode, max_packets, max_full_sources)
    packets: list[dict[str, Any]] = []
    for candidate in selected:
        source_ref = _artifact_ref(candidate.path, candidate.source_type, candidate.locator)
        claim_id = f"claim:{stable_hash({'source': source_ref['artifact_id'], 'locator': candidate.locator, 'claim': candidate.claim}, length=20)}"
        packets.append(
            {
                "schema_version": SCHEMA_VERSION,
                "claim_id": claim_id,
                "category": candidate.category,
                "claim": candidate.claim,
                "evidence_state": "reported" if candidate.source_type in {"source", "s2_gate"} else "synthesized",
                "scope_hash": scope_hash,
                "score": round(candidate.score, 3),
                "matched_terms": candidate.matched_terms,
                "why_retrieved": f"Matched {', '.join(candidate.matched_terms[:5]) or 'authoritative gate context'}",
                "source_ref": source_ref,
                "actor": "deterministic_retriever",
            }
        )

    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "context_id": f"context:{stable_hash({'slug': slug, 'objective': objective, 'mode': mode, 'scope_hash': scope_hash, 'inputs': authoritative_inputs}, length=20)}",
        "created_at": utc_now(),
        "slug": slug,
        "mode": mode,
        "objective": objective,
        "scope_hash": scope_hash,
        "authoritative_inputs": authoritative_inputs,
        "retrieval_order": retrieval_order,
        "query_terms": [
            {"term": term, "weight": weight}
            for term, weight in sorted(query.items(), key=lambda item: (-item[1], item[0]))[:60]
        ],
        "packets": packets,
        "limits": {"max_packets": max_packets, "max_full_sources": max_full_sources},
        "stats": {
            "candidate_count": len(candidates),
            "packet_count": len(packets),
            "full_source_count": sum(packet["source_ref"]["source_type"] == "source" for packet in packets),
            "categories": dict(Counter(packet["category"] for packet in packets)),
        },
        "session_stale": bool(session.get("stale")) or bool(session.get("scope_hash") and session.get("scope_hash") != scope_hash),
    }
    return manifest


def render_context_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        f"# Idea Context: {manifest['slug']}",
        "",
        f"- Mode: `{manifest['mode']}`",
        f"- Objective: {manifest['objective']}",
        f"- Scope hash: `{manifest['scope_hash']}`",
        f"- Packets: {manifest['stats']['packet_count']} (full sources: {manifest['stats']['full_source_count']})",
        "",
        "## Authoritative inputs",
        "",
    ]
    for item in manifest["authoritative_inputs"]:
        lines.append(f"- `{item['authority']}`: `{item['path']}` ({item['locator']})")
    lines.extend(["", "## Evidence packets", ""])
    for index, packet in enumerate(manifest["packets"], start=1):
        claim = packet["claim"].replace("\n", " ")
        lines.extend(
            [
                f"### {index}. {packet['category']} — `{packet['claim_id']}`",
                "",
                claim,
                "",
                f"Source: `{packet['source_ref']['path']}` ({packet['source_ref']['locator']})",
                f"Matched: {', '.join(packet['matched_terms']) or 'authoritative gate context'}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def write_context_manifest(
    manifest: dict[str, Any],
    *,
    workspace: str | Path,
    output_format: str = "json",
    filename: str | None = None,
    allowed_root: str | Path | None = None,
) -> Path:
    workspace = Path(workspace)
    if allowed_root is None:
        idea_input = next(
            (item for item in manifest.get("authoritative_inputs", []) if item.get("authority") == "canonical_idea"),
            None,
        )
        if not idea_input:
            raise ValueError("Cannot derive the permitted idea-session workspace")
        allowed_root = Path(idea_input["path"]).parent / "sessions"
    ensure_within(workspace, Path(allowed_root))
    suffix = ".md" if output_format == "markdown" else ".json"
    safe_context = manifest["context_id"].replace(":", "-")
    path = workspace / (filename or f"{safe_context}{suffix}")
    ensure_within(path, workspace)
    if output_format == "markdown":
        atomic_write_text(path, render_context_markdown(manifest))
    elif output_format == "json":
        atomic_write_json(path, manifest)
    else:
        raise ValueError("output_format must be json or markdown")
    return path
