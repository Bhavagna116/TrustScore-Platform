"""
language_detector.py
--------------------
Detects language and infers geographic region from content.
Uses langdetect library with confidence scoring.
"""

import logging
import re
from typing import Tuple

logger = logging.getLogger(__name__)

# Language code to full name mapping
LANGUAGE_NAMES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "nl": "Dutch",
    "pl": "Polish",
    "ru": "Russian",
    "ja": "Japanese",
    "zh-cn": "Chinese (Simplified)",
    "zh-tw": "Chinese (Traditional)",
    "ko": "Korean",
    "ar": "Arabic",
    "hi": "Hindi",
    "bn": "Bengali",
    "tr": "Turkish",
    "sv": "Swedish",
    "no": "Norwegian",
    "da": "Danish",
    "fi": "Finnish",
    "ro": "Romanian",
    "cs": "Czech",
    "sk": "Slovak",
    "hu": "Hungarian",
    "el": "Greek",
    "he": "Hebrew",
    "th": "Thai",
    "vi": "Vietnamese",
    "id": "Indonesian",
    "ms": "Malay",
    "uk": "Ukrainian",
    "ca": "Catalan",
    "af": "Afrikaans",
}

# Language code to likely region mapping
LANGUAGE_REGION_MAP = {
    "en": "United States",
    "es": "Spain/Latin America",
    "fr": "France",
    "de": "Germany",
    "it": "Italy",
    "pt": "Brazil/Portugal",
    "nl": "Netherlands",
    "pl": "Poland",
    "ru": "Russia",
    "ja": "Japan",
    "zh-cn": "China",
    "zh-tw": "Taiwan",
    "ko": "South Korea",
    "ar": "Middle East",
    "hi": "India",
    "bn": "Bangladesh/India",
    "tr": "Turkey",
    "sv": "Sweden",
    "no": "Norway",
    "da": "Denmark",
}


def detect_language(text: str) -> Tuple[str, str]:
    """
    Detect the language of the given text.
    Returns (language_code, language_name).
    Defaults to ('en', 'English') on failure.
    """
    if not text or len(text.strip()) < 20:
        return "en", "English"

    # Use first 1000 chars for efficiency
    sample = text[:1000].strip()

    try:
        from langdetect import detect, detect_langs, LangDetectException

        # Get probability distribution
        probabilities = detect_langs(sample)

        if not probabilities:
            return "en", "English"

        # Use highest confidence language
        best = probabilities[0]
        lang_code = best.lang
        confidence = best.prob

        logger.debug(f"Language detected: {lang_code} (confidence: {confidence:.2f})")

        # Low confidence → fall back to English
        if confidence < 0.5:
            logger.warning(f"Low confidence ({confidence:.2f}) for language detection, defaulting to English")
            return "en", "English"

        lang_name = LANGUAGE_NAMES.get(lang_code, lang_code.upper())
        return lang_code, lang_name

    except Exception as e:
        logger.warning(f"Language detection failed: {e}")
        return "en", "English"


def infer_region_from_domain(domain: str) -> str:
    """
    Infer geographic region from domain TLD.
    """
    tld_map = {
        ".co.uk": "United Kingdom",
        ".co.au": "Australia",
        ".co.nz": "New Zealand",
        ".co.in": "India",
        ".co.jp": "Japan",
        ".co.kr": "South Korea",
        ".co.za": "South Africa",
        ".co.br": "Brazil",
        ".com.au": "Australia",
        ".com.br": "Brazil",
        ".com.mx": "Mexico",
        ".uk": "United Kingdom",
        ".au": "Australia",
        ".ca": "Canada",
        ".de": "Germany",
        ".fr": "France",
        ".in": "India",
        ".jp": "Japan",
        ".cn": "China",
        ".br": "Brazil",
        ".es": "Spain",
        ".it": "Italy",
        ".nl": "Netherlands",
        ".pl": "Poland",
        ".ru": "Russia",
        ".kr": "South Korea",
        ".mx": "Mexico",
        ".se": "Sweden",
        ".no": "Norway",
        ".dk": "Denmark",
        ".fi": "Finland",
        ".eu": "Europe",
        ".int": "International",
        ".gov": "United States",
        ".edu": "United States",
        ".com": "United States",
        ".net": "International",
        ".org": "International",
    }

    domain_lower = domain.lower()
    # Sort by length descending to match most specific TLD first
    for tld, region in sorted(tld_map.items(), key=lambda x: -len(x[0])):
        if domain_lower.endswith(tld):
            return region

    return "Unknown"


def detect_language_and_region(text: str, domain: str = "") -> dict:
    """
    Combined language and region detection.
    Returns dict with language_code, language, and region.
    """
    lang_code, lang_name = detect_language(text)

    # Region: prefer domain-based inference, fall back to language-based
    region = ""
    if domain:
        region = infer_region_from_domain(domain)

    if not region or region == "Unknown":
        region = LANGUAGE_REGION_MAP.get(lang_code, "Unknown")

    return {
        "language_code": lang_code,
        "language": lang_name,
        "region": region,
    }
