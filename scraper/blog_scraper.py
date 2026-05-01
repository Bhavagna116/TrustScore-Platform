"""
blog_scraper.py
---------------
Scrapes 3 pre-defined blog posts using newspaper3k with BeautifulSoup fallback.
Extracts: title, author, publish date, full text, and source metadata.
Uses async HTTP requests for performance.
"""

import asyncio
import aiohttp
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# ── Pre-defined blog URLs to scrape ─────────────────────────────────────────
BLOG_URLS = [
    "https://www.who.int/news-room/feature-stories/detail/who-can-i-believe-helping-people-navigate-an-infodemic",
    "https://hbr.org/2023/07/how-to-use-ai-responsibly",
    "https://www.nature.com/articles/d41586-023-03817-6",
]


def _extract_with_newspaper(url: str) -> dict:
    """
    Primary extraction using newspaper3k library.
    Falls back to BeautifulSoup on failure.
    """
    try:
        from newspaper import Article
        article = Article(url)
        article.download()
        article.parse()
        article.nlp()

        author = ", ".join(article.authors) if article.authors else "Unknown"
        pub_date = ""
        if article.publish_date:
            pub_date = article.publish_date.strftime("%Y-%m-%d")

        return {
            "title": article.title or "",
            "author": author,
            "published_date": pub_date,
            "text": article.text or "",
            "description": article.meta_description or article.summary or "",
            "success": True,
        }
    except Exception as e:
        logger.warning(f"newspaper3k failed for {url}: {e}")
        return {"success": False}


def _extract_with_bs4(url: str, html: str) -> dict:
    """
    Fallback extraction using BeautifulSoup.
    Attempts to find common article patterns in the HTML.
    """
    soup = BeautifulSoup(html, "lxml")

    # Remove navigation, ads, footer, sidebar elements
    for tag in soup.find_all(
        ["nav", "footer", "aside", "script", "style",
         "header", "advertisement", "iframe"]
    ):
        tag.decompose()

    for tag in soup.find_all(class_=re.compile(
        r"(nav|menu|sidebar|ad|cookie|popup|banner|footer|header|social|share|comment)",
        re.I
    )):
        tag.decompose()

    # Extract title
    title = ""
    for selector in ["h1", 'meta[property="og:title"]', "title"]:
        el = soup.find(selector)
        if el:
            title = el.get("content", "") or el.get_text(strip=True)
            if title:
                break

    # Extract author
    author = "Unknown"
    for selector in [
        'meta[name="author"]', 'meta[property="article:author"]',
        '[rel="author"]', ".author", ".byline", '[itemprop="author"]'
    ]:
        el = soup.find(selector)
        if el:
            author = el.get("content", "") or el.get_text(strip=True)
            if author:
                break

    # Extract publish date
    pub_date = ""
    for selector in [
        'meta[property="article:published_time"]',
        'meta[name="date"]', 'meta[name="publish-date"]',
        '[itemprop="datePublished"]', "time"
    ]:
        el = soup.find(selector)
        if el:
            raw = el.get("content", "") or el.get("datetime", "") or el.get_text(strip=True)
            if raw:
                try:
                    from dateutil import parser as date_parser
                    pub_date = date_parser.parse(raw[:20]).strftime("%Y-%m-%d")
                except Exception:
                    pub_date = raw[:10]
                break

    # Extract main article text
    text = ""
    for selector in ["article", "main", ".content", ".post-content", ".entry-content"]:
        el = soup.find(selector)
        if el:
            text = el.get_text(separator="\n", strip=True)
            if len(text) > 200:
                break

    if not text:
        body = soup.find("body")
        if body:
            text = body.get_text(separator="\n", strip=True)

    # Extract description
    desc_el = soup.find("meta", attrs={"name": "description"}) or \
              soup.find("meta", attrs={"property": "og:description"})
    description = desc_el.get("content", "") if desc_el else ""

    return {
        "title": title,
        "author": author,
        "published_date": pub_date,
        "text": text,
        "description": description,
        "success": bool(text),
    }


def scrape_blog(url: str) -> Optional[dict]:
    """
    Scrape a single blog post URL.
    Returns structured data dict or None on failure.
    """
    logger.info(f"Scraping blog: {url}")

    # Try newspaper3k first
    data = _extract_with_newspaper(url)

    # Fall back to BeautifulSoup
    if not data["success"] or len(data.get("text", "")) < 100:
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            response = requests.get(url, headers=headers, timeout=20)
            response.raise_for_status()
            data = _extract_with_bs4(url, response.text)
        except Exception as e:
            logger.error(f"BS4 fallback also failed for {url}: {e}")
            return None

    if not data.get("success") and not data.get("text"):
        logger.warning(f"Could not extract content from {url}")
        return None

    # Infer region from domain TLD
    from urllib.parse import urlparse
    domain = urlparse(url).netloc
    region = _infer_region(domain)

    return {
        "source_url": url,
        "source_type": "blog",
        "title": data.get("title", ""),
        "author": data.get("author", "Unknown"),
        "published_date": data.get("published_date", ""),
        "description": data.get("description", ""),
        "text": data.get("text", ""),
        "domain": domain,
        "region": region,
    }


def scrape_all_blogs() -> list:
    """
    Scrape all pre-defined blog URLs.
    Returns list of scraped blog dicts.
    """
    results = []
    for url in BLOG_URLS:
        result = scrape_blog(url)
        if result:
            results.append(result)
        else:
            # Return placeholder with error flag for graceful degradation
            logger.warning(f"Failed to scrape blog: {url}")
            results.append({
                "source_url": url,
                "source_type": "blog",
                "title": "Scrape Failed",
                "author": "Unknown",
                "published_date": "",
                "description": "",
                "text": "",
                "domain": url.split("/")[2] if "//" in url else url,
                "region": "Unknown",
                "error": "Scraping failed"
            })
    return results


def _infer_region(domain: str) -> str:
    """
    Infer geographic region from the domain TLD.
    """
    tld_region_map = {
        ".uk": "United Kingdom",
        ".co.uk": "United Kingdom",
        ".au": "Australia",
        ".ca": "Canada",
        ".de": "Germany",
        ".fr": "France",
        ".in": "India",
        ".jp": "Japan",
        ".cn": "China",
        ".br": "Brazil",
        ".eu": "Europe",
        ".int": "International",
        ".org": "International",
        ".gov": "United States",
        ".edu": "United States",
        ".com": "United States",
        ".net": "International",
    }

    domain_lower = domain.lower()
    for tld, region in sorted(tld_region_map.items(), key=lambda x: -len(x[0])):
        if domain_lower.endswith(tld):
            return region

    return "Unknown"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    blogs = scrape_all_blogs()
    for b in blogs:
        print(f"\n--- {b['source_url']} ---")
        print(f"Title: {b['title']}")
        print(f"Author: {b['author']}")
        print(f"Date: {b['published_date']}")
        print(f"Text preview: {b['text'][:200]}...")
