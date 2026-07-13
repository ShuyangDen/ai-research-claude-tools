"""Deterministic core utilities for the paper tracker.

This module deliberately contains no model calls.  It owns the contracts that
must remain stable across model/provider changes: paper identity, compact
recommendation signals, source health, and the structured reading queue.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import json
import math
import os
import re
import tempfile
import time
import unicodedata
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit


LANES = ("exploit", "adjacent", "contradiction", "methodology")
DEFAULT_LANE_WEIGHTS = {
    "exploit": 0.55,
    "adjacent": 0.20,
    "contradiction": 0.15,
    "methodology": 0.10,
}


class SourceFetchError(RuntimeError):
    """A source could not be fetched after retrying transient failures."""

    def __init__(self, source: str, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.source = source
        self.status_code = status_code


class SourceConfigurationError(SourceFetchError):
    """A permanent 4xx/configuration error that must fail the run."""


_EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
_ENCODED_EMAIL_RE = re.compile(
    r"[A-Z0-9._%+-]+%40[A-Z0-9.-]+(?:%2E|\.)[A-Z]{2,}",
    re.IGNORECASE,
)
_QUERY_VALUE_RE = re.compile(r"([?&][A-Z0-9_.~-]+)=([^&\s)\]}]+)", re.IGNORECASE)
_CREDENTIAL_VALUE_RE = re.compile(
    r"\b(api[_-]?key|token|password|secret)\s*[:=]\s*([^\s,;]+)",
    re.IGNORECASE,
)


def safe_error_summary(error: BaseException, *, max_length: int = 500) -> str:
    """Return a useful error summary without leaking addresses or request data."""

    message = str(error)
    message = _EMAIL_RE.sub("[redacted-email]", message)
    message = _ENCODED_EMAIL_RE.sub("[redacted-email]", message)
    message = _QUERY_VALUE_RE.sub(r"\1=[redacted]", message)
    message = _CREDENTIAL_VALUE_RE.sub(r"\1=[redacted]", message)
    message = " ".join(message.split())
    if len(message) > max_length:
        message = message[: max_length - 3] + "..."
    kind = type(error).__name__
    return f"{kind}: {message}" if message else kind


def crossref_contact_params(environ: Mapping[str, str] | None = None) -> dict[str, str]:
    """Build optional CrossRef polite-pool params without reusing recipient data."""

    source = os.environ if environ is None else environ
    contact = source.get("PAPER_TRACKER_CONTACT_EMAIL", "").strip()
    if not contact:
        return {}
    parsed = parse_recipients(contact)
    if len(parsed) != 1:
        raise ValueError("PAPER_TRACKER_CONTACT_EMAIL must contain exactly one address")
    return {"mailto": parsed[0]}


def _atomic_write_text(path: str | Path, content: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, target)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def request_with_retry(
    source: str,
    url: str,
    *,
    request_func: Callable[..., Any],
    max_attempts: int = 4,
    backoff_seconds: float = 1.0,
    **kwargs: Any,
) -> Any:
    """Call an HTTP GET function with bounded retry semantics.

    HTTP 400 is treated as a query/configuration bug and never retried.  Other
    non-retryable 4xx errors fail immediately.  429 and 5xx responses retry.
    """

    last_error: BaseException | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = request_func(url, **kwargs)
            status = int(getattr(response, "status_code", 200))
            if status == 400:
                raise SourceConfigurationError(
                    source,
                    f"{source} returned HTTP 400; check query/filter configuration",
                    status_code=status,
                )
            if 400 <= status < 500 and status != 429:
                raise SourceFetchError(
                    source,
                    f"{source} returned non-retryable HTTP {status}",
                    status_code=status,
                )
            if status == 429 or status >= 500:
                raise SourceFetchError(
                    source,
                    f"{source} returned retryable HTTP {status}",
                    status_code=status,
                )
            response.raise_for_status()
            return response
        except SourceConfigurationError:
            raise
        except SourceFetchError as exc:
            last_error = exc
            retryable = exc.status_code == 429 or (exc.status_code or 0) >= 500
            if not retryable or attempt == max_attempts:
                raise
        except Exception as exc:  # requests connection/timeout exceptions
            last_error = exc
            if attempt == max_attempts:
                raise SourceFetchError(
                    source,
                    f"{source} request failed ({safe_error_summary(exc)})",
                ) from None

        time.sleep(backoff_seconds * (2 ** (attempt - 1)))

    if last_error is None:
        raise SourceFetchError(source, f"{source} request failed")
    raise SourceFetchError(
        source,
        f"{source} request failed ({safe_error_summary(last_error)})",
    ) from None


def fetch_feed_with_retry(
    source: str,
    url: str,
    *,
    request_func: Callable[..., Any],
    feed_parser: Callable[[bytes], Any],
    timeout: int = 30,
) -> Any:
    response = request_with_retry(
        source,
        url,
        request_func=request_func,
        timeout=timeout,
        headers={"User-Agent": "ai-economics-paper-tracker/3.0"},
    )
    feed = feed_parser(response.content)
    if getattr(feed, "bozo", False) and not getattr(feed, "entries", []):
        error = getattr(feed, "bozo_exception", "invalid feed")
        raise SourceFetchError(source, f"{source} feed parse failed: {error}")
    return feed


@dataclasses.dataclass
class RecommendationProfile:
    retrieval_terms: list[str] = dataclasses.field(default_factory=list)
    lane_weights: dict[str, float] = dataclasses.field(default_factory=dict)
    tier_1_signal_ids: list[str] = dataclasses.field(default_factory=list)
    active_signals: list[dict[str, Any]] = dataclasses.field(default_factory=list)
    current_interests: list[dict[str, Any]] = dataclasses.field(default_factory=list)
    reading_preferences: list[dict[str, Any]] = dataclasses.field(default_factory=list)
    negative_signals: list[str] = dataclasses.field(default_factory=list)

    def compact_prompt(self, max_chars: int = 5000) -> str:
        payload = {
            "retrieval_terms": self.retrieval_terms[:20],
            "tier_1_signal_ids": self.tier_1_signal_ids[:20],
            "active_signals": self.active_signals[:20],
            "current_interests": self.current_interests[:12],
            "reading_preferences": self.reading_preferences[:12],
            "negative_signals": self.negative_signals[:12],
        }
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        # Never slice serialized JSON: a compact prompt must remain machine
        # readable. Drop lowest-priority tail signals until it fits.
        trim_order = (
            "reading_preferences",
            "current_interests",
            "active_signals",
            "negative_signals",
            "retrieval_terms",
        )
        while len(encoded) > max_chars:
            field = next((name for name in trim_order if payload[name]), None)
            if field is None:
                return "{}"
            payload[field].pop()
            active_ids = {
                str(item.get("id", "")) for item in payload["active_signals"]
            }
            payload["tier_1_signal_ids"] = [
                signal_id
                for signal_id in payload["tier_1_signal_ids"]
                if signal_id in active_ids
            ]
            encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        return encoded


def _section(markdown: str, heading: str) -> str:
    pattern = re.compile(
        rf"(?ms)^##\s+{re.escape(heading)}\s*$\n(.*?)(?=^##\s+|\Z)",
        re.IGNORECASE,
    )
    match = pattern.search(markdown)
    return match.group(1).strip() if match else ""


def _clean_signal_line(line: str) -> str:
    line = re.sub(r"^\s*(?:[-*+] |\d+[.)]\s*)", "", line).strip()
    line = re.sub(r"\*+", "", line)
    return re.sub(r"\s+", " ", line).strip()


def _signals_from_section(markdown: str, heading: str, prefix: str, limit: int) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for line in _section(markdown, heading).splitlines():
        if not re.match(r"^\s*(?:[-*+] |\d+[.)]\s*)", line):
            continue
        text = _clean_signal_line(line)
        if not text or text.startswith("(") or "<" in text:
            continue
        digest = hashlib.sha256(text.casefold().encode("utf-8")).hexdigest()[:10]
        result.append({"id": f"{prefix}:{digest}", "text": text[:360], "weight": 1.0})
        if len(result) >= limit:
            break
    return result


def _retrieval_terms_from_markdown(markdown: str) -> list[str]:
    section = _section(markdown, "Retrieval Terms")
    terms: list[str] = []
    for line in section.splitlines():
        cleaned = _clean_signal_line(line).strip("`\"'")
        if cleaned and not cleaned.startswith("(") and "<" not in cleaned:
            terms.extend(part.strip() for part in re.split(r"[,;]", cleaned) if part.strip())
    return _unique_terms(terms)


def _unique_terms(terms: Iterable[str], limit: int = 20) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for term in terms:
        normalized = re.sub(r"\s+", " ", str(term)).strip().strip("\"'")
        key = normalized.casefold()
        if not normalized or key in seen or len(normalized) > 100:
            continue
        seen.add(key)
        output.append(normalized)
        if len(output) >= limit:
            break
    return output


def _projection_text(signal: dict[str, Any]) -> str:
    title = re.sub(r"\s+", " ", str(signal.get("title", ""))).strip()
    mechanism = re.sub(r"\s+", " ", str(signal.get("mechanism", ""))).strip()
    return (f"{title}: {mechanism}" if title and mechanism else title or mechanism)[:360]


def _projection_item(signal: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(signal.get("signal_id", "")),
        "text": _projection_text(signal),
        "weight": abs(float(signal.get("projection_score", 0.0))),
        "signal_type": str(signal.get("signal_type", "")),
    }


def _profile_from_projection(data: dict[str, Any]) -> RecommendationProfile:
    """Adapt research-core's five provenance lanes to the compact tracker view."""

    lanes = data.get("lanes")
    if not isinstance(lanes, dict):
        raise ValueError("Profile projection lanes must be an object")

    def lane(name: str) -> list[dict[str, Any]]:
        value = lanes.get(name, [])
        if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
            raise ValueError(f"Profile projection lane {name!r} must be an array of objects")
        return value

    declared = lane("declared")
    portfolio = lane("portfolio")
    inferred = lane("inferred")
    speculative = lane("speculative")
    negative = lane("negative")
    active = [
        signal
        for signal in [*declared, *portfolio]
        if signal.get("tier_1_eligible") and float(signal.get("projection_score", 0.0)) > 0
    ]
    interests = [signal for signal in speculative if float(signal.get("projection_score", 0.0)) > 0]
    preferences = [signal for signal in inferred if float(signal.get("projection_score", 0.0)) > 0]
    retrieval_terms = _unique_terms(
        term
        for signal in [*active, *interests, *preferences]
        for term in signal.get("retrieval_terms", [])
    )
    raw_lane_weights = data.get("recommendation_lane_weights", {})
    if not isinstance(raw_lane_weights, dict):
        raise ValueError("recommendation_lane_weights must be an object")
    lane_weights = {
        str(name): float(weight)
        for name, weight in raw_lane_weights.items()
        if str(name) in LANES and float(weight) >= 0
    }
    active_items = [
        _projection_item(signal) for signal in active if _projection_text(signal)
    ]
    active_ids = {item["id"] for item in active_items}
    raw_tier_1_ids = data.get("tier_1_signal_ids")
    if raw_tier_1_ids is None:
        tier_1_signal_ids = sorted(active_ids)
    elif not isinstance(raw_tier_1_ids, list):
        raise ValueError("tier_1_signal_ids must be an array")
    else:
        tier_1_signal_ids = [
            str(signal_id)
            for signal_id in raw_tier_1_ids
            if str(signal_id) in active_ids
        ]
    return RecommendationProfile(
        retrieval_terms=retrieval_terms,
        lane_weights=lane_weights,
        tier_1_signal_ids=tier_1_signal_ids,
        active_signals=active_items,
        current_interests=[_projection_item(signal) for signal in interests if _projection_text(signal)],
        reading_preferences=[_projection_item(signal) for signal in preferences if _projection_text(signal)],
        negative_signals=[_projection_text(signal) for signal in negative if _projection_text(signal)],
    )


def load_recommendation_profile(
    markdown_path: str | Path,
    structured_path: str | Path | None = None,
) -> RecommendationProfile:
    """Load a compact profile from JSON, falling back to selected MD sections."""

    markdown_file = Path(markdown_path)
    json_file = Path(structured_path) if structured_path else markdown_file.with_name("recommendation_profile.json")
    if json_file.exists():
        data = json.loads(json_file.read_text(encoding="utf-8-sig"))
        if isinstance(data, dict) and "lanes" in data:
            profile = _profile_from_projection(data)
        else:
            allowed = {field.name for field in dataclasses.fields(RecommendationProfile)}
            profile = RecommendationProfile(**{k: v for k, v in data.items() if k in allowed})
    else:
        markdown = markdown_file.read_text(encoding="utf-8-sig") if markdown_file.exists() else ""
        profile = RecommendationProfile(
            retrieval_terms=_retrieval_terms_from_markdown(markdown),
            active_signals=_signals_from_section(markdown, "Active Research Directions", "active", 20),
            current_interests=_signals_from_section(markdown, "Current Interest Signals", "interest", 12),
            reading_preferences=_signals_from_section(markdown, "Reading Preference Signals", "preference", 12),
            negative_signals=[
                signal["text"]
                for signal in _signals_from_section(
                    markdown, "What This Researcher Does NOT Care About", "negative", 12
                )
            ],
        )

    active_ids = {
        str(item.get("id", ""))
        for item in profile.active_signals
        if isinstance(item, dict) and item.get("id")
    }
    if json_file.exists():
        profile.tier_1_signal_ids = [
            str(signal_id)
            for signal_id in profile.tier_1_signal_ids
            if str(signal_id) in active_ids
        ]
    else:
        # The Markdown Active Research Directions section is manually curated;
        # current interests and reading preferences remain ranking-only signals.
        profile.tier_1_signal_ids = sorted(active_ids)

    env_terms = os.environ.get("PAPER_TRACKER_RETRIEVAL_TERMS", "")
    profile.retrieval_terms = _unique_terms(
        [*profile.retrieval_terms, *(term.strip() for term in env_terms.split(","))]
    )
    return profile


def enforce_tier_1_contract(
    tier: int,
    matched_signal: str,
    profile: RecommendationProfile,
) -> int:
    """Deterministically reject model-invented or non-approved Tier 1 matches."""

    if tier != 1:
        return tier
    return 1 if matched_signal in set(profile.tier_1_signal_ids) else 2


_DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
_ARXIV_RE = re.compile(
    r"(?:arxiv:|arxiv\.org/(?:abs|pdf)/)(?P<id>(?:\d{4}\.\d{4,5}|[a-z-]+/\d{7})(?:v\d+)?)",
    re.IGNORECASE,
)
_OPENALEX_RE = re.compile(r"openalex\.org/(?P<id>W\d+)", re.IGNORECASE)
_NBER_RE = re.compile(r"(?:nber\.org/(?:papers/)?|nber\s*:\s*)?(?P<id>w\d{3,})", re.IGNORECASE)
_TRACKING_QUERY_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid", "ref", "source"}


def _normalize_doi(value: str) -> str:
    decoded = unquote(value or "")
    match = _DOI_RE.search(decoded)
    if not match:
        return ""
    return match.group(0).rstrip(".,;)]}").casefold()


def _normalize_arxiv(value: str) -> str:
    match = _ARXIV_RE.search(unquote(value or ""))
    if not match:
        raw = (value or "").strip()
        if re.fullmatch(r"(?:\d{4}\.\d{4,5}|[a-z-]+/\d{7})(?:v\d+)?", raw, re.IGNORECASE):
            return raw.casefold()
        return ""
    return match.group("id").casefold()


def _normalize_openalex(value: str) -> str:
    raw = (value or "").strip()
    if re.fullmatch(r"W\d+", raw, re.IGNORECASE):
        return raw.upper()
    match = _OPENALEX_RE.search(raw)
    return match.group("id").upper() if match else ""


def _normalize_nber(value: str) -> str:
    match = _NBER_RE.search((value or "").strip())
    return match.group("id").casefold() if match else ""


def normalize_url(value: str) -> str:
    if not value:
        return ""
    parts = urlsplit(value.strip())
    scheme = parts.scheme.casefold()
    if scheme not in {"http", "https"} or not parts.netloc:
        return value.strip().casefold()
    host = (parts.hostname or "").casefold()
    port = parts.port
    netloc = host
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{host}:{port}"
    path = re.sub(r"/{2,}", "/", parts.path or "/")
    if path != "/":
        path = path.rstrip("/")
    query = [
        (key, item_value)
        for key, item_value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.casefold().startswith("utm_") and key.casefold() not in _TRACKING_QUERY_KEYS
    ]
    query.sort()
    return urlunsplit((scheme, netloc, path, urlencode(query), ""))


def normalize_title(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value or "").casefold()
    normalized = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", normalized)
    return " ".join(normalized.split())


def stable_paper_id(
    *,
    title: str,
    url: str = "",
    doi: str = "",
    arxiv_id: str = "",
    openalex_id: str = "",
    nber_id: str = "",
) -> str:
    """Return a stable identifier with explicit identifier priority."""

    normalized_doi = _normalize_doi(doi) or _normalize_doi(url)
    if normalized_doi:
        return f"doi:{normalized_doi}"
    normalized_arxiv = _normalize_arxiv(arxiv_id) or _normalize_arxiv(url)
    if normalized_arxiv:
        # Version suffixes should not create a new logical paper.
        normalized_arxiv = re.sub(r"v\d+$", "", normalized_arxiv)
        return f"arxiv:{normalized_arxiv}"
    normalized_openalex = _normalize_openalex(openalex_id) or _normalize_openalex(url)
    if normalized_openalex:
        return f"openalex:{normalized_openalex}"
    normalized_nber = _normalize_nber(nber_id) or _normalize_nber(url)
    if normalized_nber:
        return f"nber:{normalized_nber}"
    normalized_url = normalize_url(url)
    if normalized_url:
        digest = hashlib.sha256(normalized_url.encode("utf-8")).hexdigest()[:20]
        return f"url-sha256:{digest}"
    normalized_title = normalize_title(title)
    digest = hashlib.sha256(normalized_title.encode("utf-8")).hexdigest()[:20]
    return f"title-sha256:{digest}"


def stratified_evaluation_sample(
    papers: Sequence[Any],
    limit: int,
) -> list[Any]:
    """Bound model calls with a deterministic recent-paper round robin by source."""

    if limit <= 0:
        raise ValueError("evaluation limit must be positive")
    if len(papers) <= limit:
        return list(papers)

    buckets: dict[str, list[Any]] = {}
    for paper in papers:
        source = str(getattr(paper, "source", "") or "unknown").strip().casefold()
        buckets.setdefault(source, []).append(paper)
    for bucket in buckets.values():
        bucket.sort(
            key=lambda paper: (
                str(getattr(paper, "published", "") or ""),
                normalize_title(str(getattr(paper, "title", "") or "")),
                normalize_url(str(getattr(paper, "url", "") or "")),
            ),
            reverse=True,
        )

    positions = {source: 0 for source in buckets}
    selected: list[Any] = []
    source_order = sorted(buckets)
    while len(selected) < limit:
        progressed = False
        for source in source_order:
            position = positions[source]
            if position >= len(buckets[source]):
                continue
            selected.append(buckets[source][position])
            positions[source] += 1
            progressed = True
            if len(selected) == limit:
                break
        if not progressed:
            break
    return selected


def parse_recipients(value: str | Sequence[str]) -> list[str]:
    """Parse a recipient list without ever formatting it for logs."""

    raw = value.split(",") if isinstance(value, str) else value
    recipients: list[str] = []
    seen: set[str] = set()
    for item in raw:
        recipient = str(item).strip()
        key = recipient.casefold()
        if not recipient or key in seen:
            continue
        seen.add(key)
        recipients.append(recipient)
    if not recipients:
        raise ValueError("at least one email recipient is required")
    return recipients


def default_lane(*, tier: int, matched_signal: str = "", methodology: str = "") -> str:
    if tier == 3 or "method" in methodology.casefold():
        return "methodology"
    signal_family = matched_signal.partition(":")[0].casefold()
    if signal_family in {
        "active",
        "active_direction",
        "current_interest",
        "interest",
        "preference",
        "reading_preference",
    }:
        return "exploit"
    return "adjacent"


@dataclasses.dataclass
class QueueRecord:
    paper_id: str
    candidate_slug: str
    title: str
    tier: int
    lane: str
    matched_signal: str
    authors: str
    venue: str
    url: str
    published: str
    added: str
    last_seen: str
    status: str = "queued"
    score: float = 0.0
    source: str = ""
    identifiers: dict[str, str] = dataclasses.field(default_factory=dict)
    schema_version: str = "1.0"


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9\s-]", "", title.casefold())
    return re.sub(r"\s+", "-", slug.strip())[:60] or "untitled-paper"


def record_from_paper(paper: Any, today: str) -> QueueRecord:
    identifiers = {
        key: str(getattr(paper, key, "") or "")
        for key in ("doi", "arxiv_id", "openalex_id", "nber_id")
        if getattr(paper, key, "")
    }
    paper_id = getattr(paper, "paper_id", "") or stable_paper_id(
        title=getattr(paper, "title", ""),
        url=getattr(paper, "url", ""),
        doi=identifiers.get("doi", ""),
        arxiv_id=identifiers.get("arxiv_id", ""),
        openalex_id=identifiers.get("openalex_id", ""),
        nber_id=identifiers.get("nber_id", ""),
    )
    tier = int(getattr(paper, "tier", 2))
    matched_signal = str(getattr(paper, "matched_signal", "") or "")
    methodology = str(getattr(paper, "methodology", "") or "")
    lane = str(getattr(paper, "lane", "") or default_lane(
        tier=tier, matched_signal=matched_signal, methodology=methodology
    ))
    if lane not in LANES:
        lane = default_lane(tier=tier, matched_signal=matched_signal, methodology=methodology)
    return QueueRecord(
        paper_id=paper_id,
        candidate_slug=_slugify(str(getattr(paper, "title", ""))),
        title=str(getattr(paper, "title", "")),
        tier=tier,
        lane=lane,
        matched_signal=matched_signal,
        authors=str(getattr(paper, "authors", "") or ""),
        venue=str(getattr(paper, "venue", "") or ""),
        url=str(getattr(paper, "url", "") or ""),
        published=str(getattr(paper, "published", "") or ""),
        added=today,
        last_seen=today,
        score=float(getattr(paper, "recommendation_score", 0.0) or 0.0),
        source=str(getattr(paper, "source", "") or ""),
        identifiers=identifiers,
    )


def _parse_legacy_markdown(path: str | Path) -> list[QueueRecord]:
    legacy = Path(path)
    if not legacy.exists():
        return []
    result: list[QueueRecord] = []
    header: list[str] = []
    for line in legacy.read_text(encoding="utf-8-sig").splitlines():
        if not line.lstrip().startswith("|"):
            continue
        columns = [column.strip() for column in line.split("|")[1:-1]]
        lowered = [column.casefold() for column in columns]
        if "candidate-slug" in lowered:
            header = lowered
            continue
        if all(re.fullmatch(r":?-+:?", column) for column in columns):
            continue
        if header:
            values = dict(zip(header, columns))
            slug = values.get("candidate-slug", "")
            title = values.get("title", "")
            tier_raw = values.get("tier", "2")
            authors = values.get("authors", "")
            venue = values.get("venue", "")
            url = values.get("url", "")
            added = values.get("added", "")
            direction = values.get("direction", "")
        elif len(columns) >= 7:
            slug, title, tier_raw, authors, venue, url, added = columns[:7]
            direction = ""
        else:
            continue
        if not title:
            continue
        try:
            tier_match = re.search(r"\d+", tier_raw)
            tier = int(tier_match.group(0)) if tier_match else 2
        except (AttributeError, ValueError):
            continue
        added = added or dt.date.today().isoformat()
        result.append(
            QueueRecord(
                paper_id=stable_paper_id(title=title, url=url),
                candidate_slug=slug or _slugify(title),
                title=title,
                tier=tier,
                lane=default_lane(tier=tier),
                matched_signal=f"manual:{direction}" if direction else "legacy",
                authors=authors,
                venue=venue,
                url=url,
                published="",
                added=added,
                last_seen=added,
            )
        )
    return result


def load_queue_state(state_path: str | Path, legacy_path: str | Path) -> list[QueueRecord]:
    state = Path(state_path)
    if not state.exists():
        return _parse_legacy_markdown(legacy_path)
    records: list[QueueRecord] = []
    for line_number, line in enumerate(state.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
            records.append(QueueRecord(**raw))
        except (json.JSONDecodeError, TypeError) as exc:
            raise ValueError(f"Invalid queue state at {state}:{line_number}: {exc}") from exc
    return records


def parse_lane_weights(value: str | None) -> dict[str, float]:
    if not value:
        return dict(DEFAULT_LANE_WEIGHTS)
    parsed: dict[str, float] = {lane: 0.0 for lane in LANES}
    for item in value.split(","):
        lane, separator, raw_weight = item.partition(":")
        lane = lane.strip()
        if not separator or lane not in parsed:
            raise ValueError(f"Invalid lane mix item: {item!r}")
        parsed[lane] = float(raw_weight)
    if sum(parsed.values()) <= 0:
        raise ValueError("Lane weights must sum to more than zero")
    return parsed


def _lane_quotas(max_new: int, weights: Mapping[str, float]) -> dict[str, int]:
    total = sum(max(0.0, float(weights.get(lane, 0.0))) for lane in LANES)
    raw = {lane: max_new * max(0.0, float(weights.get(lane, 0.0))) / total for lane in LANES}
    quotas = {lane: math.floor(value) for lane, value in raw.items()}
    remainder = max_new - sum(quotas.values())
    for lane in sorted(LANES, key=lambda item: raw[item] - quotas[item], reverse=True)[:remainder]:
        quotas[lane] += 1
    return quotas


def _candidate_sort_key(record: QueueRecord) -> tuple[Any, ...]:
    try:
        published_ordinal = dt.date.fromisoformat(record.published[:10]).toordinal()
    except (TypeError, ValueError):
        published_ordinal = 0
    return (-record.score, record.tier, -published_ordinal, record.paper_id)


def select_new_records(
    candidates: Sequence[QueueRecord],
    *,
    max_new: int,
    lane_weights: Mapping[str, float],
) -> list[QueueRecord]:
    if max_new <= 0:
        return []
    quotas = _lane_quotas(max_new, lane_weights)
    by_lane = {
        lane: sorted((record for record in candidates if record.lane == lane), key=_candidate_sort_key)
        for lane in LANES
    }
    selected: list[QueueRecord] = []
    selected_ids: set[str] = set()
    for lane in LANES:
        for record in by_lane[lane][: quotas[lane]]:
            if record.paper_id not in selected_ids:
                selected.append(record)
                selected_ids.add(record.paper_id)
    if len(selected) < max_new:
        leftovers = sorted(
            (record for record in candidates if record.paper_id not in selected_ids),
            key=_candidate_sort_key,
        )
        selected.extend(leftovers[: max_new - len(selected)])
    return sorted(selected, key=_candidate_sort_key)


def _markdown_safe(value: str) -> str:
    return value.replace("|", "/").replace("\n", " ").strip()


def render_legacy_queue(records: Sequence[QueueRecord]) -> str:
    active = [record for record in records if record.status not in {"completed", "dismissed", "skipped"}]

    def display_key(record: QueueRecord) -> tuple[Any, ...]:
        try:
            added_ordinal = dt.date.fromisoformat(record.added[:10]).toordinal()
        except (TypeError, ValueError):
            added_ordinal = 0
        return (record.tier, -added_ordinal, record.candidate_slug)

    active.sort(key=display_key)
    header = (
        "# Reading Queue\n\n"
        "Derived compatibility view. Canonical state: `queue_state.jsonl`.\n\n"
        "Tier 1 = priority read. Tier 2 = adjacent/general fit. "
        "Tier 3 = methodology.\n\n"
        "| candidate-slug | title | tier | authors | venue | url | added |\n"
        "|----------------|-------|------|---------|-------|-----|-------|\n"
    )
    rows = [
        "| "
        + " | ".join(
            [
                _markdown_safe(record.candidate_slug),
                _markdown_safe(record.title),
                str(record.tier),
                _markdown_safe(record.authors),
                _markdown_safe(record.venue),
                _markdown_safe(record.url),
                _markdown_safe(record.added),
            ]
        )
        + " |"
        for record in active
    ]
    return header + "\n".join(rows) + ("\n" if rows else "")


def update_queue_state(
    papers: Sequence[Any],
    *,
    state_path: str | Path = "queue_state.jsonl",
    markdown_path: str | Path = "reading_queue.md",
    max_new: int = 15,
    lane_weights: Mapping[str, float] | None = None,
    today: str | None = None,
) -> dict[str, Any]:
    """Merge candidates into canonical state and regenerate the legacy view."""

    today = today or dt.date.today().isoformat()
    existing = load_queue_state(state_path, markdown_path)
    by_id = {record.paper_id: record for record in existing}
    by_url = {
        normalize_url(record.url): record.paper_id
        for record in existing
        if normalize_url(record.url)
    }
    by_title = {
        normalize_title(record.title): record.paper_id
        for record in existing
        if len(normalize_title(record.title)) >= 20
    }
    candidates: list[QueueRecord] = []
    candidate_objects: dict[str, Any] = {}
    for paper in papers:
        record = record_from_paper(paper, today)
        matched_id = record.paper_id
        if matched_id not in by_id:
            matched_id = by_url.get(normalize_url(record.url), "")
        if matched_id not in by_id and len(normalize_title(record.title)) >= 20:
            matched_id = by_title.get(normalize_title(record.title), "")

        if matched_id in by_id:
            current = by_id[matched_id]
            # Upgrade a legacy URL/title identity when a stronger identifier
            # later becomes available, while preserving terminal queue state.
            priority = {
                "title": 0,
                "title-sha256": 0,
                "url": 1,
                "url-sha256": 1,
                "nber": 2,
                "openalex": 3,
                "arxiv": 4,
                "doi": 5,
            }
            old_kind = current.paper_id.partition(":")[0]
            new_kind = record.paper_id.partition(":")[0]
            canonicalizes_legacy_hash = (old_kind, new_kind) in {
                ("url", "url-sha256"),
                ("title", "title-sha256"),
            }
            if priority.get(new_kind, -1) > priority.get(old_kind, -1) or canonicalizes_legacy_hash:
                del by_id[matched_id]
                current.paper_id = record.paper_id
                by_id[current.paper_id] = current
                by_url = {
                    key: current.paper_id if value == matched_id else value
                    for key, value in by_url.items()
                }
                by_title = {
                    key: current.paper_id if value == matched_id else value
                    for key, value in by_title.items()
                }
            current.last_seen = today
            current.tier = record.tier
            current.lane = record.lane
            current.matched_signal = record.matched_signal
            current.score = record.score
            current.url = record.url or current.url
            current.identifiers.update(record.identifiers)
            candidate_objects[current.paper_id] = paper
        else:
            candidates.append(record)
            candidate_objects[record.paper_id] = paper

    selected = select_new_records(
        candidates,
        max_new=max_new,
        lane_weights=lane_weights or DEFAULT_LANE_WEIGHTS,
    )
    for record in selected:
        by_id[record.paper_id] = record

    records = sorted(by_id.values(), key=lambda record: (record.added, record.paper_id))
    state_content = "".join(
        json.dumps(dataclasses.asdict(record), ensure_ascii=False, sort_keys=True) + "\n"
        for record in records
    )
    _atomic_write_text(state_path, state_content)
    _atomic_write_text(markdown_path, render_legacy_queue(records))

    lane_counts = {lane: sum(1 for record in selected if record.lane == lane) for lane in LANES}
    return {
        "added": len(selected),
        "selected_ids": [record.paper_id for record in selected],
        "selected_papers": [candidate_objects[record.paper_id] for record in selected],
        "lane_counts": lane_counts,
        "total_active": sum(
            1 for record in records if record.status not in {"completed", "dismissed", "skipped"}
        ),
    }


@dataclasses.dataclass
class SourceHealthReport:
    run_date: str
    started_at: str = dataclasses.field(default_factory=lambda: dt.datetime.now(dt.timezone.utc).isoformat())
    completed_at: str = ""
    status: str = "running"
    sources: dict[str, dict[str, Any]] = dataclasses.field(default_factory=dict)
    errors: list[str] = dataclasses.field(default_factory=list)

    def success(self, source: str, count: int, *, core: bool) -> None:
        self.sources[source] = {"status": "ok", "count": count, "core": core}

    def failure(self, source: str, error: BaseException, *, core: bool) -> None:
        permanent = isinstance(error, SourceConfigurationError)
        safe_error = safe_error_summary(error)
        self.sources[source] = {
            "status": "failed",
            "count": 0,
            "core": core,
            "permanent": permanent,
            "status_code": getattr(error, "status_code", None),
            "error": safe_error,
        }
        self.errors.append(f"{source}: {safe_error}")

    @property
    def core_failures(self) -> int:
        return sum(
            1 for entry in self.sources.values() if entry.get("core") and entry.get("status") == "failed"
        )

    @property
    def permanent_failure(self) -> bool:
        return any(entry.get("permanent") for entry in self.sources.values())

    def finalize(self, *, failure_threshold: int) -> str:
        self.completed_at = dt.datetime.now(dt.timezone.utc).isoformat()
        failures = sum(1 for entry in self.sources.values() if entry.get("status") == "failed")
        if self.permanent_failure or self.core_failures >= failure_threshold:
            self.status = "failed"
        elif failures:
            self.status = "degraded"
        else:
            self.status = "ok"
        return self.status

    def write(self, path: str | Path) -> None:
        _atomic_write_text(
            path,
            json.dumps(dataclasses.asdict(self), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )
