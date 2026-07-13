"""
Econ JMP Paper Tracker (Causal Inference & Rigorous Methods)
FINAL ENGLISH VERSION:
1) Source: OpenAlex restricted strictly to ECONOMICS concept.
2) Filter: "The Identification Police" (Rejects non-causal papers).
3) Output: Strict English Summaries (Focus on Identification & Effect Sizes).

Install:
  pip install arxiv requests google-genai feedparser
"""

from __future__ import annotations

import os
import sys
import json
import time
import datetime as dt
from dataclasses import dataclass
from typing import List

import requests
import arxiv
import feedparser
from google.genai import Client

from tracker_core import (
    LANES,
    RecommendationProfile,
    SourceConfigurationError,
    SourceFetchError,
    SourceHealthReport,
    crossref_contact_params,
    default_lane,
    enforce_tier_1_contract,
    fetch_feed_with_retry,
    load_recommendation_profile,
    normalize_title,
    parse_lane_weights,
    request_with_retry,
    safe_error_summary,
    stable_paper_id,
    stratified_evaluation_sample,
    update_queue_state,
)

# =========================================================
# 1) Config
# =========================================================

@dataclass
class Config:
    google_api_key: str
    gemini_model: str = "gemini-2.5-flash"

    # Search Window
    days_back: int = 7

    # Limits
    max_candidates_per_source: int = 250
    final_max_papers: int = 15
    weekly_max_new: int = 15
    evaluation_max: int = 180
    source_failure_threshold: int = 2
    lane_mix: str = "exploit:0.55,adjacent:0.20,contradiction:0.15,methodology:0.10"
    queue_state_path: str = "queue_state.jsonl"
    queue_markdown_path: str = "reading_queue.md"
    source_health_path: str = "source_health.json"

    # OpenAlex Concept IDs
    # STRICTLY Economics (C162324750) and Econometrics (C149178828)
    openalex_concepts: str = "C162324750|C149178828"

def load_config() -> Config:
    # Read API key from environment variable (required for GitHub Actions)
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is not set. Please configure it in GitHub Secrets.")
    return Config(
        google_api_key=api_key,
        gemini_model=os.environ.get("PAPER_TRACKER_MODEL", "gemini-2.5-flash"),
        days_back=int(os.environ.get("PAPER_TRACKER_DAYS_BACK", "7")),
        max_candidates_per_source=int(os.environ.get("PAPER_TRACKER_SOURCE_LIMIT", "250")),
        weekly_max_new=int(os.environ.get("PAPER_TRACKER_WEEKLY_MAX", "15")),
        evaluation_max=max(
            1, int(os.environ.get("PAPER_TRACKER_EVALUATION_MAX", "180"))
        ),
        source_failure_threshold=max(
            1, int(os.environ.get("PAPER_TRACKER_SOURCE_FAILURE_THRESHOLD", "2"))
        ),
        lane_mix=os.environ.get(
            "PAPER_TRACKER_LANE_MIX",
            "exploit:0.55,adjacent:0.20,contradiction:0.15,methodology:0.10",
        ),
        queue_state_path=os.environ.get("PAPER_TRACKER_QUEUE_STATE", "queue_state.jsonl"),
        queue_markdown_path=os.environ.get("PAPER_TRACKER_QUEUE_MARKDOWN", "reading_queue.md"),
        source_health_path=os.environ.get("PAPER_TRACKER_SOURCE_HEALTH", "source_health.json"),
    )

def log(msg: str):
    line = f"[{dt.datetime.now().strftime('%H:%M:%S')}] {msg}\n"
    sys.stdout.buffer.write(line.encode('utf-8', errors='replace'))
    sys.stdout.buffer.flush()

def load_researcher_profile() -> str:
    """Load researcher_profile.md from the same directory as this script."""
    profile_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "researcher_profile.md")
    try:
        with open(profile_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        log("WARNING: researcher_profile.md not found. Using empty profile.")
        return ""


def load_compact_recommendation_profile() -> RecommendationProfile:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return load_recommendation_profile(
        os.path.join(base_dir, "researcher_profile.md"),
        os.path.join(base_dir, "recommendation_profile.json"),
    )

# =========================================================
# 2) Data Structures
# =========================================================

@dataclass
class Paper:
    source: str
    title: str
    abstract: str
    url: str
    published: str
    venue: str = "Unknown"
    authors: str = ""
    relevance_reason: str = ""
    tier: int = 2
    doi: str = ""
    arxiv_id: str = ""
    openalex_id: str = ""
    paper_id: str = ""
    methodology: str = ""
    matched_signal: str = ""
    lane: str = "adjacent"
    recommendation_score: float = 0.0

def dedupe_papers(papers: List[Paper]) -> List[Paper]:
    seen_ids = set()
    seen_titles = set()
    unique = []
    for p in papers:
        p.paper_id = p.paper_id or stable_paper_id(
            title=p.title,
            url=p.url,
            doi=p.doi,
            arxiv_id=p.arxiv_id,
            openalex_id=p.openalex_id,
        )
        t_norm = normalize_title(p.title)
        if p.paper_id in seen_ids or (t_norm and t_norm in seen_titles):
            continue
        seen_ids.add(p.paper_id)
        if t_norm:
            seen_titles.add(t_norm)
        unique.append(p)
    return unique

# =========================================================
# 3) Sources (Strict Econ Focus)
# =========================================================

def fetch_openalex_econ(
    cfg: Config, profile: RecommendationProfile | None = None
) -> List[Paper]:
    log(f"Fetching OpenAlex (Strict Economics Concepts)...")
    base_url = "https://api.openalex.org/works"
    start_date = (dt.date.today() - dt.timedelta(days=cfg.days_back)).strftime("%Y-%m-%d")

    # OpenAlex search is issued as small, valid single-term queries.  This also
    # allows researcher-profile retrieval terms to expand recall instead of
    # affecting only the downstream LLM ranking.
    base_terms = ["artificial intelligence", "generative AI", "large language model", "ChatGPT"]
    retrieval_terms = profile.retrieval_terms[:8] if profile else []
    search_terms = list(dict.fromkeys([*base_terms, *retrieval_terms]))
    concept_ids = [value.strip() for value in cfg.openalex_concepts.split("|") if value.strip()]
    per_query = max(10, min(50, cfg.max_candidates_per_source // max(1, len(search_terms))))
    results: List[Paper] = []

    for concept_id in concept_ids:
        for search_term in search_terms:
            params = {
                "filter": f"concepts.id:{concept_id},from_publication_date:{start_date}",
                "search": search_term,
                "sort": "publication_date:desc",
                "per-page": per_query,
            }
            response = request_with_retry(
                "openalex",
                base_url,
                request_func=requests.get,
                params=params,
                timeout=20,
                headers={"User-Agent": "ai-economics-paper-tracker/3.0"},
            )
            data = response.json()
            for item in data.get('results', []):
            # Abstract
                abstract = ""
                if item.get('abstract_inverted_index'):
                    index = item['abstract_inverted_index']
                    words = {}
                    for w, positions in index.items():
                        for p in positions:
                            words[p] = w
                    abstract = " ".join(words[i] for i in sorted(words.keys()) if i < 600)
                else:
                    abstract = item.get('title', "")

            # Location/Venue
                primary_loc = item.get('primary_location') or {}
                source_info = primary_loc.get('source') or {}
                venue = source_info.get('display_name') or "OpenAlex (Working Paper)"

            # Authors
                authors_list = item.get('authorships', [])
                authors_str = ", ".join([a.get('author', {}).get('display_name', '') for a in authors_list[:3]])
                ids = item.get('ids', {}) or {}
                results.append(Paper(
                    source="OpenAlex (Econ)",
                    title=item.get('title', 'No Title'),
                    abstract=abstract,
                    url=ids.get('doi') or ids.get('openalex', ''),
                    published=item.get('publication_date', ''),
                    venue=venue,
                    authors=authors_str,
                    doi=ids.get('doi', ''),
                    openalex_id=item.get('id', '') or ids.get('openalex', ''),
                ))

    unique = dedupe_papers(results)[: cfg.max_candidates_per_source]
    log(f"Found {len(unique)} Econ candidates from OpenAlex.")
    return unique

def fetch_arxiv_econ(
    cfg: Config, profile: RecommendationProfile | None = None
) -> List[Paper]:
    """
    ArXiv pre-filtered for Causal Inference terms to reduce noise.
    """
    log("Fetching ArXiv (Econ/Quant-Fin focus)...")

    profile_terms = profile.retrieval_terms[:8] if profile else []
    escaped_terms = [term.replace('"', '') for term in profile_terms]
    profile_clause = " OR ".join(f'all:"{term}"' for term in escaped_terms)
    topic_clause = '(all:"causal inference" OR all:"difference-in-differences" OR all:"randomized" OR all:"instrumental variable" OR all:"regression discontinuity" OR all:econometrics OR all:"labor market" OR all:education OR all:employment OR all:automation OR all:wages OR all:productivity)'
    if profile_clause:
        topic_clause = f"({topic_clause} OR {profile_clause})"
    query = f'(all:"large language model" OR all:"generative AI" OR all:"ChatGPT" OR all:"GPT-4" OR all:"artificial intelligence") AND {topic_clause}'

    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=cfg.max_candidates_per_source,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )

    results = []
    try:
        for r in client.results(search):
            pub_date = r.published.strftime("%Y-%m-%d")
            pub_dt = r.published.date()
            cutoff = dt.date.today() - dt.timedelta(days=cfg.days_back)

            if pub_dt >= cutoff:
                authors = ", ".join(a.name for a in r.authors[:3])
                results.append(Paper(
                    source="arXiv (Quant)",
                    title=r.title,
                    abstract=r.summary,
                    url=(f"https://doi.org/{r.doi}" if getattr(r, "doi", None) else r.entry_id),
                    published=pub_date,
                    venue="arXiv",
                    authors=authors,
                    doi=getattr(r, "doi", "") or "",
                    arxiv_id=r.get_short_id(),
                ))
    except Exception as e:
        raise SourceFetchError("arxiv", f"Error fetching arXiv: {e}") from e

    log(f"Found {len(results)} Quant/Econ candidates from ArXiv.")
    return results

def fetch_nber_papers(cfg: Config) -> List[Paper]:
    """
    Fetch NBER working papers from RSS feeds and RePEc NEP feeds.
    Filters for AI + (education OR labor) topics.
    """
    log("Fetching NBER papers from RSS feeds...")
    results = []

    # Keywords for filtering — AI must be specific enough to be the subject, not just a tool
    ai_keywords = ['artificial intelligence', 'large language model', 'generative ai', 'chatgpt',
                   'gpt-4', 'llm', 'automation', 'machine learning', 'ai-', ' ai ']
    topic_keywords = ['education', 'learning', 'schooling', 'student', 'teacher', 'labor', 'labour',
                      'employment', 'wage', 'job', 'occupation', 'skill', 'workforce',
                      'human capital', 'productivity', 'worker']

    cutoff_date = dt.date.today() - dt.timedelta(days=cfg.days_back)

    # Feed URLs to check
    feeds = [
        ('https://back.nber.org/rss/new.xml', 'NBER Direct'),
        ('https://nep.repec.org/rss/nep-ain.rss.xml', 'NEP-AIN'),
        ('https://nep.repec.org/rss/nep-lab.rss.xml', 'NEP-LAB'),
        ('https://nep.repec.org/rss/nep-edu.rss.xml', 'NEP-EDU'),
        ('https://nep.repec.org/rss/nep-lma.rss.xml', 'NEP-LMA'),
    ]
    feed_failures = []

    for feed_url, feed_name in feeds:
        try:
            feed = fetch_feed_with_retry(
                f"nber/{feed_name}",
                feed_url,
                request_func=requests.get,
                feed_parser=feedparser.parse,
            )

            for entry in feed.entries:
                # Check if it's an NBER paper
                link = entry.get('link', '')
                if 'nber.org' not in link.lower():
                    continue

                # Get paper metadata
                title = entry.get('title', '')
                description = entry.get('description', '') or entry.get('summary', '')

                # Combine title and abstract for keyword search
                text = f"{title} {description}".lower()

                # Check for AI keywords AND topic keywords
                has_ai = any(kw in text for kw in ai_keywords)
                has_topic = any(kw in text for kw in topic_keywords)

                if not (has_ai and has_topic):
                    continue

                # Parse date (different formats in different feeds)
                pub_date = None
                date_str = entry.get('dc_date') or entry.get('published') or entry.get('updated')

                if date_str:
                    try:
                        # Try parsing various date formats
                        if 'T' in date_str:
                            pub_date = dt.datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
                        else:
                            pub_date = dt.datetime.strptime(date_str[:10], '%Y-%m-%d').date()
                    except:
                        pass

                # If we have a date, check if it's recent enough
                if pub_date and pub_date < cutoff_date:
                    continue

                # Parse authors
                authors = ""
                if hasattr(entry, 'dc_creator'):
                    if isinstance(entry.dc_creator, list):
                        authors = ", ".join(entry.dc_creator[:3])
                    else:
                        authors = entry.dc_creator
                elif hasattr(entry, 'author'):
                    authors = entry.author
                # If no explicit author field, try to extract from title (NBER format: "Title by Author1, Author2")
                elif ' by ' in title:
                    parts = title.split(' by ')
                    if len(parts) > 1:
                        authors = parts[-1]
                        title = parts[0]

                results.append(Paper(
                    source="NBER",
                    title=title,
                    abstract=description,
                    url=link,
                    published=date_str[:10] if date_str and len(date_str) >= 10 else str(dt.date.today()),
                    venue="NBER Working Paper",
                    authors=authors
                ))

        except SourceConfigurationError:
            raise
        except Exception as e:
            log(f"Error fetching {feed_name}: {e}")
            feed_failures.append(f"{feed_name}: {e}")
            continue

    if len(feed_failures) == len(feeds):
        raise SourceFetchError("nber", "All NBER/RePEc feeds failed: " + "; ".join(feed_failures))

    # Deduplicate by URL
    seen_urls = set()
    unique_results = []
    for p in results:
        if p.url not in seen_urls:
            seen_urls.add(p.url)
            unique_results.append(p)

    log(f"Found {len(unique_results)} NBER candidates from RSS feeds.")
    return unique_results

def fetch_iza_papers(cfg: Config) -> List[Paper]:
    """
    Fetch IZA discussion papers from RePEc NEP feeds.
    Filters for AI + (education OR labor) topics.
    """
    log("Fetching IZA papers from RePEc NEP feeds...")
    results = []

    # Keywords for filtering — AI must be specific enough to be the subject, not just a tool
    ai_keywords = ['artificial intelligence', 'large language model', 'generative ai', 'chatgpt',
                   'gpt-4', 'llm', 'automation', 'machine learning', 'ai-', ' ai ']
    topic_keywords = ['education', 'learning', 'schooling', 'student', 'teacher', 'labor', 'labour',
                      'employment', 'wage', 'job', 'occupation', 'skill', 'workforce',
                      'human capital', 'productivity', 'worker']

    cutoff_date = dt.date.today() - dt.timedelta(days=cfg.days_back)

    # NEP feeds that include IZA papers
    feeds = [
        ('https://nep.repec.org/rss/nep-ain.rss.xml', 'NEP-AIN'),
        ('https://nep.repec.org/rss/nep-lab.rss.xml', 'NEP-LAB'),
        ('https://nep.repec.org/rss/nep-edu.rss.xml', 'NEP-EDU'),
        ('https://nep.repec.org/rss/nep-lma.rss.xml', 'NEP-LMA'),
    ]
    feed_failures = []

    for feed_url, feed_name in feeds:
        try:
            feed = fetch_feed_with_retry(
                f"iza/{feed_name}",
                feed_url,
                request_func=requests.get,
                feed_parser=feedparser.parse,
            )

            for entry in feed.entries:
                # Check if it's an IZA paper
                link = entry.get('link', '')
                description = entry.get('description', '') or entry.get('summary', '')

                # IZA papers appear in RePEc with 'iza' in the link or description
                is_iza = 'iza' in link.lower() or 'iza' in description.lower()

                if not is_iza:
                    continue

                # Get paper metadata
                title = entry.get('title', '')

                # Combine title and abstract for keyword search
                text = f"{title} {description}".lower()

                # Check for AI keywords AND topic keywords
                has_ai = any(kw in text for kw in ai_keywords)
                has_topic = any(kw in text for kw in topic_keywords)

                if not (has_ai and has_topic):
                    continue

                # Parse date
                pub_date = None
                date_str = entry.get('dc_date') or entry.get('published') or entry.get('updated')

                if date_str:
                    try:
                        # Try parsing various date formats
                        if 'T' in date_str:
                            pub_date = dt.datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
                        else:
                            pub_date = dt.datetime.strptime(date_str[:10], '%Y-%m-%d').date()
                    except:
                        pass

                # If we have a date, check if it's recent enough
                if pub_date and pub_date < cutoff_date:
                    continue

                # Parse authors
                authors = ""
                if hasattr(entry, 'dc_creator'):
                    if isinstance(entry.dc_creator, list):
                        authors = ", ".join(entry.dc_creator[:3])
                    else:
                        authors = entry.dc_creator
                elif hasattr(entry, 'author'):
                    authors = entry.author

                results.append(Paper(
                    source="IZA",
                    title=title,
                    abstract=description,
                    url=link,
                    published=date_str[:10] if date_str and len(date_str) >= 10 else str(dt.date.today()),
                    venue="IZA Discussion Paper",
                    authors=authors
                ))

        except SourceConfigurationError:
            raise
        except Exception as e:
            log(f"Error fetching {feed_name} for IZA: {e}")
            feed_failures.append(f"{feed_name}: {e}")
            continue

    if len(feed_failures) == len(feeds):
        raise SourceFetchError("iza", "All IZA/RePEc feeds failed: " + "; ".join(feed_failures))

    # Deduplicate by URL
    seen_urls = set()
    unique_results = []
    for p in results:
        if p.url not in seen_urls:
            seen_urls.add(p.url)
            unique_results.append(p)

    log(f"Found {len(unique_results)} IZA candidates from RePEc feeds.")
    return unique_results

def fetch_aea_papers(cfg: Config) -> List[Paper]:
    """
    Fetch recent AEA journal papers via CrossRef API (no API key required).
    Covers: AER, AEJ Applied, AEJ Macro, AEJ Policy, AEJ Micro, JEL, JEP, AER Insights.
    Abstracts come from CrossRef (88%+ coverage for AEA journals).
    Falls back to RSS feeds for any papers missing abstracts.
    """
    log("Fetching AEA papers from CrossRef API...")
    results = []

    import re

    ai_keywords = ['artificial intelligence', 'large language model', 'generative ai', 'chatgpt',
                   'gpt-4', 'llm', 'automation', 'machine learning', 'ai-', ' ai ']
    topic_keywords = ['education', 'learning', 'schooling', 'student', 'teacher', 'labor', 'labour',
                      'employment', 'wage', 'job', 'occupation', 'skill', 'workforce',
                      'human capital', 'productivity', 'worker']

    cutoff_date = dt.date.today() - dt.timedelta(days=cfg.days_back)
    from_date = cutoff_date.strftime("%Y-%m-%d")

    def strip_jats(text: str) -> str:
        """Remove JATS XML tags from CrossRef abstracts."""
        return re.sub(r'<[^>]+>', '', text).strip()

    # Step 1: CrossRef API — AEA member ID is 11, DOI prefix 10.1257
    crossref_url = "https://api.crossref.org/works"
    params = {
        "filter": f"member:11,type:journal-article,from-pub-date:{from_date}",
        "rows": cfg.max_candidates_per_source,
        "select": "title,abstract,author,URL,published,DOI,container-title",
        "sort": "published",
        "order": "desc",
        **crossref_contact_params(),
    }

    seen_dois = set()
    crossref_error = None
    try:
        r = request_with_retry(
            "aea/crossref",
            crossref_url,
            request_func=requests.get,
            params=params,
            timeout=30,
            headers={"User-Agent": "ai-economics-paper-tracker/3.0"},
        )
        data = r.json()
        items = data.get("message", {}).get("items", [])

        for item in items:
            title_list = item.get("title", [])
            title = title_list[0] if title_list else ""
            if not title:
                continue

            doi = item.get("DOI", "")
            url = item.get("URL", f"https://doi.org/{doi}" if doi else "")
            seen_dois.add(doi)

            # Abstract (strip JATS XML tags)
            raw_abstract = item.get("abstract", "")
            abstract = strip_jats(raw_abstract) if raw_abstract else ""

            # Authors (up to 3)
            author_list = item.get("author", [])
            authors_str = ", ".join(
                f"{a.get('given', '')} {a.get('family', '')}".strip()
                for a in author_list[:3]
            )

            # Publication date
            pub_parts = item.get("published", {}).get("date-parts", [[]])
            if pub_parts and pub_parts[0]:
                parts = pub_parts[0]
                pub_str = "-".join(str(x).zfill(2) for x in parts)
                try:
                    pub_date = dt.date(parts[0], parts[1] if len(parts) > 1 else 1, parts[2] if len(parts) > 2 else 1)
                except Exception:
                    pub_date = None
            else:
                pub_str = str(dt.date.today())
                pub_date = None

            if pub_date and pub_date < cutoff_date:
                continue

            # Venue
            container = item.get("container-title", [])
            venue = container[0] if container else "AEA Journal"

            # Keyword pre-filter (use title + abstract)
            text = f"{title} {abstract}".lower()
            has_ai = any(kw in text for kw in ai_keywords)
            has_topic = any(kw in text for kw in topic_keywords)
            if not (has_ai and has_topic):
                continue

            results.append(Paper(
                source="AEA",
                title=title,
                abstract=abstract,
                url=url,
                published=pub_str,
                venue=venue,
                authors=authors_str,
                doi=doi,
            ))

    except SourceConfigurationError:
        raise
    except Exception as e:
        log(f"Error fetching AEA via CrossRef: {safe_error_summary(e)}")
        crossref_error = e

    # Step 2: RSS feeds — catch any papers CrossRef might have missed (TOC-only, no abstract)
    # Use DOI from RSS to avoid duplicates; only add if not already fetched via CrossRef
    aea_rss_feeds = [
        ("https://pubs.aeaweb.org/action/showFeed?jc=aer&type=etoc&feed=rss", "American Economic Review"),
        ("https://pubs.aeaweb.org/action/showFeed?jc=app&type=etoc&feed=rss", "AEJ: Applied Economics"),
        ("https://pubs.aeaweb.org/action/showFeed?jc=mac&type=etoc&feed=rss", "AEJ: Macroeconomics"),
        ("https://pubs.aeaweb.org/action/showFeed?jc=pol&type=etoc&feed=rss", "AEJ: Economic Policy"),
        ("https://pubs.aeaweb.org/action/showFeed?jc=mic&type=etoc&feed=rss", "AEJ: Microeconomics"),
        ("https://pubs.aeaweb.org/action/showFeed?jc=jel&type=etoc&feed=rss", "Journal of Economic Literature"),
        ("https://pubs.aeaweb.org/action/showFeed?jc=jep&type=etoc&feed=rss", "Journal of Economic Perspectives"),
    ]

    rss_failures = []
    for feed_url, journal_name in aea_rss_feeds:
        try:
            feed = fetch_feed_with_retry(
                f"aea/{journal_name}",
                feed_url,
                request_func=requests.get,
                feed_parser=feedparser.parse,
            )
            for entry in feed.entries:
                title = entry.get("title", "")
                link = entry.get("link", "")
                doi = ""
                if hasattr(entry, "prism_doi"):
                    doi = entry.prism_doi
                elif "10.1257" in link:
                    doi = link.split("10.1257")[-1]
                    doi = "10.1257" + doi

                # Skip if already fetched via CrossRef
                if doi and doi in seen_dois:
                    continue

                # AEA RSS feeds don't include abstracts; use title for keyword check
                text = title.lower()
                has_ai = any(kw in text for kw in ai_keywords)
                has_topic = any(kw in text for kw in topic_keywords)
                if not (has_ai and has_topic):
                    continue

                # Try to get abstract via CrossRef DOI lookup
                abstract = ""
                authors_str = ""
                if doi:
                    try:
                        doi_resp = request_with_retry(
                            "aea/crossref-doi",
                            f"https://api.crossref.org/works/{doi}",
                            request_func=requests.get,
                            params=crossref_contact_params(),
                            timeout=10
                        )
                        if doi_resp.status_code == 200:
                            doi_data = doi_resp.json().get("message", {})
                            raw_abstract = doi_data.get("abstract", "")
                            abstract = strip_jats(raw_abstract) if raw_abstract else ""
                            author_list = doi_data.get("author", [])
                            authors_str = ", ".join(
                                f"{a.get('given', '')} {a.get('family', '')}".strip()
                                for a in author_list[:3]
                            )
                        time.sleep(0.4)  # polite pool rate limit
                    except Exception:
                        pass

                if not abstract:
                    abstract = title  # fallback so LLM filter can still see something

                seen_dois.add(doi)
                results.append(Paper(
                    source="AEA",
                    title=title,
                    abstract=abstract,
                    url=link,
                    published=str(dt.date.today()),
                    venue=journal_name,
                    authors=authors_str if doi else "",
                    doi=doi,
                ))
        except SourceConfigurationError:
            raise
        except Exception as e:
            log(f"Error fetching AEA RSS ({journal_name}): {e}")
            rss_failures.append(f"{journal_name}: {e}")
            continue

    if crossref_error and len(rss_failures) == len(aea_rss_feeds):
        raise SourceFetchError(
            "aea",
            f"CrossRef and all AEA RSS feeds failed: {crossref_error}; " + "; ".join(rss_failures),
        )

    log(f"Found {len(results)} AEA candidates from CrossRef + RSS.")
    return results

def fetch_cepr_papers(cfg: Config) -> List[Paper]:
    """
    Fetch CEPR Discussion Papers via RSS feed.
    Full abstracts (~280 words), free, no API key required.
    ~50 papers per feed, published continuously.
    """
    log("Fetching CEPR Discussion Papers from RSS...")
    results = []

    ai_keywords = ['artificial intelligence', 'large language model', 'generative ai', 'chatgpt',
                   'gpt-4', 'llm', 'automation', 'machine learning', 'ai-', ' ai ']
    topic_keywords = ['education', 'learning', 'schooling', 'student', 'teacher', 'labor', 'labour',
                      'employment', 'wage', 'job', 'occupation', 'skill', 'workforce',
                      'human capital', 'productivity', 'worker']
    cutoff_date = dt.date.today() - dt.timedelta(days=cfg.days_back)

    try:
        feed = fetch_feed_with_retry(
            "cepr",
            "https://cepr.org/rss/discussion-paper",
            request_func=requests.get,
            feed_parser=feedparser.parse,
        )
        for entry in feed.entries:
            title = entry.get("title", "")
            abstract = entry.get("description", "") or entry.get("summary", "")
            link = entry.get("link", "")

            pub_date = None
            if entry.get("published_parsed"):
                pub_date = dt.date(*entry.published_parsed[:3])
            if pub_date and pub_date < cutoff_date:
                continue

            text = f"{title} {abstract}".lower()
            if not (any(kw in text for kw in ai_keywords) and
                    any(kw in text for kw in topic_keywords)):
                continue

            authors = entry.get("author", "")
            results.append(Paper(
                source="CEPR",
                title=title,
                abstract=abstract,
                url=link,
                published=str(pub_date) if pub_date else str(dt.date.today()),
                venue="CEPR Discussion Paper",
                authors=authors,
            ))
    except SourceConfigurationError:
        raise
    except Exception as e:
        raise SourceFetchError("cepr", f"Error fetching CEPR RSS: {e}") from e

    log(f"Found {len(results)} CEPR candidates from RSS.")
    return results

def fetch_worldbank_papers(cfg: Config) -> List[Paper]:
    """
    Fetch World Bank working papers via Documents & Reports REST API.
    Free, no API key, full abstracts, date-filtered via strdate param.
    """
    log("Fetching World Bank papers via API...")
    results = []

    ai_keywords = ['artificial intelligence', 'large language model', 'generative ai', 'chatgpt',
                   'gpt-4', 'llm', 'automation', 'machine learning', 'ai-', ' ai ']
    topic_keywords = ['education', 'learning', 'schooling', 'student', 'teacher', 'labor', 'labour',
                      'employment', 'wage', 'job', 'occupation', 'skill', 'workforce',
                      'human capital', 'productivity', 'worker']
    cutoff_date = dt.date.today() - dt.timedelta(days=cfg.days_back)
    from_date = cutoff_date.strftime("%Y-%m-%d")

    params = {
        "qterm": 'artificial intelligence OR machine learning OR automation OR "large language model"',
        "strdate": from_date,
        "format": "json",
        "fl": "display_title,abstracts,docdt,authr,url",
        "rows": cfg.max_candidates_per_source,
        "os": 0,
    }

    try:
        r = request_with_retry(
            "worldbank",
            "https://search.worldbank.org/api/v3/wds",
            request_func=requests.get,
            params=params,
            timeout=30,
            headers={"User-Agent": "ai-economics-paper-tracker/3.0"},
        )
        documents = r.json().get("documents", {})

        for doc_id, doc in documents.items():
            if not isinstance(doc, dict):
                continue
            title = doc.get("docna", doc.get("display_title", ""))
            if not title:
                continue

            # Abstract nested under abstracts -> cdata!
            abstracts_field = doc.get("abstracts", {})
            abstract = abstracts_field.get("cdata!", "") if isinstance(abstracts_field, dict) else str(abstracts_field or "")

            # Date filter
            doc_date_str = doc.get("docdt", "")
            pub_date = None
            if doc_date_str:
                try:
                    pub_date = dt.datetime.strptime(doc_date_str[:10], "%Y-%m-%d").date()
                except Exception:
                    pass
            if pub_date and pub_date < cutoff_date:
                continue

            # Authors
            authors_field = doc.get("authr", "")
            if isinstance(authors_field, list):
                authors = ", ".join(a.get("value", "") for a in authors_field[:3])
            else:
                authors = str(authors_field) if authors_field else ""

            url = doc.get("url", f"https://documents.worldbank.org/en/publication/documents-reports/documentdetail/{doc_id}")

            text = f"{title} {abstract}".lower()
            if not (any(kw in text for kw in ai_keywords) and
                    any(kw in text for kw in topic_keywords)):
                continue

            results.append(Paper(
                source="World Bank",
                title=title,
                abstract=abstract,
                url=url,
                published=str(pub_date) if pub_date else doc_date_str[:10],
                venue="World Bank Working Paper",
                authors=authors,
            ))
    except SourceConfigurationError:
        raise
    except Exception as e:
        raise SourceFetchError("worldbank", f"Error fetching World Bank papers: {e}") from e

    log(f"Found {len(results)} World Bank candidates.")
    return results

# =========================================================
# 4) The Filter (The "JMP Referee")
# =========================================================

def llm_econ_rigor_check(
    client: Client,
    cfg: Config,
    papers: List[Paper],
    profile: RecommendationProfile | str | None = None,
) -> List[Paper]:
    log(f"--- Starting Econ Rigor Check (JMP Filter) on {len(papers)} papers ---")
    relevant_papers = []

    if isinstance(profile, RecommendationProfile):
        profile_section = profile.compact_prompt()
    elif profile:
        profile_section = str(profile)[:5000]
    else:
        profile_section = json.dumps({
            "retrieval_terms": ["artificial intelligence", "generative AI", "large language models", "automation"],
            "active_signals": [],
            "current_interests": [],
            "reading_preferences": [],
        })

    evaluation_errors = 0

    for i, p in enumerate(papers):
        if not p.abstract or len(p.abstract) < 50:
            continue

        prompt = f"""
You are a research assistant for a PhD student in Economics. Your job is to decide whether a paper belongs in their weekly reading list, and if so, how high a priority it is.

=== RESEARCHER PROFILE ===
{profile_section}

=== SELECTION RULES ===

ACCEPT the paper if it satisfies TRACK A or TRACK B below.

--- TRACK A: Causal Empirical Paper ---
Must satisfy ALL THREE:

1. AI IS THE MAIN SUBJECT: The paper must primarily study the economic consequences of AI/LLMs/automation/generative AI. AI must appear in the research question itself — "How does AI affect X?" — not merely as a tool the authors use.

2. ECONOMIC OUTCOME IS CENTRAL: The paper's outcome variable must be one of: student learning/achievement, teacher productivity, educational attainment, wages, employment levels, occupational structure, task displacement, labor productivity, firm-level output or innovation from AI adoption. Papers on supply chains, logistics, tourism, healthcare, climate, finance markets, or other sectors are only acceptable if they measure direct effects on workers' wages or employment.

3. METHODOLOGY IS RIGOROUS: Must use at least one of: RCT, DiD, IV, RDD, event study, or structural economic model with calibrated parameters. Pure descriptive, conceptual, or narrative papers are REJECTED under this track.

--- TRACK B: Methodology Paper ---
Accept if BOTH hold:

1. The paper introduces, substantially improves, or critically evaluates a research methodology that is directly useful for empirical economics research — e.g., new ways to use AI agents to construct datasets, new causal inference estimators, new measurement approaches for economic variables.

2. The methodology is plausibly applicable to labor, education, or AI-economics research. Pure CS benchmarks or model architecture papers do not qualify.

HARD REJECT — always reject papers in these categories even if they mention AI:
- Tourism, hospitality, or travel industry papers
- Supply chain, logistics, or operations management papers
- Pure finance: asset pricing, banking risk, investment, cryptocurrency
- Climate change, energy, agriculture, or environmental papers
- Healthcare, medicine, or neuroscience papers
- Pure CS/engineering: system benchmarks, model architecture, accuracy evaluations
- Entrepreneurship strategy or business management without labor/wage data
- Governance, ethics, regulation, or policy opinion pieces without empirical outcomes
- Papers studying AI behavior or LLM capabilities with no human economic outcome

=== PRIVATE RECOMMENDATION SIGNALS ===

The researcher profile may contain three internal signal types:
- ACTIVE RESEARCH DIRECTIONS: formal, human-approved idea-pipeline entries.
- CURRENT INTEREST SIGNALS: rough research questions that are not yet formal ideas; ranking-only.
- READING PREFERENCE SIGNALS: recent high-value, useful, low-fit, full-read, selective-read, or rough-read feedback; ranking-only.

Only an exact ID listed in `tier_1_signal_ids` may justify TIER 1. Never
invent a signal ID. Current-interest, reading-preference, inferred, and
speculative signals may affect lane and score but may not justify TIER 1.

Use these signals only for private ranking. Do NOT copy or quote them into the public report.

=== TIER CLASSIFICATION (for accepted papers only) ===

Assign TIER 1 only if the paper (Track A only) directly matches an exact signal ID in `tier_1_signal_ids`.

Assign TIER 2 if the paper (Track A) is rigorous and relevant to AI + labor/education generally, but does not directly target one of those private signals.

Assign TIER 3 if the paper qualifies under Track B (methodology paper useful for economics research). These are lower-priority reads — skim for technique.

=== PORTFOLIO LANE ===

Assign exactly one lane:
- exploit: direct support for a high-value active/current/preference signal.
- adjacent: relevant neighboring mechanism, setting, dataset, or outcome.
- contradiction: credible counterevidence, boundary condition, null result, or design that could change a current belief.
- methodology: Track B methods/tools.

Do not force every direct match into exploit: use contradiction when its main value is challenging an existing belief.

=== PAPER TO EVALUATE ===
Title: {p.title}
Abstract: {p.abstract[:1200]}

Respond in JSON only:
{{ "accept": true/false, "tier": 1, 2, or 3, "lane": "exploit|adjacent|contradiction|methodology", "score": 0-100, "methodology": "e.g. RCT, DiD, IV, Structural, Methodology, Descriptive", "matched_signal": "signal id from profile, or general_fit|methodology|none", "reason": "Private one-sentence explanation for logs only. Do not include private profile wording." }}
"""

        try:
            response_error = None
            resp = None
            for attempt in range(3):
                try:
                    time.sleep(0.25 * (2 ** attempt))
                    resp = client.models.generate_content(
                        model=cfg.gemini_model,
                        contents=prompt,
                        config={
                            'response_mime_type': 'application/json',
                            'temperature': 0,
                        }
                    )
                    break
                except Exception as exc:
                    response_error = exc
            if resp is None:
                raise RuntimeError(f"model evaluation failed after 3 attempts: {response_error}")

            text = resp.text
            if not text:
                raise ValueError("model returned an empty response")

            result = json.loads(text)
            accept = result.get("accept") is True
            method = str(result.get("methodology", "Unknown"))[:80]
            tier = int(result.get("tier", 2))
            if tier not in (1, 2, 3):
                raise ValueError(f"invalid tier: {tier}")
            matched_signal = str(result.get("matched_signal", "none"))[:120]
            validation_profile = (
                profile if isinstance(profile, RecommendationProfile) else RecommendationProfile()
            )
            tier = enforce_tier_1_contract(tier, matched_signal, validation_profile)
            lane = str(result.get("lane", ""))
            if lane not in LANES:
                lane = default_lane(tier=tier, matched_signal=matched_signal, methodology=method)
            score = max(0.0, min(100.0, float(result.get("score", 50))))

            if accept:
                p.relevance_reason = f"[{method}] {result.get('reason', '')}"
                p.tier = tier
                p.methodology = method
                p.matched_signal = matched_signal
                p.lane = lane
                p.recommendation_score = score
                relevant_papers.append(p)
                sys.stdout.buffer.write(
                    f"[{i+1}] [T{tier} YES - {method}] {p.title[:60]}...\n".encode('utf-8', errors='replace')
                )
            else:
                sys.stdout.buffer.write(
                    f"[{i+1}] [NO - {method}]  {p.title[:60]}...\n".encode('utf-8', errors='replace')
                )

        except Exception as e:
            evaluation_errors += 1
            sys.stdout.buffer.write(f"[{i+1}] [ERR] {e}\n".encode('utf-8', errors='replace'))

    evaluated = sum(1 for paper in papers if paper.abstract and len(paper.abstract) >= 50)
    if evaluated and evaluation_errors / evaluated > 0.20:
        raise RuntimeError(
            f"Model evaluation failure rate {evaluation_errors}/{evaluated} exceeds 20%"
        )

    log(f"--- Filter done. Kept {len(relevant_papers)}/{len(papers)} papers "
        f"(T1: {sum(1 for p in relevant_papers if p.tier == 1)}, "
        f"T2: {sum(1 for p in relevant_papers if p.tier == 2)}, "
        f"T3: {sum(1 for p in relevant_papers if p.tier == 3)}) ---")
    return relevant_papers

# =========================================================
# 5) Paper Card Formatter (original abstract, no LLM summarization)
# =========================================================

def format_paper_card(p: Paper) -> str:
    """Format a public paper card without private recommendation reasons."""
    abstract = p.abstract.strip()
    if len(abstract) > 1000:
        abstract = abstract[:1000] + "..."
    return (
        f"### {p.title}\n"
        f"- **Authors**: {p.authors or 'N/A'}\n"
        f"- **Source**: {p.venue} | {p.published}\n"
        f"- **Abstract**:\n\n  > {abstract}\n\n"
        f"- 🔗 {p.url}\n"
    )

# =========================================================
# 6) Reading Queue Update
# =========================================================

def slugify(title: str) -> str:
    """Convert title to a stable URL-safe slug for use as unique key."""
    import re
    s = title.lower()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'\s+', '-', s.strip())
    return s[:60]

def update_reading_queue(
    papers: List[Paper],
    queue_path: str = "reading_queue.md",
    *,
    state_path: str = "queue_state.jsonl",
    max_new: int = 15,
    lane_mix: str | None = None,
) -> dict:
    """Update canonical JSONL state and regenerate the legacy Markdown view."""

    summary = update_queue_state(
        papers,
        state_path=state_path,
        markdown_path=queue_path,
        max_new=max_new,
        lane_weights=parse_lane_weights(lane_mix),
    )
    log(
        "Reading queue updated: "
        f"+{summary['added']} new papers; lanes={summary['lane_counts']}; "
        f"active={summary['total_active']}"
    )
    return summary


# =========================================================
# 7) Main Pipeline
# =========================================================

def main() -> dict:
    cfg = load_config()

    if not cfg.google_api_key or "YOUR_KEY" in cfg.google_api_key:
        raise ValueError("GOOGLE_API_KEY is missing or still contains a placeholder")

    client = Client(api_key=cfg.google_api_key)

    # 0. Load only structured, compact recommendation signals.
    profile = load_compact_recommendation_profile()
    log(
        "Recommendation profile loaded "
        f"({len(profile.retrieval_terms)} retrieval terms, "
        f"{len(profile.active_signals)} active signals, "
        f"{len(profile.current_interests)} current interests, "
        f"{len(profile.reading_preferences)} preference signals)."
    )

    # 1. Fetch with an explicit source-health contract.
    health = SourceHealthReport(run_date=dt.date.today().isoformat())
    source_specs = [
        ("openalex", True, lambda: fetch_openalex_econ(cfg, profile)),
        ("arxiv", True, lambda: fetch_arxiv_econ(cfg, profile)),
        ("nber", True, lambda: fetch_nber_papers(cfg)),
        ("iza", False, lambda: fetch_iza_papers(cfg)),
        ("aea", False, lambda: fetch_aea_papers(cfg)),
        ("cepr", False, lambda: fetch_cepr_papers(cfg)),
        ("worldbank", False, lambda: fetch_worldbank_papers(cfg)),
    ]
    candidates: List[Paper] = []
    for source_name, core, fetcher in source_specs:
        try:
            source_papers = fetcher()
            candidates.extend(source_papers)
            health.success(source_name, len(source_papers), core=core)
        except Exception as exc:
            health.failure(source_name, exc, core=core)
            log(f"SOURCE FAILURE [{source_name}]: {safe_error_summary(exc)}")
            if isinstance(exc, SourceConfigurationError):
                break

    health_status = health.finalize(failure_threshold=cfg.source_failure_threshold)
    health.write(cfg.source_health_path)
    if health_status == "failed":
        raise RuntimeError(
            "Paper source health failed: " + "; ".join(health.errors)
        )

    # 2. Dedupe
    unique_candidates = dedupe_papers(candidates)
    log(f"Unique candidates: {len(unique_candidates)}")
    evaluation_candidates = stratified_evaluation_sample(
        unique_candidates, cfg.evaluation_max
    )
    if len(evaluation_candidates) < len(unique_candidates):
        log(
            "Pre-model evaluation cap applied: "
            f"{len(evaluation_candidates)}/{len(unique_candidates)} candidates "
            "selected by source and recency"
        )

    # 3. Econ Rigor Filter (The JMP Check)
    final_selection = (
        llm_econ_rigor_check(client, cfg, evaluation_candidates, profile)
        if evaluation_candidates
        else []
    )

    # 4. Apply one global weekly cap and a configurable portfolio lane mix.
    final_selection.sort(
        key=lambda paper: (paper.recommendation_score, paper.published), reverse=True
    )
    effective_lane_mix = cfg.lane_mix
    if "PAPER_TRACKER_LANE_MIX" not in os.environ and profile.lane_weights:
        effective_lane_mix = ",".join(
            f"{lane}:{profile.lane_weights[lane]}"
            for lane in LANES
            if lane in profile.lane_weights
        )
    queue_summary = update_reading_queue(
        final_selection,
        queue_path=cfg.queue_markdown_path,
        state_path=cfg.queue_state_path,
        max_new=cfg.weekly_max_new,
        lane_mix=effective_lane_mix,
    )
    weekly_selection = queue_summary["selected_papers"]
    tier1 = [p for p in weekly_selection if p.tier == 1]
    tier2 = [p for p in weekly_selection if p.tier == 2]
    tier3 = [p for p in weekly_selection if p.tier == 3]

    # 5. Build report
    log(f"Building report: {len(tier1)} Tier 1, {len(tier2)} Tier 2, {len(tier3)} Tier 3 papers...")

    report_lines = [
        f"# 📊 AI + Economics Weekly Paper Digest",
        f"**Sources**: NBER, IZA, NEP-AIN, NEP-LAB, NEP-LMA, AEA, CEPR, World Bank, arXiv",
        f"**Date**: {dt.date.today()}",
        f"**Source health**: {health_status.upper()} (`{cfg.source_health_path}`)",
        f"**Papers**: {len(tier1)} priority + {len(tier2)} additional relevant + {len(tier3)} methodology",
        f"**Portfolio lanes**: {queue_summary['lane_counts']}",
        "",
    ]

    if not weekly_selection:
        report_lines += [
            "No new papers passed the filters and queue deduplication this week.",
            "",
        ]

    if tier1:
        report_lines += [
            "---",
            f"## 🔴 Tier 1 — Priority Papers ({len(tier1)} papers)",
            "*Highest-priority papers from this week's screened sources.*",
            "",
        ]
        for p in tier1:
            report_lines.append(format_paper_card(p))
            report_lines.append("")

    if tier2:
        report_lines += [
            "---",
            f"## 🟡 Tier 2 — Additional Relevant Papers ({len(tier2)} papers)",
            "*Relevant AI + economics papers from this week's screened sources.*",
            "",
        ]
        for p in tier2:
            report_lines.append(format_paper_card(p))
            report_lines.append("")

    if tier3:
        report_lines += [
            "---",
            f"## 🔵 Tier 3 — Methodology Papers ({len(tier3)} papers)",
            "*Methods or tools that may be useful for economics research.*",
            "",
        ]
        for p in tier3:
            report_lines.append(format_paper_card(p))
            report_lines.append("")

    filename = f"Econ_JMP_Report_EN_{dt.date.today()}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    log(f"✅ Done! Saved to {filename}")

    # Generate PDF (email sending handled by run_weekly_digest.py)
    try:
        from utils_pdf_email import markdown_to_pdf

        log("Converting MD to PDF...")
        pdf_path = markdown_to_pdf(filename)
        log(f"PDF created: {pdf_path}")

    except ImportError:
        log("PDF utilities not available, skipping PDF generation")
    except Exception as e:
        log(f"Error in PDF generation: {e}")

    return {
        "report_path": filename,
        "source_health_path": cfg.source_health_path,
        "health_status": health_status,
        "queue_state_path": cfg.queue_state_path,
        "queue_markdown_path": cfg.queue_markdown_path,
        "queue_summary": queue_summary,
    }

if __name__ == "__main__":
    main()
