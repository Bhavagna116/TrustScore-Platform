"""
pubmed_scraper.py
-----------------
Scrapes PubMed articles using the NCBI Entrez API via Biopython.
No API key required for low-volume access (<3 requests/sec).
Extracts: title, authors, journal, abstract, publication year.
"""

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

# ── Pre-defined PubMed article IDs ──────────────────────────────────────────
# Using specific PMIDs for reliable scraping
PUBMED_IDS = [
    "37638757",  # "Large language models in medicine" - Nature Medicine 2023
]

# NCBI Entrez configuration
ENTREZ_EMAIL = "research@example.com"  # Required by NCBI (use a real email in prod)
ENTREZ_TOOL = "TrustScoringPlatform"


def _setup_entrez():
    """Configure Biopython Entrez with email and tool name."""
    try:
        from Bio import Entrez
        Entrez.email = ENTREZ_EMAIL
        Entrez.tool = ENTREZ_TOOL
        return Entrez
    except ImportError:
        logger.error("Biopython not installed. Run: pip install biopython")
        raise


def _fetch_pubmed_article(pmid: str) -> Optional[dict]:
    """
    Fetch a PubMed article by PMID using Entrez efetch.
    Returns parsed article data or None on failure.
    """
    try:
        Entrez = _setup_entrez()

        # Rate limit: NCBI allows 3 requests/sec without API key
        time.sleep(0.4)

        # Fetch article in XML format for rich metadata
        handle = Entrez.efetch(
            db="pubmed",
            id=pmid,
            rettype="xml",
            retmode="xml"
        )
        records = Entrez.read(handle)
        handle.close()

        if not records or "PubmedArticle" not in records:
            logger.warning(f"No article found for PMID: {pmid}")
            return None

        article_data = records["PubmedArticle"][0]
        medline_citation = article_data.get("MedlineCitation", {})
        article = medline_citation.get("Article", {})

        # ── Extract Title ────────────────────────────────────────────────────
        title = str(article.get("ArticleTitle", ""))

        # ── Extract Authors ──────────────────────────────────────────────────
        authors = []
        author_list = article.get("AuthorList", [])
        for auth in author_list:
            last = str(auth.get("LastName", ""))
            fore = str(auth.get("ForeName", ""))
            collective = str(auth.get("CollectiveName", ""))
            if collective:
                authors.append(collective)
            elif last:
                name = f"{fore} {last}".strip()
                authors.append(name)

        # ── Extract Journal ──────────────────────────────────────────────────
        journal_info = article.get("Journal", {})
        journal_title = str(journal_info.get("Title", ""))

        # ── Extract Publication Date ─────────────────────────────────────────
        pub_date_info = journal_info.get("JournalIssue", {}).get("PubDate", {})
        year = str(pub_date_info.get("Year", ""))
        month = str(pub_date_info.get("Month", "01"))
        day = str(pub_date_info.get("Day", "01"))

        # Normalize month name to number
        month_map = {
            "jan": "01", "feb": "02", "mar": "03", "apr": "04",
            "may": "05", "jun": "06", "jul": "07", "aug": "08",
            "sep": "09", "oct": "10", "nov": "11", "dec": "12"
        }
        month_lower = month.lower()[:3]
        month = month_map.get(month_lower, month.zfill(2))

        pub_date = f"{year}-{month}-{day.zfill(2)}" if year else ""

        # ── Extract Abstract ─────────────────────────────────────────────────
        abstract_text = ""
        abstract_data = article.get("Abstract", {})
        if abstract_data:
            abstract_texts = abstract_data.get("AbstractText", [])
            if isinstance(abstract_texts, list):
                parts = []
                for part in abstract_texts:
                    label = str(part.attributes.get("Label", "")) if hasattr(part, "attributes") else ""
                    text = str(part)
                    if label:
                        parts.append(f"{label}: {text}")
                    else:
                        parts.append(text)
                abstract_text = "\n\n".join(parts)
            else:
                abstract_text = str(abstract_texts)

        # ── Extract Keywords ─────────────────────────────────────────────────
        keywords = []
        keyword_list = medline_citation.get("KeywordList", [])
        for kw_group in keyword_list:
            for kw in kw_group:
                keywords.append(str(kw))

        # ── Extract MeSH Terms ───────────────────────────────────────────────
        mesh_terms = []
        mesh_heading_list = medline_citation.get("MeshHeadingList", [])
        for mesh in mesh_heading_list:
            descriptor = mesh.get("DescriptorName", "")
            if descriptor:
                mesh_terms.append(str(descriptor))

        # ── Extract Citation Count (via Entrez elink) ────────────────────────
        citation_count = _get_citation_count(pmid, Entrez)

        # ── Build result ─────────────────────────────────────────────────────
        pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

        return {
            "source_url": pubmed_url,
            "source_type": "pubmed",
            "pmid": pmid,
            "title": title,
            "author": ", ".join(authors) if authors else "Unknown",
            "authors_list": authors,
            "published_date": pub_date,
            "journal": journal_title,
            "abstract": abstract_text,
            "text": abstract_text,  # PubMed content is the abstract
            "keywords": keywords,
            "mesh_terms": mesh_terms,
            "citation_count": citation_count,
            "domain": "pubmed.ncbi.nlm.nih.gov",
            "region": "United States",
        }

    except Exception as e:
        logger.error(f"Failed to fetch PubMed article {pmid}: {e}")
        return None


def _get_citation_count(pmid: str, Entrez) -> int:
    """
    Attempt to get citation count via Entrez elink (PubMed Central).
    Returns 0 on failure (graceful degradation).
    """
    try:
        time.sleep(0.4)
        handle = Entrez.elink(dbfrom="pubmed", db="pmc", id=pmid, linkname="pubmed_pmc_refs")
        result = Entrez.read(handle)
        handle.close()

        if result and result[0].get("LinkSetDb"):
            links = result[0]["LinkSetDb"][0].get("Link", [])
            return len(links)
        return 0
    except Exception:
        return 0  # Non-critical; return 0 on any failure


def scrape_all_pubmed() -> list:
    """
    Scrape all pre-defined PubMed article IDs.
    Returns list of scraped article dicts.
    """
    results = []
    for pmid in PUBMED_IDS:
        result = _fetch_pubmed_article(pmid)
        if result:
            results.append(result)
        else:
            logger.warning(f"Failed to scrape PubMed article: PMID {pmid}")
            results.append({
                "source_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "source_type": "pubmed",
                "pmid": pmid,
                "title": f"PubMed Article PMID:{pmid}",
                "author": "Unknown",
                "authors_list": [],
                "published_date": "",
                "journal": "",
                "abstract": "",
                "text": "",
                "keywords": [],
                "mesh_terms": [],
                "citation_count": 0,
                "domain": "pubmed.ncbi.nlm.nih.gov",
                "region": "United States",
                "error": "Scraping failed"
            })
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    articles = scrape_all_pubmed()
    for a in articles:
        print(f"\n--- PMID: {a.get('pmid')} ---")
        print(f"Title: {a['title']}")
        print(f"Authors: {a['author']}")
        print(f"Journal: {a.get('journal')}")
        print(f"Date: {a['published_date']}")
        print(f"Citations: {a.get('citation_count', 0)}")
        print(f"Abstract preview: {a['text'][:300]}...")
