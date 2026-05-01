"""
cleaner.py
----------
Text cleaning utilities for scraped content.
Removes HTML artifacts, normalizes whitespace, deduplicates sentences,
and handles encoding issues.
"""

import re
import html
import unicodedata
from typing import Optional


def clean_text(raw_text: str) -> str:
    """
    Main text cleaning pipeline.
    Steps: decode HTML entities → strip HTML tags → fix encoding →
           remove boilerplate → normalize whitespace → deduplicate sentences
    """
    if not raw_text:
        return ""

    text = raw_text

    # 1. Decode HTML entities (&amp; &lt; etc.)
    text = html.unescape(text)

    # 2. Strip any remaining HTML tags
    text = re.sub(r"<[^>]+>", " ", text)

    # 3. Normalize unicode (handle smart quotes, em-dashes, etc.)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")

    # 4. Remove URLs
    text = re.sub(r"https?://\S+|www\.\S+", "[URL]", text)

    # 5. Remove email addresses
    text = re.sub(r"\S+@\S+\.\S+", "[EMAIL]", text)

    # 6. Remove excessive punctuation (e.g. !!!!!  .....)
    text = re.sub(r"([!?.]){3,}", r"\1\1", text)

    # 7. Remove common boilerplate patterns
    boilerplate_patterns = [
        r"(subscribe|click here|read more|sign up|cookie policy|privacy policy"
        r"|all rights reserved|copyright \d{4}|terms of service|follow us on"
        r"|share this|advertisement|sponsored content|related articles)",
    ]
    for pattern in boilerplate_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # 8. Collapse multiple newlines to double newline (paragraph breaks)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 9. Collapse multiple spaces
    text = re.sub(r" {2,}", " ", text)

    # 10. Strip leading/trailing whitespace per line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(line for line in lines if line)

    # 11. Deduplicate consecutive identical sentences
    text = _deduplicate_sentences(text)

    return text.strip()


def _deduplicate_sentences(text: str) -> str:
    """
    Remove duplicate sentences that often appear in scraped content
    (e.g. from repeated nav elements or structured data leakage).
    """
    sentences = re.split(r"(?<=[.!?])\s+", text)
    seen = set()
    unique = []
    for sent in sentences:
        normalized = re.sub(r"\s+", " ", sent.strip().lower())
        if normalized and normalized not in seen and len(normalized) > 5:
            seen.add(normalized)
            unique.append(sent.strip())
    return " ".join(unique)


def clean_author(author: str) -> str:
    """
    Clean and normalize an author name string.
    Handles 'By Author Name', 'Author Name | Site' patterns.
    """
    if not author:
        return "Unknown"

    author = author.strip()

    # Remove 'By' prefix
    author = re.sub(r"^[Bb]y\s+", "", author)

    # Take only the part before | or @ or •
    author = re.split(r"[|@•]", author)[0].strip()

    # Remove extra whitespace
    author = re.sub(r"\s+", " ", author)

    # If resulting name is too short or too long, mark as unknown
    if len(author) < 2 or len(author) > 100:
        return "Unknown"

    return author


def clean_date(raw_date: str) -> str:
    """
    Normalize date strings to YYYY-MM-DD format.
    Returns empty string if parsing fails.
    """
    if not raw_date:
        return ""

    raw_date = raw_date.strip()

    try:
        from dateutil import parser as date_parser
        dt = date_parser.parse(raw_date, fuzzy=True)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        # Try to extract year at minimum
        year_match = re.search(r"\b(19|20)\d{2}\b", raw_date)
        if year_match:
            return f"{year_match.group()}-01-01"
        return ""


def extract_references(text: str) -> int:
    """
    Count the number of references/citations in the text.
    Looks for common citation patterns: [1], (Smith, 2020), etc.
    """
    patterns = [
        r"\[\d+\]",                          # [1], [23]
        r"\(\w+,?\s+\d{4}\)",               # (Smith, 2020)
        r"\d+\.\s+\w+.*?\d{4}",            # Numbered reference list
        r"https?://(?:doi\.org|dx\.doi\.org)/\S+",  # DOI links
    ]
    total = 0
    for pattern in patterns:
        total += len(re.findall(pattern, text))
    return total


def detect_medical_disclaimer(text: str) -> bool:
    """
    Check if the content contains medical disclaimer language.
    Returns True if disclaimer found (boosts trust for health content).
    """
    disclaimer_patterns = [
        r"this (article|content|information) is not (intended as |a substitute for )?medical advice",
        r"consult (your|a) (doctor|physician|healthcare provider|medical professional)",
        r"not intended to (diagnose|treat|cure|prevent)",
        r"for informational purposes only",
        r"seek (professional |medical )?advice",
        r"this is not medical advice",
        r"speak with (your|a) doctor",
    ]
    text_lower = text.lower()
    for pattern in disclaimer_patterns:
        if re.search(pattern, text_lower):
            return True
    return False


def detect_keyword_stuffing(text: str) -> float:
    """
    Detect SEO keyword stuffing.
    Returns a penalty score (0.0 = no stuffing, 1.0 = heavy stuffing).
    """
    if not text or len(text) < 100:
        return 0.0

    words = re.findall(r"\b[a-z]{3,}\b", text.lower())
    if len(words) < 50:
        return 0.0

    from collections import Counter
    word_freq = Counter(words)
    total_words = len(words)

    # Calculate max keyword density
    top_count = word_freq.most_common(1)[0][1]
    density = top_count / total_words

    # Common English stop words (not keyword stuffing)
    stop_words = {
        "the", "and", "for", "are", "was", "were", "that", "this",
        "with", "from", "have", "has", "had", "been", "will", "can",
        "not", "but", "you", "they", "their", "there", "here", "when",
        "which", "than", "then", "its", "our", "your", "all", "also",
    }

    # Check top keywords excluding stop words
    for word, count in word_freq.most_common(10):
        if word not in stop_words:
            density = count / total_words
            if density > 0.05:  # >5% density = potential stuffing
                return min((density - 0.05) * 5, 1.0)

    return 0.0
