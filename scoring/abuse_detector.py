"""
abuse_detector.py
-----------------
Detects content quality issues that reduce trust score.
Checks: keyword stuffing, fake author patterns, outdated content,
misleading medical claims, and SEO spam signals.
"""

import re
import logging
from datetime import datetime, date
from typing import Tuple, List
from collections import Counter

logger = logging.getLogger(__name__)

# Misleading health/medical claim patterns
MISLEADING_MEDICAL_PATTERNS = [
    r"(cure|cures|cured|curing)\s+(cancer|diabetes|hiv|aids|covid|autism)",
    r"(doctors|big pharma|government)\s+(don'?t|doesn'?t|won'?t|refuse to)\s+want you to know",
    r"100%\s+(guaranteed|proven|effective|safe|natural)",
    r"(miracle|magic|secret)\s+(cure|remedy|treatment|formula)",
    r"(detox|cleanse)\s+your\s+(liver|body|kidney|colon)",
    r"big pharma\s+(conspiracy|hiding|suppressing)",
    r"(essential oils|crystals|homeopathy)\s+(treat|cure|heal)",
    r"vaccines?\s+(cause|causes|causing)\s+(autism|cancer|death)",
    r"(alkaline|acidic)\s+(water|diet)\s+(cure|treat|heal)",
]

# Fake author name patterns (gibberish, single letters, numbers)
FAKE_AUTHOR_PATTERNS = [
    r"^[A-Z]{1}$",                          # Single letter
    r"^\d+$",                               # Pure numbers
    r"^[a-z0-9]{8,}@",                     # Looks like email handle
    r"^(admin|user|author|editor|staff|webmaster|anonymous|anon)$",  # Generic names
    r"^[^a-zA-Z]*$",                        # No letters
    r"[<>{}\\[\]|]",                        # Suspicious characters
]

# Reputable author institution patterns (boost credibility)
CREDIBLE_INSTITUTION_PATTERNS = [
    r"\b(md|phd|dr\.?|professor|prof\.?|researcher|scientist)\b",
    r"\b(university|college|institute|hospital|clinic|center)\b",
    r"\b(harvard|stanford|mit|oxford|cambridge|johns hopkins)\b",
    r"\b(cdc|nih|who|fda|mayo clinic|cleveland clinic)\b",
    r"\b(journalist|reporter|correspondent|editor)\b",
]


def detect_keyword_stuffing(text: str) -> Tuple[float, str]:
    """
    Detect keyword stuffing (SEO spam).
    Returns (penalty_score, explanation) where higher penalty = more stuffing.
    """
    if not text or len(text) < 100:
        return 0.0, "Text too short to analyze"

    words = re.findall(r"\b[a-z]{3,}\b", text.lower())
    if len(words) < 30:
        return 0.0, "Too few words to detect stuffing"

    # Common English stop words (excluded from analysis)
    stop_words = {
        "the", "and", "for", "are", "was", "were", "that", "this", "with",
        "from", "have", "has", "had", "will", "can", "not", "but", "you",
        "they", "their", "also", "just", "more", "some", "any", "each",
        "use", "used", "make", "made", "said", "like", "well", "into",
        "over", "after", "before", "very", "much", "most", "many", "how",
        "what", "who", "where", "why", "when", "one", "two", "new", "get",
    }

    content_words = [w for w in words if w not in stop_words]
    if not content_words:
        return 0.0, "No content words found"

    total = len(content_words)
    freq = Counter(content_words)
    top_word, top_count = freq.most_common(1)[0]
    density = top_count / total

    if density > 0.08:
        penalty = min((density - 0.05) * 10, 1.0)
        return penalty, f"Keyword stuffing detected: '{top_word}' appears {top_count}x ({density:.1%} density)"
    elif density > 0.05:
        penalty = (density - 0.05) * 5
        return penalty, f"Mild repetition: '{top_word}' appears frequently ({density:.1%} density)"
    else:
        return 0.0, "No keyword stuffing detected"


def score_author_credibility(author: str, text: str = "") -> Tuple[float, str]:
    """
    Score author credibility (0.0–1.0).
    Returns (score, explanation).
    """
    if not author or author.strip().lower() in ["unknown", "n/a", "", "-"]:
        return 0.3, "No author information available"

    author_lower = author.strip().lower()

    # Check for fake author patterns
    for pattern in FAKE_AUTHOR_PATTERNS:
        if re.search(pattern, author_lower, re.IGNORECASE):
            return 0.1, f"Suspicious author name pattern detected"

    # Multiple authors → generally more credible (peer review)
    author_count = len([a.strip() for a in re.split(r"[,;]", author) if a.strip()])
    if author_count >= 3:
        multi_bonus = 0.1
    elif author_count == 2:
        multi_bonus = 0.05
    else:
        multi_bonus = 0.0

    # Check text for author credentials
    combined = f"{author} {text[:500]}".lower()
    credential_score = 0.0
    for pattern in CREDIBLE_INSTITUTION_PATTERNS:
        if re.search(pattern, combined, re.IGNORECASE):
            credential_score = 0.2
            break

    # Base score: named author = 0.5
    base_score = 0.5

    # Check if name looks like a real person (First Last pattern)
    if re.match(r"^[A-Z][a-z]+\s+[A-Z][a-z]+", author):
        base_score = 0.6

    total = min(base_score + credential_score + multi_bonus, 1.0)
    explanation = f"Author '{author[:30]}' scored {total:.2f}"
    return total, explanation


def score_recency(pub_date: str) -> Tuple[float, str]:
    """
    Score content recency (0.0–1.0).
    Very new content scores higher. Content > 5 years old penalized.
    Returns (score, explanation).
    """
    if not pub_date:
        return 0.4, "Publication date unknown (assumed moderate age)"

    try:
        from dateutil import parser as date_parser
        pub_dt = date_parser.parse(pub_date)
        today = datetime.now()

        # Calculate age in days
        age_days = (today - pub_dt).days

        if age_days < 0:
            # Future date (data error)
            return 0.5, "Invalid future publication date"
        elif age_days <= 90:   # ≤ 3 months
            score = 1.0
            label = "very recent (≤ 3 months)"
        elif age_days <= 365:  # ≤ 1 year
            score = 0.85
            label = "recent (< 1 year)"
        elif age_days <= 730:  # ≤ 2 years
            score = 0.70
            label = "moderately recent (1-2 years)"
        elif age_days <= 1825: # ≤ 5 years
            score = 0.55
            label = "aging (2-5 years)"
        elif age_days <= 3650: # ≤ 10 years
            score = 0.35
            label = "old (5-10 years)"
        else:
            score = 0.15
            label = "very old (> 10 years)"

        return score, f"Content is {label} (published {pub_date})"

    except Exception:
        return 0.4, f"Could not parse date: {pub_date}"


def score_citation_count(count: int, source_type: str = "blog") -> Tuple[float, str]:
    """
    Normalize citation count to 0.0–1.0 score.
    Different scales for different source types.
    """
    if count <= 0:
        return 0.0, "No citations found"

    # Different scales for different source types
    if source_type == "pubmed":
        # Academic articles can have hundreds of citations
        if count >= 100:
            score = 1.0
        elif count >= 50:
            score = 0.9
        elif count >= 20:
            score = 0.75
        elif count >= 10:
            score = 0.60
        elif count >= 5:
            score = 0.45
        else:
            score = 0.30
    else:
        # Blog/YouTube: count references/links in content
        if count >= 20:
            score = 1.0
        elif count >= 10:
            score = 0.80
        elif count >= 5:
            score = 0.60
        elif count >= 2:
            score = 0.40
        else:
            score = 0.25

    return score, f"{count} citation(s) found → score {score:.2f}"


def detect_misleading_claims(text: str) -> Tuple[bool, List[str]]:
    """
    Detect potentially misleading medical/health claims.
    Returns (has_misleading_content, list_of_detected_patterns).
    """
    if not text:
        return False, []

    text_lower = text.lower()
    detected = []

    for pattern in MISLEADING_MEDICAL_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            detected.append(match.group(0))

    return bool(detected), detected


def calculate_spam_penalty(text: str) -> float:
    """
    Calculate overall spam penalty (0.0 = no penalty, 1.0 = full penalty).
    Combines keyword stuffing, misleading claims, and other signals.
    """
    penalties = []

    # Keyword stuffing penalty
    stuffing_penalty, _ = detect_keyword_stuffing(text)
    penalties.append(stuffing_penalty * 0.5)

    # Misleading claims penalty
    has_misleading, _ = detect_misleading_claims(text)
    if has_misleading:
        penalties.append(0.3)

    # Excessive ALL CAPS
    caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
    if caps_ratio > 0.3:
        penalties.append(0.2)

    # Excessive exclamation marks
    excl_count = text.count("!")
    if excl_count > 10:
        penalties.append(min(excl_count / 50, 0.3))

    return min(sum(penalties), 0.8)  # Cap penalty at 0.8
