"""
domain_checker.py
-----------------
Domain authority scoring using heuristics.
Assigns credibility scores based on domain TLD, known high-trust domains,
HTTPS usage, and domain age proxies.
"""

import re
from urllib.parse import urlparse
from typing import Tuple


# Known high-authority domains → score 0.9–1.0
HIGH_AUTHORITY_DOMAINS = {
    # Government & International Organizations
    "who.int", "cdc.gov", "nih.gov", "fda.gov", "ncbi.nlm.nih.gov",
    "pubmed.ncbi.nlm.nih.gov", "europa.eu", "un.org", "worldbank.org",
    "imf.org", "nato.int", "oecd.org",

    # Academic & Research
    "nature.com", "science.org", "cell.com", "thelancet.com",
    "nejm.org", "bmj.com", "jamanetwork.com", "springer.com",
    "wiley.com", "elsevier.com", "arxiv.org", "ssrn.com",
    "jstor.org", "pubmedcentral.nih.gov", "plos.org",
    "royalsocietypublishing.org", "cambridge.org", "oxford.com",
    "mitpress.mit.edu", "hbr.org",

    # Reputable News
    "bbc.com", "bbc.co.uk", "reuters.com", "apnews.com",
    "nytimes.com", "washingtonpost.com", "theguardian.com",
    "economist.com", "ft.com", "wsj.com", "bloomberg.com",
    "npr.org", "pbs.org",

    # Tech & Science Media
    "scientificamerican.com", "newscientist.com", "technologyreview.com",
    "wired.com", "arstechnica.com", "spectrum.ieee.org",

    # Medical
    "mayoclinic.org", "clevelandclinic.org", "hopkinsmedicine.org",
    "webmd.com", "healthline.com", "medicalnewstoday.com",
}

# Medium-authority domains → score 0.5–0.75
MEDIUM_AUTHORITY_DOMAINS = {
    "medium.com", "towardsdatascience.com", "hackernoon.com",
    "techcrunch.com", "theverge.com", "engadget.com", "cnet.com",
    "zdnet.com", "pcmag.com", "venturebeat.com", "forbes.com",
    "businessinsider.com", "inc.com", "entrepreneur.com",
    "psychologytoday.com", "verywell.com", "everydayhealth.com",
    "youtube.com", "linkedin.com",
}

# Low-authority or spam-prone domains
LOW_AUTHORITY_PATTERNS = [
    r"wordpress\.com$",
    r"blogspot\.com$",
    r"tumblr\.com$",
    r"weebly\.com$",
    r"wixsite\.com$",
    r"freewebsitehosting\.",
    r"tripod\.com$",
    r"angelfire\.com$",
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",  # Raw IP addresses
]

# TLD authority scores
TLD_SCORES = {
    ".gov": 0.95,
    ".edu": 0.90,
    ".int": 0.90,
    ".mil": 0.85,
    ".ac.uk": 0.85,
    ".org": 0.65,
    ".co.uk": 0.60,
    ".net": 0.55,
    ".com": 0.50,
    ".io": 0.50,
    ".co": 0.45,
    ".info": 0.35,
    ".biz": 0.30,
    ".xyz": 0.20,
    ".tk": 0.10,
    ".click": 0.10,
    ".top": 0.15,
}


def get_domain_authority(url: str) -> Tuple[float, str]:
    """
    Calculate domain authority score (0.0–1.0) for a URL.
    Returns (score, explanation).
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        scheme = parsed.scheme.lower()

        # Remove www. prefix for matching
        domain_clean = re.sub(r"^www\.", "", domain)

        # ── Check HTTPS ──────────────────────────────────────────────────────
        https_bonus = 0.05 if scheme == "https" else 0.0

        # ── Check high-authority domains ─────────────────────────────────────
        if domain_clean in HIGH_AUTHORITY_DOMAINS:
            score = min(0.95 + https_bonus, 1.0)
            return score, f"Known high-authority domain ({domain_clean})"

        # ── Check if subdomain of high-authority domain ──────────────────────
        for high_domain in HIGH_AUTHORITY_DOMAINS:
            if domain_clean.endswith("." + high_domain):
                score = min(0.85 + https_bonus, 1.0)
                return score, f"Subdomain of high-authority domain ({high_domain})"

        # ── Check medium-authority domains ───────────────────────────────────
        if domain_clean in MEDIUM_AUTHORITY_DOMAINS:
            score = min(0.60 + https_bonus, 1.0)
            return score, f"Known medium-authority domain ({domain_clean})"

        # ── Check low-authority patterns ─────────────────────────────────────
        for pattern in LOW_AUTHORITY_PATTERNS:
            if re.search(pattern, domain_clean):
                score = max(0.20 + https_bonus, 0.0)
                return score, f"Low-authority hosting platform detected"

        # ── Score by TLD ─────────────────────────────────────────────────────
        tld_score = 0.40  # Default
        matched_tld = ".com"
        for tld, s in sorted(TLD_SCORES.items(), key=lambda x: -len(x[0])):
            if domain_clean.endswith(tld):
                tld_score = s
                matched_tld = tld
                break

        score = min(tld_score + https_bonus, 1.0)
        return score, f"Domain scored by TLD ({matched_tld})"

    except Exception:
        return 0.3, "Could not parse domain"


def is_https(url: str) -> bool:
    """Check if URL uses HTTPS."""
    return url.lower().startswith("https://")


def get_domain_from_url(url: str) -> str:
    """Extract clean domain from URL."""
    try:
        parsed = urlparse(url)
        return re.sub(r"^www\.", "", parsed.netloc.lower())
    except Exception:
        return url
