"""Canonical scholarly-work identifiers shared by queue, tutor, PKB, and ideas."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from typing import Mapping
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit


_TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "source",
}


def normalize_doi(value: str) -> str:
    value = unquote(value.strip())
    value = re.sub(r"^(?:doi\s*:\s*|https?://(?:dx\.)?doi\.org/)", "", value, flags=re.I)
    match = re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", value, flags=re.I)
    if not match:
        raise ValueError(f"Invalid DOI: {value!r}")
    return match.group(0).rstrip(".,;:)]}").lstrip("([{").lower()


def normalize_openalex(value: str) -> str:
    raw = value.strip()
    match = re.fullmatch(r"[Ww]\d{3,}", raw)
    if not match:
        match = re.search(r"(?:openalex\.org/|openalex\s*:\s*)([Ww]\d{3,})", raw)
    if not match:
        raise ValueError(f"Invalid OpenAlex work ID: {value!r}")
    return match.group(0).upper() if re.fullmatch(r"[Ww]\d{3,}", raw) else match.group(1).upper()


def normalize_arxiv(value: str) -> str:
    value = value.strip()
    value = re.sub(r"^https?://arxiv\.org/(?:abs|pdf)/", "", value, flags=re.I)
    value = re.sub(r"^(?:arxiv\s*:\s*)", "", value, flags=re.I)
    value = re.sub(r"\.pdf$", "", value, flags=re.I)
    value = re.sub(r"v\d+$", "", value, flags=re.I)
    if not re.fullmatch(r"(?:\d{4}\.\d{4,5}|[a-z-]+/\d{7})", value, flags=re.I):
        raise ValueError(f"Invalid arXiv ID: {value!r}")
    return value.lower()


def normalize_nber(value: str) -> str:
    raw = value.strip()
    match = re.fullmatch(r"w\d{3,}", raw, flags=re.I)
    if not match:
        match = re.search(r"(?:nber\.org/(?:papers/)?|nber\s*:\s*)(w\d{3,})", raw, flags=re.I)
    if not match:
        raise ValueError(f"Invalid NBER work ID: {value!r}")
    return match.group(0).lower() if re.fullmatch(r"w\d{3,}", raw, flags=re.I) else match.group(1).lower()


def normalize_url(value: str) -> str:
    value = value.strip()
    parts = urlsplit(value)
    if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
        raise ValueError(f"Invalid HTTP(S) URL: {value!r}")
    host = parts.hostname.lower() if parts.hostname else ""
    port = parts.port
    netloc = host
    if port and not ((parts.scheme.lower() == "http" and port == 80) or (parts.scheme.lower() == "https" and port == 443)):
        netloc = f"{host}:{port}"
    path = re.sub(r"/{2,}", "/", parts.path or "/")
    if path != "/":
        path = path.rstrip("/")
    query = []
    for key, item_value in parse_qsl(parts.query, keep_blank_values=True):
        key_lower = key.lower()
        if key_lower.startswith("utm_") or key_lower in _TRACKING_QUERY_KEYS:
            continue
        query.append((key, item_value))
    query.sort()
    return urlunsplit((parts.scheme.lower(), netloc, path, urlencode(query), ""))


def normalize_title(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", value)
    return " ".join(value.split())


def normalize_identifier(kind: str, value: str) -> str:
    kind = kind.strip().lower().replace("_", "-")
    if kind == "doi":
        return normalize_doi(value)
    if kind in {"openalex", "openalex-id"}:
        return normalize_openalex(value)
    if kind == "arxiv":
        return normalize_arxiv(value)
    if kind == "nber":
        return normalize_nber(value)
    if kind in {"url", "landing-url"}:
        return normalize_url(value)
    raise ValueError(f"Unsupported identifier type: {kind}")


@dataclass(frozen=True)
class IdentifierSet:
    doi: str | None = None
    openalex: str | None = None
    arxiv: str | None = None
    nber: str | None = None
    url: str | None = None
    title: str | None = None

    @classmethod
    def from_mapping(cls, value: Mapping[str, str | None]) -> "IdentifierSet":
        def maybe(kind: str) -> str | None:
            raw = value.get(kind)
            return normalize_identifier(kind, raw) if raw else None

        url = value.get("url")

        def explicit_or_url(kind: str) -> str | None:
            explicit = maybe(kind)
            if explicit or not url:
                return explicit
            try:
                return normalize_identifier(kind, url)
            except ValueError:
                return None

        return cls(
            doi=explicit_or_url("doi"),
            openalex=explicit_or_url("openalex"),
            arxiv=explicit_or_url("arxiv"),
            nber=explicit_or_url("nber"),
            url=maybe("url"),
            title=value.get("title"),
        )


def canonical_paper_id(value: IdentifierSet | Mapping[str, str | None]) -> str:
    identifiers = value if isinstance(value, IdentifierSet) else IdentifierSet.from_mapping(value)
    for kind in ("doi", "arxiv", "openalex", "nber"):
        item = getattr(identifiers, kind)
        if item:
            return f"{kind}:{item}"
    if identifiers.url:
        digest = hashlib.sha256(identifiers.url.encode("utf-8")).hexdigest()[:20]
        return f"url-sha256:{digest}"
    if identifiers.title:
        title = normalize_title(identifiers.title)
        if title:
            digest = hashlib.sha256(title.encode("utf-8")).hexdigest()[:20]
            return f"title-sha256:{digest}"
    raise ValueError("At least one stable identifier, URL, or title is required")
