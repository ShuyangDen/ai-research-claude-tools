"""
Econ JMP Paper Tracker (Causal Inference & Rigorous Methods)
UPDATED v5:
1) FIXED: Summaries are now strictly in Chinese. 
   - The LLM prompt template uses Chinese keys (e.g., '识别策略' instead of 'Identification').
2) Source: OpenAlex restricted strictly to ECONOMICS concept (C162324750).
3) Filter: "The Identification Police" (Rejects non-causal papers).

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
    days_back: int = 7  # Econ papers move slower, look back 2 weeks
    
    # Limits
    max_candidates_per_source: int = 100
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

    # AEA publishes monthly issues (on the 1st of each month).
    # Use a 35-day window to always capture the most recent issue regardless of run date.
    aea_days_back = max(cfg.days_back, 35)
    cutoff_date = dt.date.today() - dt.timedelta(days=aea_days_back)
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
                    authors=authors_str,
                ))
        except Exception as e:
            log(f"Error fetching AEA RSS ({journal_name}): {e}")
            continue

    log(f"Found {len(results)} AEA candidates from CrossRef + RSS.")
    return results

# =========================================================
# 4) The Filter (The "JMP Referee")
# =========================================================

def llm_econ_rigor_check(client: Client, cfg: Config, papers: List[Paper]) -> List[Paper]:
    log(f"--- Starting Econ Rigor Check (JMP Filter) on {len(papers)} papers ---")
    relevant_papers = []
    
    for i, p in enumerate(papers):
        if not p.abstract or len(p.abstract) < 50:
            continue
            
        # THE JOB MARKET PAPER PROMPT
        prompt = f"""
You are a research assistant for a PhD student in Economics whose dissertation focuses on how Artificial Intelligence affects education outcomes and labor markets. Your job is to decide whether a paper belongs in their weekly reading list.

=== RESEARCHER PROFILE ===
The researcher studies the ECONOMIC EFFECTS of AI on:
- Education: student learning, teacher productivity, ed-tech adoption, tutoring tools, human capital formation
- Labor markets: employment, wages, occupational change, automation, task displacement, skill-biased technical change
- Firm-level productivity driven by AI adoption

The researcher uses CAUSAL INFERENCE methods (RCT, DiD, IV, RDD, event study) and also values well-designed structural models or rigorous empirical work even without a clean natural experiment.

=== SELECTION RULES ===

ACCEPT the paper ONLY if ALL THREE conditions hold simultaneously:

1. AI IS THE MAIN SUBJECT: The paper must primarily study the economic consequences of AI/LLMs/automation/generative AI. AI must appear in the research question itself — "How does AI affect X?" — not merely as a tool the authors use. Simply applying ML methods to non-AI questions does not qualify.

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
- Coding assistants or software development tools unless measuring programmer wages/employment
- Papers where AI is only used as a measurement instrument and the topic itself is unrelated to AI's economic effects

=== PAPER TO EVALUATE ===
Title: {p.title}
Abstract: {p.abstract[:1200]}

Respond in JSON only:
{{ "accept": true/false, "methodology": "e.g. RCT, DiD, IV, Structural, Theory, Descriptive", "reason": "One sentence explaining accept/reject decision with specific reference to the paper content" }}
"""
        
        try:
            time.sleep(1.0)
            
            resp = client.models.generate_content(
                model=cfg.gemini_model,
                contents=prompt,
                config={'response_mime_type': 'application/json'}
            )
            
            text = resp.text
            if not text: continue
            
            result = json.loads(text)
            accept = result.get("accept", False)
            method = result.get("methodology", "Unknown")
            
            if accept:
                p.relevance_reason = f"[{method}] {result.get('reason')}"
                relevant_papers.append(p)
                sys.stdout.buffer.write(f"[{i+1}] [YES - {method}] {p.title[:60]}...\n".encode('utf-8', errors='replace'))
            else:
                sys.stdout.buffer.write(f"[{i+1}] [NO - {method}]  {p.title[:60]}...\n".encode('utf-8', errors='replace'))

        except Exception as e:
            sys.stdout.buffer.write(f"[{i+1}] [ERR] {e}\n".encode('utf-8', errors='replace'))
            
    log(f"--- Filter done. Kept {len(relevant_papers)}/{len(papers)} Rigorous Papers ---")
    return relevant_papers

# =========================================================
# 5) Summarization (Strict Chinese Keys)
# =========================================================

def summarize_for_econ_phd(client: Client, cfg: Config, p: Paper) -> str:
    # Summarize paper in Chinese, focused on AI+education/labor research
    prompt = (
        "You are an Economics PhD research assistant helping a student studying how AI affects"
        " education and labor markets. Summarize the paper below. Output ENTIRELY in Simplified"
        " Chinese using Markdown.\n\n"
        "Paper Title: " + p.title + "\n"
        "Authors: " + p.authors + "\n"
        "Venue: " + p.venue + "\n"
        "Abstract: " + p.abstract + "\n"
        "Link: " + p.url + "\n\n"
        "Use this exact Markdown format:\n\n"
        "## [Translate the paper title into Chinese]\n"
        "- **\u4f5c\u8005**: " + p.authors + "\n"
        "- **\u53d1\u8868\u573a\u6240**: " + p.venue + "\n"
        "- **AI\u7ef4\u5ea6**: (\u672c\u6587\u7814\u7a76\u7684\u5177\u4f53AI\u6280\u672f\u6216\u81ea\u52a8\u5316\u5f62\u5f0f\uff1f\u4f8b\u5982\uff1a\u5927\u578b\u8bed\u8a00\u6a21\u578b\u3001\u751f\u6210\u5f0fAI\u5de5\u5177\u3001\u7b97\u6cd5\u7ba1\u7406\u3001\u81ea\u52a8\u5316\u6280\u672f)\n"
        "- **\u7ecf\u6d4e\u7ed3\u679c\u53d8\u91cf**: (AI\u5f71\u54cd\u7684\u5177\u4f53\u7ecf\u6d4e\u53d8\u91cf\uff1f\u4f8b\u5982\uff1a\u8003\u8bd5\u6210\u7ee9\u3001\u5de5\u8d44\u6c34\u5e73\u3001\u5c31\u4e1a\u7387\u3001\u804c\u4e1a\u7ed3\u6784\u53d8\u5316\u3001\u4f01\u4e1a\u751f\u4ea7\u7387)\n"
        "- **\u7814\u7a76\u65b9\u6cd5**: (\u8bf7\u7cbe\u786e\u8bf4\u660e\uff1aRCT\u968f\u673a\u5b9e\u9a8c / DiD\u53cc\u91cd\u5dee\u5206 / IV\u5de5\u5177\u53d8\u91cf / RDD\u65ad\u70b9\u56de\u5f52 / \u4e8b\u4ef6\u7814\u7a76 / \u7ed3\u6784\u6a21\u578b / \u63cf\u8ff0\u6027\u7edf\u8ba1\u3002\u7528\u4e00\u53e5\u8bdd\u63cf\u8ff0\u8bc6\u522b\u7b56\u7565\u3002)\n"
        "- **\u4e3b\u8981\u53d1\u73b0**: (\u5c3d\u91cf\u91cf\u5316\u7ed3\u679c\uff0c\u4f8b\u5982X%\u7684\u63d0\u5347\u30010.2\u4e2a\u6807\u51c6\u5dee\u7684\u589e\u957f\u3002\u8bf4\u660e\u4e3b\u8981\u7ed3\u8bba\u53ca\u7ecf\u6d4e\u5b66\u610f\u4e49\u3002)\n"
        "- **\u5bf9AI+\u6559\u80b2/\u52b3\u52a8\u7814\u7a76\u7684\u610f\u4e49**: (\u4e00\u53e5\u8bdd\u8bf4\u660e\u8fd9\u7bc7\u6587\u7ae0\u5bf9\u7814\u7a76AI\u5bf9\u4eba\u529b\u8d44\u672c\u6216\u52b3\u52a8\u529b\u5e02\u573a\u5f71\u54cd\u7684\u5b66\u8005\u6709\u4f55\u53c2\u8003\u4ef7\u503c\u3002)\n"
        "- Link: " + p.url
    )

    try:
        resp = client.models.generate_content(
            model=cfg.gemini_model,
            contents=prompt
        )
        return resp.text
    except Exception as e:
        return f"## {p.title}\n- **Error**: {e}\n- **Link**: {p.url}"

# =========================================================
# 6) Main Pipeline
# =========================================================

def main():
    cfg = load_config()
    
    if not cfg.google_api_key or "YOUR_KEY" in cfg.google_api_key:
        print("⚠️ ERROR: Please set GOOGLE_API_KEY env var.")
        # return

    client = Client(api_key=cfg.google_api_key)
    
    # 1. Fetch
    candidates = []
    candidates.extend(fetch_openalex_econ(cfg))
    candidates.extend(fetch_arxiv_econ(cfg))
    candidates.extend(fetch_nber_papers(cfg))
    candidates.extend(fetch_iza_papers(cfg))
    candidates.extend(fetch_aea_papers(cfg))      
    
    # 2. Dedupe
    unique_candidates = dedupe_papers(candidates)
    log(f"Unique candidates: {len(unique_candidates)}")
    
    if not unique_candidates:
        return

    # 3. Econ Rigor Filter (The JMP Check)
    # No limit on input size
    final_selection = llm_econ_rigor_check(client, cfg, unique_candidates)
    
    if not final_selection:
        log("No rigorous econ papers found. (Try increasing days_back in Config)")
        return

    # 4. Generate Report
    log("Generating Econ Summaries (Chinese)...")
    report_lines = [f"# 📉 Econ JMP Paper Digest (Causal Inference Focus)",
                   f"Sources: OpenAlex, arXiv, NBER, IZA",
                   f"Date: {dt.date.today()}", ""]
    
    final_selection.sort(key=lambda x: x.published, reverse=True)
    top_papers = final_selection[:cfg.final_max_papers]
    
    for i, p in enumerate(top_papers, 1):
        log(f"Summarizing [{i}]: {p.title[:40]}...")
        summary = summarize_for_econ_phd(client, cfg, p)
        report_lines.append(summary)
        report_lines.append("---")
        sys.stdout.buffer.write((summary + "\n").encode('utf-8', errors='replace'))
        
    filename = f"Econ_JMP_Report_{dt.date.today()}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    log(f"✅ Done! Saved to {filename}")

    # Generate PDF (email sending handled by run_weekly_digest.py)
    try:
        from utils_pdf_email import markdown_to_pdf

        # Convert to PDF
        log("Converting MD to PDF...")
        pdf_path = markdown_to_pdf(filename)
        log(f"PDF created: {pdf_path}")

    except ImportError:
        log("PDF utilities not available, skipping PDF generation")
    except Exception as e:
        log(f"Error in PDF generation: {e}")

if __name__ == "__main__":
    main()