from __future__ import annotations

"""Multi-source web fetcher: Google/Scholar (optional), DuckDuckGo, Semantic Scholar.

Google and Google Scholar are supported via SerpAPI when `SERPAPI_API_KEY`
is available. Otherwise the pipeline falls back to free sources.
"""

import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Iterable, List, Optional
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; ResearchAgent/0.2; "
        "+https://github.com/research-agent)"
    ),
}

_SERPAPI_URL = "https://serpapi.com/search.json"
_S2_SEARCH = "https://api.semanticscholar.org/graph/v1/paper/search"
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_LIKELY_CN_DOMAINS = {
    "zhihu.com",
    "zhidao.baidu.com",
    "baike.baidu.com",
    "tieba.baidu.com",
    "weibo.com",
    "bilibili.com",
    "csdn.net",
    "juejin.cn",
}


@dataclass
class WebResult:
    """A single result returned by a search source."""

    uid: str
    title: str
    url: str
    snippet: str
    source: str  # "web", "google", "semantic_scholar", "google_scholar"
    body: str = ""  # full extracted text (filled by scrape step)
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    pdf_url: Optional[str] = None
    pdf_path: Optional[str] = None


def _contains_cjk(text: str) -> bool:
    return bool(_CJK_RE.search(text or ""))


def _is_chinese_result(r: WebResult) -> bool:
    host = urlparse(r.url or "").netloc.lower()
    if host.endswith(".cn") or any(host.endswith(x) for x in _LIKELY_CN_DOMAINS):
        return True
    return _contains_cjk(f"{r.title} {r.snippet}")


def _url_to_uid(url: str) -> str:
    """Convert a URL to a filesystem-safe UID fragment."""
    parsed = urlparse(url)
    host = parsed.netloc.replace("www.", "")
    path = parsed.path.strip("/").replace("/", "_")
    raw = f"{host}_{path}" if path else host
    return re.sub(r"[^a-zA-Z0-9._-]", "_", raw)[:120]


def dedup_results(*result_lists: List[WebResult]) -> List[WebResult]:
    """Merge multiple result lists, deduplicating by uid."""
    seen: dict[str, WebResult] = {}
    for lst in result_lists:
        for r in lst:
            if r.uid not in seen:
                seen[r.uid] = r
    return list(seen.values())


def filter_results_by_domain(
    results: List[WebResult],
    *,
    blocked_domains: Iterable[str] | None = None,
) -> List[WebResult]:
    blocked = {d.strip().lower() for d in (blocked_domains or []) if d and d.strip()}
    if not blocked:
        return results

    out: List[WebResult] = []
    for r in results:
        host = urlparse(r.url or "").netloc.lower()
        if any(host == d or host.endswith(f".{d}") for d in blocked):
            continue
        out.append(r)
    return out


def prioritize_results(
    results: List[WebResult],
    *,
    max_results: int,
    prefer_english: bool = True,
    max_chinese_ratio: float = 0.25,
) -> List[WebResult]:
    """Prefer English/global sources first, then Chinese sources."""
    uniq = dedup_results(results)
    if not prefer_english:
        return uniq[:max_results]

    en_like: List[WebResult] = []
    zh_like: List[WebResult] = []
    for r in uniq:
        if _is_chinese_result(r):
            zh_like.append(r)
        else:
            en_like.append(r)

    zh_cap = max(0, int(max_results * max(0.0, min(max_chinese_ratio, 1.0))))

    out: List[WebResult] = en_like[:max_results]
    if len(out) < max_results:
        out.extend(zh_like[: max_results - len(out)])
    elif zh_cap > 0:
        keep_en = max_results - zh_cap
        out = en_like[:keep_en] + zh_like[:zh_cap]
    return out[:max_results]


def _search_serpapi(
    query: str,
    *,
    engine: str,
    max_results: int = 10,
    hl: str = "en",
    gl: str = "us",
) -> List[dict]:
    key = os.getenv("SERPAPI_API_KEY", "").strip()
    if not key:
        return []
    try:
        resp = requests.get(
            _SERPAPI_URL,
            params={
                "api_key": key,
                "engine": engine,
                "q": query,
                "num": min(max_results, 20),
                "hl": hl,
                "gl": gl,
            },
            headers=_HEADERS,
            timeout=30,
        )
        resp.raise_for_status()
        return (resp.json() or {}).get("organic_results", []) or []
    except Exception as e:
        logger.error("SerpAPI search failed (engine=%s): %s", engine, e)
        return []


def search_google(
    query: str,
    max_results: int = 10,
    *,
    hl: str = "en",
    gl: str = "us",
) -> List[WebResult]:
    """Search Google via SerpAPI when `SERPAPI_API_KEY` is set."""
    rows = _search_serpapi(query, engine="google", max_results=max_results, hl=hl, gl=gl)
    out: List[WebResult] = []
    for i, row in enumerate(rows):
        url = row.get("link", "")
        uid = f"web:{_url_to_uid(url)}" if url else f"web:google_{i}"
        out.append(
            WebResult(
                uid=uid,
                title=row.get("title", ""),
                url=url,
                snippet=row.get("snippet", "") or "",
                source="google",
            )
        )
    return out


def search_google_scholar(
    query: str,
    max_results: int = 10,
) -> List[WebResult]:
    """Search Google Scholar via SerpAPI when `SERPAPI_API_KEY` is set."""
    rows = _search_serpapi(query, engine="google_scholar", max_results=max_results, hl="en", gl="us")
    out: List[WebResult] = []
    for i, row in enumerate(rows):
        url = row.get("link", "") or row.get("resources", [{}])[0].get("link", "")
        result_id = row.get("result_id", "")
        uid = f"gs:{result_id}" if result_id else (f"web:{_url_to_uid(url)}" if url else f"gs:{i}")
        pub_info = row.get("publication_info", {}) or {}
        summary = pub_info.get("summary", "") or ""
        authors = [a.get("name", "") for a in pub_info.get("authors", []) if a.get("name")]
        year_match = re.search(r"(19|20)\d{2}", summary)
        year = int(year_match.group(0)) if year_match else None
        out.append(
            WebResult(
                uid=uid,
                title=row.get("title", ""),
                url=url,
                snippet=row.get("snippet", "") or summary,
                source="google_scholar",
                authors=authors,
                year=year,
            )
        )
    return out


def search_duckduckgo(
    query: str,
    max_results: int = 10,
    *,
    region: str = "us-en",
) -> List[WebResult]:
    """Search the web via DuckDuckGo (no API key needed)."""
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        logger.error(
            "duckduckgo-search not installed. "
            "Run: pip install duckduckgo-search"
        )
        return []

    results: List[WebResult] = []
    try:
        with DDGS() as ddgs:
            hits = list(ddgs.text(query, region=region, max_results=max_results))
        for i, h in enumerate(hits):
            url = h.get("href", h.get("link", ""))
            uid = f"web:{_url_to_uid(url)}" if url else f"web:ddg_{i}"
            results.append(
                WebResult(
                    uid=uid,
                    title=h.get("title", ""),
                    url=url,
                    snippet=h.get("body", ""),
                    source="web",
                )
            )
    except Exception as e:
        logger.error("DuckDuckGo search failed: %s", e)
    return results


def search_semantic_scholar(
    query: str,
    max_results: int = 10,
) -> List[WebResult]:
    """Search Semantic Scholar for academic papers (free, no key)."""
    results: List[WebResult] = []
    try:
        resp = requests.get(
            _S2_SEARCH,
            params={
                "query": query,
                "limit": min(max_results, 100),
                "fields": "title,authors,year,abstract,externalIds,url,openAccessPdf",
            },
            headers=_HEADERS,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
    except Exception as e:
        logger.error("Semantic Scholar search failed: %s", e)
        return []

    for paper in data:
        paper_id = paper.get("paperId", "")
        ext = paper.get("externalIds") or {}
        arxiv_id = ext.get("ArXiv", "")
        doi = ext.get("DOI", "")

        if arxiv_id:
            uid = f"arxiv:{arxiv_id}"
        elif doi:
            uid = f"doi:{doi}"
        else:
            uid = f"s2:{paper_id}"

        authors = [a.get("name", "") for a in (paper.get("authors") or [])]
        pdf_info = paper.get("openAccessPdf") or {}
        pdf_url = pdf_info.get("url")

        results.append(
            WebResult(
                uid=uid,
                title=paper.get("title", ""),
                url=paper.get("url", f"https://www.semanticscholar.org/paper/{paper_id}"),
                snippet=paper.get("abstract", "") or "",
                source="semantic_scholar",
                authors=authors,
                year=paper.get("year"),
                pdf_url=pdf_url,
            )
        )
    return results


def fetch_page_content(
    url: str,
    timeout: int = 20,
) -> str:
    """Extract main textual content from a web page."""
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=timeout)
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        logger.warning("Failed to fetch %s: %s", url, e)
        return ""

    try:
        import trafilatura

        text = trafilatura.extract(html, include_links=False, include_tables=True)
        if text:
            return text.strip()
    except ImportError:
        pass

    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text[:50000]
    except ImportError:
        pass

    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:50000]


def scrape_results(
    results: List[WebResult],
    *,
    polite_delay_sec: float = 0.5,
    max_chars: int = 30000,
) -> List[WebResult]:
    """Fetch full body text for each WebResult that has a URL."""
    for r in results:
        if r.body or not r.url:
            continue
        if r.url.lower().endswith(".pdf"):
            continue
        logger.info("Scraping: %s", r.url)
        r.body = fetch_page_content(r.url)[:max_chars]
        if polite_delay_sec > 0:
            time.sleep(polite_delay_sec)
    return results
