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

# =========================================================
# 1) Config
# =========================================================

@dataclass
class Config:
    google_api_key: str
    gemini_model: str = "gemini-2.0-flash" 
    
    # Search Window
    days_back: int = 7  
    
    # Limits
    max_candidates_per_source: int = 250
    final_max_papers: int = 15

    # OpenAlex Concept IDs
    # STRICTLY Economics (C162324750) and Econometrics (C149178828)
    openalex_concepts: str = "C162324750|C149178828"

def load_config() -> Config:
    # Read API key from environment variable (required for GitHub Actions)
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is not set. Please configure it in GitHub Secrets.")
    return Config(google_api_key=api_key)

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

def dedupe_papers(papers: List[Paper]) -> List[Paper]:
    seen_titles = set()
    unique = []
    for p in papers:
        t_norm = "".join(x for x in p.title.lower() if x.isalnum())
        if t_norm not in seen_titles:
            seen_titles.add(t_norm)
            unique.append(p)
    return unique

# =========================================================
# 3) Sources (Strict Econ Focus)
# =========================================================

def fetch_openalex_econ(cfg: Config) -> List[Paper]:
    log(f"Fetching OpenAlex (Strict Economics Concepts)...")
    base_url = "https://api.openalex.org/works"
    start_date = (dt.date.today() - dt.timedelta(days=cfg.days_back)).strftime("%Y-%m-%d")
    
    # Search logic:
    # Concepts MUST be Economics.
    # Text MUST mention AI AND (Education OR Labor terms).
    ai_search = '("artificial intelligence" OR "large language model" OR "generative AI" OR "ChatGPT" OR "GPT-4" OR "LLM") AND (education OR learning OR schooling OR labor OR employment OR wages OR "labor market" OR "human capital" OR productivity OR automation OR occupation OR skill)'
    
    params = {
        "filter": f"concepts.id:{cfg.openalex_concepts},from_publication_date:{start_date}",
        "search": ai_search,
        "sort": "publication_date:desc",
        "per_page": cfg.max_candidates_per_source,
    }

    try:
        r = requests.get(base_url, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        
        results = []
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

            results.append(Paper(
                source="OpenAlex (Econ)",
                title=item.get('title', 'No Title'),
                abstract=abstract,
                url=item.get('ids', {}).get('openalex', ''),
                published=item.get('publication_date', ''),
                venue=venue,
                authors=authors_str
            ))
        
        log(f"Found {len(results)} Econ candidates from OpenAlex.")
        return results

    except Exception as e:
        log(f"Error fetching OpenAlex: {e}")
        return []

def fetch_arxiv_econ(cfg: Config) -> List[Paper]:
    """
    ArXiv pre-filtered for Causal Inference terms to reduce noise.
    """
    log("Fetching ArXiv (Econ/Quant-Fin focus)...")
    
    query = '(all:"large language model" OR all:"generative AI" OR all:"ChatGPT" OR all:"GPT-4" OR all:"artificial intelligence") AND (all:"causal inference" OR all:"difference-in-differences" OR all:"randomized" OR all:"instrumental variable" OR all:"regression discontinuity" OR all:econometrics OR all:"labor market" OR all:education OR all:employment OR all:automation OR all:wages OR all:productivity)'
    
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
                    url=r.entry_id,
                    published=pub_date,
                    venue="arXiv",
                    authors=authors
                ))
    except Exception as e:
        log(f"Error fetching ArXiv: {e}")
        
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

    for feed_url, feed_name in feeds:
        try:
            feed = feedparser.parse(feed_url)

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

        except Exception as e:
            log(f"Error fetching {feed_name}: {e}")
            continue

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

    for feed_url, feed_name in feeds:
        try:
            feed = feedparser.parse(feed_url)

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

        except Exception as e:
            log(f"Error fetching {feed_name} for IZA: {e}")
            continue

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
        "mailto": os.environ.get("RECIPIENT_EMAIL", ""),
    }

    seen_dois = set()
    try:
        r = requests.get(crossref_url, params=params, timeout=30)
        r.raise_for_status()
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
            ))

    except Exception as e:
        log(f"Error fetching AEA via CrossRef: {e}")

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

    for feed_url, journal_name in aea_rss_feeds:
        try:
            feed = feedparser.parse(feed_url)
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
                        doi_resp = requests.get(
                            f"https://api.crossref.org/works/{doi}",
                            params={"mailto": os.environ.get("RECIPIENT_EMAIL", "")},
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
                ))
        except Exception as e:
            log(f"Error fetching AEA RSS ({journal_name}): {e}")
            continue

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
        feed = feedparser.parse("https://cepr.org/rss/discussion-paper")
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
    except Exception as e:
        log(f"Error fetching CEPR RSS: {e}")

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
        r = requests.get("https://search.worldbank.org/api/v3/wds", params=params, timeout=30)
        r.raise_for_status()
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
    except Exception as e:
        log(f"Error fetching World Bank papers: {e}")

    log(f"Found {len(results)} World Bank candidates.")
    return results

# =========================================================
# 4) The Filter (The "JMP Referee")
# =========================================================

def llm_econ_rigor_check(client: Client, cfg: Config, papers: List[Paper], profile: str = "") -> List[Paper]:
    log(f"--- Starting Econ Rigor Check (JMP Filter) on {len(papers)} papers ---")
    relevant_papers = []

    profile_section = profile if profile else (
        "The researcher studies economic effects of AI on education and labor markets, "
        "using causal inference methods (RCT, DiD, IV, RDD, event study) and structural models."
    )

    for i, p in enumerate(papers):
        if not p.abstract or len(p.abstract) < 50:
            continue

        prompt = f"""
You are a research assistant for a PhD student in Economics. Your job is to decide whether a paper belongs in their weekly reading list, and if so, how high a priority it is.

=== RESEARCHER PROFILE ===
{profile_section}

=== SELECTION RULES ===

ACCEPT the paper ONLY if ALL THREE conditions hold simultaneously:

1. AI IS THE MAIN SUBJECT: The paper must primarily study the economic consequences of AI/LLMs/automation/generative AI. AI must appear in the research question itself — "How does AI affect X?" — not merely as a tool the authors use.

2. ECONOMIC OUTCOME IS CENTRAL: The paper's outcome variable must be one of: student learning/achievement, teacher productivity, educational attainment, wages, employment levels, occupational structure, task displacement, labor productivity, firm-level output or innovation from AI adoption. Papers on supply chains, logistics, tourism, healthcare, climate, finance markets, or other sectors are only acceptable if they measure direct effects on workers' wages or employment.

3. METHODOLOGY IS RIGOROUS: Must use at least one of: RCT, DiD, IV, RDD, event study, or structural economic model with calibrated parameters. Pure descriptive, conceptual, or narrative papers are REJECTED regardless of topic.

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
- Papers where AI is only used as a measurement instrument and the topic itself is unrelated to AI's economic effects

=== TIER CLASSIFICATION (for accepted papers only) ===

Assign TIER 1 if the paper directly addresses one or more of the researcher's ACTIVE RESEARCH DIRECTIONS listed in the profile (e.g., human capital trap / skill formation, entry-level labor markets, AI and selective reporting / p-hacking, knowledge velocity by field, information frictions and labor market entry).

Assign TIER 2 if the paper is rigorous and relevant to AI + labor/education generally, but does not directly target one of those active directions.

=== PAPER TO EVALUATE ===
Title: {p.title}
Abstract: {p.abstract[:1200]}

Respond in JSON only:
{{ "accept": true/false, "tier": 1 or 2, "methodology": "e.g. RCT, DiD, IV, Structural, Theory, Descriptive", "reason": "One sentence explaining accept/reject decision and tier assignment with specific reference to the paper content" }}
"""

        try:
            time.sleep(1.0)

            resp = client.models.generate_content(
                model=cfg.gemini_model,
                contents=prompt,
                config={'response_mime_type': 'application/json'}
            )

            text = resp.text
            if not text:
                continue

            result = json.loads(text)
            accept = result.get("accept", False)
            method = result.get("methodology", "Unknown")
            tier = int(result.get("tier", 2))

            if accept:
                p.relevance_reason = f"[{method}] {result.get('reason', '')}"
                p.tier = tier
                relevant_papers.append(p)
                sys.stdout.buffer.write(
                    f"[{i+1}] [T{tier} YES - {method}] {p.title[:60]}...\n".encode('utf-8', errors='replace')
                )
            else:
                sys.stdout.buffer.write(
                    f"[{i+1}] [NO - {method}]  {p.title[:60]}...\n".encode('utf-8', errors='replace')
                )

        except Exception as e:
            sys.stdout.buffer.write(f"[{i+1}] [ERR] {e}\n".encode('utf-8', errors='replace'))

    log(f"--- Filter done. Kept {len(relevant_papers)}/{len(papers)} papers "
        f"(T1: {sum(1 for p in relevant_papers if p.tier == 1)}, "
        f"T2: {sum(1 for p in relevant_papers if p.tier == 2)}) ---")
    return relevant_papers

# =========================================================
# 5) Paper Card Formatter (original abstract, no LLM summarization)
# =========================================================

def format_paper_card(p: Paper) -> str:
    """Format a paper as a readable card using the original abstract verbatim."""
    abstract = p.abstract.strip()
    if len(abstract) > 1000:
        abstract = abstract[:1000] + "..."
    return (
        f"### {p.title}\n"
        f"- **Authors**: {p.authors or 'N/A'}\n"
        f"- **Source**: {p.venue} | {p.published}\n"
        f"- **Method & Why included**: {p.relevance_reason}\n"
        f"- **Abstract**:\n\n  > {abstract}\n\n"
        f"- 🔗 {p.url}\n"
    )

# =========================================================
# 6) Main Pipeline
# =========================================================

def main():
    cfg = load_config()

    if not cfg.google_api_key or "YOUR_KEY" in cfg.google_api_key:
        print("⚠️ ERROR: Please set GOOGLE_API_KEY env var.")

    client = Client(api_key=cfg.google_api_key)

    # 0. Load researcher profile
    profile = load_researcher_profile()
    log(f"Researcher profile loaded ({len(profile)} chars).")

    # 1. Fetch
    candidates = []
    candidates.extend(fetch_openalex_econ(cfg))
    candidates.extend(fetch_arxiv_econ(cfg))
    candidates.extend(fetch_nber_papers(cfg))
    candidates.extend(fetch_iza_papers(cfg))
    candidates.extend(fetch_aea_papers(cfg))
    candidates.extend(fetch_cepr_papers(cfg))
    candidates.extend(fetch_worldbank_papers(cfg))

    # 2. Dedupe
    unique_candidates = dedupe_papers(candidates)
    log(f"Unique candidates: {len(unique_candidates)}")

    if not unique_candidates:
        return

    # 3. Econ Rigor Filter (The JMP Check)
    final_selection = llm_econ_rigor_check(client, cfg, unique_candidates, profile)

    if not final_selection:
        log("No rigorous econ papers found. (Try increasing days_back in Config)")
        return

    # 4. Split by tier and sort by date within each tier
    final_selection.sort(key=lambda x: x.published, reverse=True)
    tier1 = [p for p in final_selection if p.tier == 1][:cfg.final_max_papers]
    tier2 = [p for p in final_selection if p.tier == 2][:cfg.final_max_papers]

    # 5. Build report
    log(f"Building report: {len(tier1)} Tier 1, {len(tier2)} Tier 2 papers...")

    report_lines = [
        f"# 📊 AI + Economics Weekly Paper Digest",
        f"**Sources**: NBER, IZA, NEP-AIN, NEP-LAB, NEP-LMA, AEA, CEPR, World Bank, arXiv",
        f"**Date**: {dt.date.today()}",
        f"**Papers**: {len(tier1)} priority + {len(tier2)} for reference",
        "",
    ]

    if tier1:
        report_lines += [
            "---",
            f"## 🔴 Tier 1 — Priority Read ({len(tier1)} papers)",
            "*Directly targets active research directions. Read in full.*",
            "",
        ]
        for p in tier1:
            report_lines.append(format_paper_card(p))
            report_lines.append("")

    if tier2:
        report_lines += [
            "---",
            f"## 🟡 Tier 2 — For Reference ({len(tier2)} papers)",
            "*Rigorous AI + labor/education papers. Scan abstract and note if relevant.*",
            "",
        ]
        for p in tier2:
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

if __name__ == "__main__":
    main()