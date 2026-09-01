from __future__ import annotations

import html
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from difflib import SequenceMatcher
from html.parser import HTMLParser
from typing import Any, Callable

from .models import PaperRecord


USER_AGENT = "AIResearchWorkbench/0.2 (abstract metadata resolver)"
MIN_ABSTRACT_CHARS = 200
MIN_ABSTRACT_WORDS = 30


@dataclass(frozen=True)
class ResolvedAbstract:
    abstract: str
    source: str
    url: str = ""
    identifier_type: str = ""
    identifier: str = ""


def repair_mojibake(value: str) -> str:
    if "â" not in value and "Ã" not in value:
        return value
    for encoding in ("cp1252", "latin-1"):
        try:
            return value.encode(encoding).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
    return value


def clean_abstract(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html.unescape(repair_mojibake(value or "")))
    return " ".join(text.replace("\u00ad", "").split()).strip()


def complete_abstract(value: str) -> bool:
    text = clean_abstract(value)
    lowered = text.casefold()
    boilerplate = (
        "founded in 1920, the nber is a private",
        "javascript is disabled in your browser",
        "please enable cookies",
        "access denied",
    )
    return (
        len(text) >= MIN_ABSTRACT_CHARS
        and len(re.findall(r"\b\w+\b", text)) >= MIN_ABSTRACT_WORDS
        and not any(phrase in lowered for phrase in boilerplate)
    )


def normalize_title(value: str) -> str:
    value = repair_mojibake(value)
    normalized = " ".join(re.sub(r"[^\w\s]", " ", html.unescape(value).casefold()).split())
    return re.sub(r"^dp\d+\s+", "", normalized).strip()


def title_matches(expected: str, candidate: str) -> bool:
    left = normalize_title(expected)
    right = normalize_title(candidate)
    if not left or not right:
        return False
    if left == right:
        return True
    score = SequenceMatcher(None, left, right).ratio()
    shorter, longer = sorted((left, right), key=len)
    return score >= 0.92 or (len(shorter) >= 35 and shorter in longer and len(shorter) / len(longer) >= 0.88)


def openalex_abstract(index: Any) -> str:
    if not isinstance(index, dict):
        return ""
    positioned: list[tuple[int, str]] = []
    for word, positions in index.items():
        if not isinstance(positions, list):
            continue
        for position in positions:
            if isinstance(position, int):
                positioned.append((position, str(word)))
    return clean_abstract(" ".join(word for _, word in sorted(positioned)))


class ScholarlyMetaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.title_parts: list[str] = []
        self.json_ld: list[str] = []
        self._in_title = False
        self._in_json_ld = False
        self._script: list[str] = []
        self._heading_level = ""
        self._heading: list[str] = []
        self._abstract_section = False
        self.abstract_parts: list[str] = []
        self.h1 = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.casefold(): value or "" for key, value in attrs}
        if tag.casefold() == "meta":
            name = (values.get("name") or values.get("property") or "").casefold()
            if name and values.get("content"):
                self.meta.setdefault(name, values["content"])
        elif tag.casefold() == "title":
            self._in_title = True
        elif tag.casefold() == "script" and "ld+json" in values.get("type", "").casefold():
            self._in_json_ld = True
            self._script = []
        elif tag.casefold() in {"h1", "h2", "h3", "h4"}:
            self._heading_level = tag.casefold()
            self._heading = []

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() == "title":
            self._in_title = False
        elif tag.casefold() == "script" and self._in_json_ld:
            self._in_json_ld = False
            self.json_ld.append("".join(self._script))
        elif tag.casefold() == self._heading_level:
            heading = clean_abstract(" ".join(self._heading)).casefold().rstrip(":")
            if tag.casefold() == "h1" and not self.h1:
                self.h1 = clean_abstract(" ".join(self._heading))
            self._abstract_section = heading == "abstract"
            self._heading_level = ""

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)
        if self._in_json_ld:
            self._script.append(data)
        if self._heading_level:
            self._heading.append(data)
        elif self._abstract_section:
            self.abstract_parts.append(data)


def _json_ld_objects(value: Any):
    if isinstance(value, dict):
        yield value
        graph = value.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                yield from _json_ld_objects(item)
    elif isinstance(value, list):
        for item in value:
            yield from _json_ld_objects(item)


class AbstractResolver:
    """Resolve complete abstracts from public scholarly metadata without using paper titles as evidence."""

    def __init__(self, *, timeout: float = 20.0, fetch_json: Callable[[str], Any] | None = None) -> None:
        self.timeout = timeout
        self._fetch_json_override = fetch_json

    def _request(self, url: str) -> bytes:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json, application/atom+xml;q=0.9"})
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return response.read()

    def _json(self, url: str) -> Any:
        if self._fetch_json_override is not None:
            return self._fetch_json_override(url)
        return json.loads(self._request(url).decode("utf-8", errors="replace"))

    @staticmethod
    def _identifier(paper: PaperRecord, name: str) -> str:
        value = str(paper.identifiers.get(name, "") or "").strip()
        if value:
            if name == "doi":
                value = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", value, flags=re.IGNORECASE)
            if name == "arxiv_id":
                value = re.sub(r"^(?:arxiv:|https?://arxiv\.org/(?:abs|pdf)/)", "", value, flags=re.IGNORECASE)
            return value
        if name == "doi":
            match = re.search(r"(?:doi\.org/|doi:\s*)(10\.\d{4,9}/\S+)", paper.url, re.IGNORECASE)
            return match.group(1).rstrip(".,)") if match else ""
        if name == "arxiv_id":
            match = re.search(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})(?:v\d+)?", paper.url, re.IGNORECASE)
            return match.group(1) if match else ""
        return ""

    def _from_arxiv(self, paper: PaperRecord) -> ResolvedAbstract | None:
        arxiv_id = self._identifier(paper, "arxiv_id")
        if not arxiv_id:
            return None
        query = urllib.parse.urlencode({"id_list": arxiv_id, "max_results": 1})
        root = ET.fromstring(self._request(f"https://export.arxiv.org/api/query?{query}"))
        namespace = {"atom": "http://www.w3.org/2005/Atom"}
        entry = root.find("atom:entry", namespace)
        if entry is None:
            return None
        title = entry.findtext("atom:title", default="", namespaces=namespace)
        abstract = clean_abstract(entry.findtext("atom:summary", default="", namespaces=namespace))
        if not title_matches(paper.title, title) or not complete_abstract(abstract):
            return None
        return ResolvedAbstract(abstract, "arXiv API", f"https://arxiv.org/abs/{arxiv_id}", "arxiv_id", arxiv_id)

    def _openalex_work(self, paper: PaperRecord, work: dict[str, Any]) -> ResolvedAbstract | None:
        title = str(work.get("display_name") or work.get("title") or "")
        if not title_matches(paper.title, title):
            return None
        abstract = openalex_abstract(work.get("abstract_inverted_index"))
        if not complete_abstract(abstract):
            return None
        work_id = str(work.get("id", ""))
        doi = str(work.get("doi", "") or "").removeprefix("https://doi.org/")
        return ResolvedAbstract(abstract, "OpenAlex", work_id, "doi" if doi else "openalex_id", doi or work_id.rsplit("/", 1)[-1])

    def _from_openalex_id(self, paper: PaperRecord) -> ResolvedAbstract | None:
        openalex_id = str(paper.identifiers.get("openalex_id", "") or "").strip()
        if not openalex_id:
            return None
        # Queue records commonly store the canonical URL (for example,
        # ``https://openalex.org/W123``).  The entity endpoint expects only
        # the terminal OpenAlex identifier; percent-encoding the whole URL
        # silently misses an otherwise valid record.
        work_id = openalex_id.rstrip("/").rsplit("/", 1)[-1]
        work = self._json(f"https://api.openalex.org/works/{urllib.parse.quote(work_id, safe='')}")
        return self._openalex_work(paper, work) if isinstance(work, dict) else None

    def _from_openalex_title(self, paper: PaperRecord) -> ResolvedAbstract | None:
        query = urllib.parse.urlencode(
            {
                "search": paper.title,
                "per-page": 5,
                "select": "id,doi,display_name,title,abstract_inverted_index",
            }
        )
        payload = self._json(f"https://api.openalex.org/works?{query}")
        for work in payload.get("results", []) if isinstance(payload, dict) else []:
            if isinstance(work, dict):
                result = self._openalex_work(paper, work)
                if result:
                    return result
        return None

    def _crossref_work(self, paper: PaperRecord, work: dict[str, Any]) -> ResolvedAbstract | None:
        titles = work.get("title") or []
        title = str(titles[0] if isinstance(titles, list) and titles else titles or "")
        if not title_matches(paper.title, title):
            return None
        abstract = clean_abstract(str(work.get("abstract", "") or ""))
        if not complete_abstract(abstract):
            return None
        doi = str(work.get("DOI", "") or "")
        return ResolvedAbstract(abstract, "Crossref", str(work.get("URL", "") or ""), "doi", doi)

    def _from_crossref_doi(self, paper: PaperRecord) -> ResolvedAbstract | None:
        doi = self._identifier(paper, "doi")
        if not doi:
            return None
        payload = self._json(f"https://api.crossref.org/v1/works/{urllib.parse.quote(doi, safe='')}")
        work = payload.get("message", {}) if isinstance(payload, dict) else {}
        return self._crossref_work(paper, work) if isinstance(work, dict) else None

    def _from_crossref_title(self, paper: PaperRecord) -> ResolvedAbstract | None:
        query = urllib.parse.urlencode(
            {"query.title": paper.title, "rows": 5, "select": "DOI,title,abstract,URL"}
        )
        payload = self._json(f"https://api.crossref.org/v1/works?{query}")
        message = payload.get("message", {}) if isinstance(payload, dict) else {}
        for work in message.get("items", []) if isinstance(message, dict) else []:
            if isinstance(work, dict):
                result = self._crossref_work(paper, work)
                if result:
                    return result
        return None

    def _from_datacite_doi(self, paper: PaperRecord) -> ResolvedAbstract | None:
        doi = self._identifier(paper, "doi")
        if not doi:
            return None
        payload = self._json(f"https://api.datacite.org/dois/{urllib.parse.quote(doi, safe='/')}")
        attributes = payload.get("data", {}).get("attributes", {}) if isinstance(payload, dict) else {}
        titles = attributes.get("titles", []) if isinstance(attributes, dict) else []
        title = str(titles[0].get("title", "")) if titles and isinstance(titles[0], dict) else ""
        if not title_matches(paper.title, title):
            return None
        descriptions = attributes.get("descriptions", []) if isinstance(attributes, dict) else []
        ordered = sorted(
            (item for item in descriptions if isinstance(item, dict)),
            key=lambda item: str(item.get("descriptionType", "")).casefold() != "abstract",
        )
        for item in ordered:
            abstract = clean_abstract(str(item.get("description", "") or ""))
            if complete_abstract(abstract):
                return ResolvedAbstract(abstract, "DataCite", f"https://doi.org/{doi}", "doi", doi)
        return None

    def _from_semantic_scholar(self, paper: PaperRecord) -> ResolvedAbstract | None:
        query = urllib.parse.urlencode(
            {"query": paper.title, "limit": 5, "fields": "title,abstract,externalIds,url"}
        )
        payload = self._json(f"https://api.semanticscholar.org/graph/v1/paper/search?{query}")
        for work in payload.get("data", []) if isinstance(payload, dict) else []:
            if not isinstance(work, dict) or not title_matches(paper.title, str(work.get("title", ""))):
                continue
            abstract = clean_abstract(str(work.get("abstract", "") or ""))
            if not complete_abstract(abstract):
                continue
            external = work.get("externalIds") if isinstance(work.get("externalIds"), dict) else {}
            doi = str(external.get("DOI", "") or "")
            return ResolvedAbstract(
                abstract,
                "Semantic Scholar",
                str(work.get("url", "") or ""),
                "doi" if doi else "semantic_scholar_id",
                doi or str(work.get("paperId", "") or ""),
            )
        return None

    def _from_repec(self, paper: PaperRecord) -> ResolvedAbstract | None:
        parsed = urllib.parse.urlparse(paper.url)
        query = urllib.parse.parse_qs(parsed.query)
        raw_handle = (query.get("u") or [""])[0]
        if not raw_handle:
            nber_match = re.search(r"nber\.org/papers/w(\d+)", paper.url, re.IGNORECASE)
            if nber_match:
                raw_handle = f"RePEc:nbr:nberwo:{nber_match.group(1)}"
        if not raw_handle:
            cepr_match = re.search(r"cepr\.org/publications/dp(\d+)", paper.url, re.IGNORECASE)
            if cepr_match:
                raw_handle = f"RePEc:cpr:ceprdp:{cepr_match.group(1)}"
        if not raw_handle:
            world_bank_handles = {
                "099222207302611441": "RePEc:wbk:wbrwps:11433",
                "099071726094510121": "RePEc:wbk:hdnspu:212835",
            }
            raw_handle = next((handle for key, handle in world_bank_handles.items() if key in paper.url), "")
        match = re.fullmatch(r"RePEc:([^:]+):([^:]+):(.+)", raw_handle, re.IGNORECASE)
        if not match:
            return None
        provider, series, identifier = match.groups()
        repec_url = (
            "https://ideas.repec.org/p/"
            f"{urllib.parse.quote(provider.casefold())}/{urllib.parse.quote(series.casefold())}/"
            f"{urllib.parse.quote(identifier)}.html"
        )
        markup = self._request(repec_url).decode("utf-8", errors="replace")
        parser = ScholarlyMetaParser()
        parser.feed(markup)
        page_title = parser.meta.get("citation_title") or parser.h1 or parser.meta.get("og:title") or "".join(parser.title_parts)
        if not title_matches(paper.title, page_title):
            return None
        candidates = [clean_abstract(" ".join(parser.abstract_parts)), parser.meta.get("citation_abstract", "")]
        for value in candidates:
            abstract = clean_abstract(value)
            if complete_abstract(abstract):
                return ResolvedAbstract(abstract, "IDEAS/RePEc", repec_url, "repec_handle", raw_handle)
        return None

    def _from_source_page(self, paper: PaperRecord) -> ResolvedAbstract | None:
        parsed_url = urllib.parse.urlparse(paper.url)
        host = (parsed_url.hostname or "").casefold()
        allowed = (
            "arxiv.org", "nber.org", "iza.org", "cepr.org", "aeaweb.org", "worldbank.org",
            "repec.org", "bfi.uchicago.edu", "papers.ssrn.com", "academic.oup.com", "doi.org",
            "journals.uchicago.edu", "zenodo.org", "mendeley.com", "meta-analysis.cz",
        )
        if not host or not any(host == domain or host.endswith("." + domain) for domain in allowed):
            return None
        doi = self._identifier(paper, "doi")
        source_overrides = {"10.1086/743543": "https://meta-analysis.cz/incentives/paper/"}
        url = source_overrides.get(doi.casefold(), urllib.parse.urlunparse(parsed_url._replace(fragment="")))
        if url != paper.url:
            host = (urllib.parse.urlparse(url).hostname or "").casefold()
        markup = self._request(url).decode("utf-8", errors="replace")
        parser = ScholarlyMetaParser()
        parser.feed(markup)
        page_title = parser.meta.get("citation_title") or parser.meta.get("og:title") or "".join(parser.title_parts)
        candidates = [
            parser.meta.get("citation_abstract", ""),
            parser.meta.get("dc.description", ""),
            parser.meta.get("dcterms.description", ""),
            clean_abstract(" ".join(parser.abstract_parts)),
        ]
        if not (host == "nber.org" or host.endswith(".nber.org")):
            candidates.extend([parser.meta.get("description", ""), parser.meta.get("og:description", "")])
        for block in parser.json_ld:
            try:
                payload = json.loads(block)
            except json.JSONDecodeError:
                continue
            for item in _json_ld_objects(payload):
                item_title = str(item.get("headline") or item.get("name") or "")
                if item_title and title_matches(paper.title, item_title):
                    candidates.extend([str(item.get("abstract", "") or ""), str(item.get("description", "") or "")])
        if not title_matches(paper.title, page_title):
            return None
        for value in candidates:
            abstract = clean_abstract(value)
            if complete_abstract(abstract):
                return ResolvedAbstract(abstract, "Official source page", url)
        return None

    def resolve(self, paper: PaperRecord) -> ResolvedAbstract | None:
        if complete_abstract(paper.abstract):
            return ResolvedAbstract(clean_abstract(paper.abstract), "existing")
        resolvers = (
            self._from_arxiv,
            self._from_crossref_doi,
            self._from_openalex_id,
            self._from_openalex_title,
            self._from_crossref_title,
            self._from_datacite_doi,
            self._from_repec,
            self._from_semantic_scholar,
            self._from_source_page,
        )
        for resolver in resolvers:
            try:
                result = resolver(paper)
            except (OSError, TimeoutError, ValueError, ET.ParseError, json.JSONDecodeError):
                continue
            if result and complete_abstract(result.abstract):
                return result
        return None
