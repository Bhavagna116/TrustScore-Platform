"""
tagger.py
---------
Automatic topic tagging using RAKE (primary) and TF-IDF (supplementary).
Extracts meaningful, concise keyword tags from text content.
"""

import re
import logging
import math
from typing import List
from collections import Counter

logger = logging.getLogger(__name__)

MAX_TAGS = 8
MIN_TAG_LENGTH = 3
MAX_TAG_WORDS = 4  # Max words per tag phrase


def _clean_tag(tag: str) -> str:
    """Clean and normalize a tag string."""
    # Remove special characters
    tag = re.sub(r"[^a-zA-Z0-9\s-]", "", tag)
    tag = re.sub(r"\s+", " ", tag).strip().lower()
    return tag


def _is_valid_tag(tag: str) -> bool:
    """Check if a tag is meaningful and not a stop word."""
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
        "been", "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "must", "shall", "can",
        "not", "no", "nor", "so", "yet", "both", "either", "neither", "if",
        "then", "else", "when", "where", "while", "although", "though",
        "because", "since", "until", "unless", "after", "before", "that",
        "this", "these", "those", "it", "its", "they", "them", "their",
        "we", "our", "you", "your", "he", "she", "his", "her", "who", "what",
        "which", "how", "why", "more", "most", "some", "any", "all", "each",
        "also", "just", "only", "very", "much", "many", "such", "new", "use",
    }

    if not tag or len(tag) < MIN_TAG_LENGTH:
        return False

    tag_words = tag.split()
    if len(tag_words) > MAX_TAG_WORDS:
        return False

    # Single-word tags must not be a stop word
    if len(tag_words) == 1 and tag in stop_words:
        return False

    # Reject purely numeric tags
    if tag.replace(" ", "").isdigit():
        return False

    return True


def extract_tags_rake(text: str, max_tags: int = MAX_TAGS) -> List[str]:
    """
    Extract topic tags using RAKE (Rapid Automatic Keyword Extraction).
    RAKE scores multi-word phrases by word co-occurrence and frequency.
    """
    try:
        from rake_nltk import Rake
        import nltk
        import os

        nltk_data_dir = '/tmp/nltk_data'
        if os.environ.get("VERCEL"):
            if not os.path.exists(nltk_data_dir):
                os.makedirs(nltk_data_dir, exist_ok=True)
            nltk.data.path.append(nltk_data_dir)
        else:
            nltk_data_dir = None # Default path

        # Download required NLTK data silently
        try:
            nltk.data.find("tokenizers/punkt")
        except LookupError:
            nltk.download("punkt", quiet=True, download_dir=nltk_data_dir)
        try:
            nltk.data.find("corpora/stopwords")
        except LookupError:
            nltk.download("stopwords", quiet=True, download_dir=nltk_data_dir)
        try:
            nltk.data.find("tokenizers/punkt_tab")
        except LookupError:
            nltk.download("punkt_tab", quiet=True, download_dir=nltk_data_dir)

        # Use first 5000 chars for efficiency
        sample = text[:5000] if len(text) > 5000 else text

        rake = Rake(
            min_length=1,
            max_length=MAX_TAG_WORDS,
            include_repeated_phrases=False,
        )
        rake.extract_keywords_from_text(sample)

        # Get ranked phrases (highest score first)
        ranked = rake.get_ranked_phrases()

        tags = []
        for phrase in ranked:
            cleaned = _clean_tag(phrase)
            if _is_valid_tag(cleaned) and cleaned not in tags:
                tags.append(cleaned)
            if len(tags) >= max_tags:
                break

        return tags

    except Exception as e:
        logger.warning(f"RAKE tagging failed: {e}")
        return []


def extract_tags_tfidf(text: str, max_tags: int = MAX_TAGS) -> List[str]:
    """
    Extract tags using TF-IDF scoring (fallback method).
    Ranks words by term frequency × inverse document frequency
    using the document itself as a proxy corpus.
    """
    if not text:
        return []

    # Tokenize
    words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())

    if len(words) < 10:
        return []

    # Calculate term frequency
    total_words = len(words)
    word_freq = Counter(words)

    # Stop words to exclude
    stop_words = {
        "the", "and", "for", "are", "was", "were", "that", "this", "with",
        "from", "have", "has", "had", "been", "will", "can", "not", "but",
        "you", "they", "their", "there", "here", "when", "which", "than",
        "then", "its", "our", "your", "all", "also", "just", "more", "some",
        "any", "each", "such", "use", "used", "using", "make", "makes",
        "made", "said", "says", "like", "well", "would", "could", "should",
        "may", "might", "must", "about", "into", "over", "after", "before",
        "between", "through", "during", "very", "much", "most", "many",
        "how", "what", "who", "where", "why", "when", "one", "two", "new",
        "get", "got", "give", "given", "take", "taken", "know", "known",
    }

    # Score each word by TF-IDF approximation
    # Since we have one document, IDF approximated by log(1/TF)
    scored = []
    for word, freq in word_freq.items():
        if word in stop_words or len(word) < 3:
            continue
        tf = freq / total_words
        # Inverse frequency weighting (rare = more informative)
        idf = math.log(1 + (1 / tf))
        score = tf * idf
        scored.append((word, score))

    scored.sort(key=lambda x: -x[1])

    tags = [word for word, _ in scored[:max_tags]]
    return tags


def extract_tags(text: str, max_tags: int = MAX_TAGS) -> List[str]:
    """
    Main tag extraction function.
    Tries RAKE first, supplements with TF-IDF if needed.
    """
    if not text or len(text.strip()) < 50:
        return []

    # Try RAKE first
    tags = extract_tags_rake(text, max_tags=max_tags)

    # If RAKE produced too few tags, supplement with TF-IDF
    if len(tags) < 3:
        logger.info("Supplementing with TF-IDF tags")
        tfidf_tags = extract_tags_tfidf(text, max_tags=max_tags)

        for tag in tfidf_tags:
            if tag not in tags and _is_valid_tag(tag):
                tags.append(tag)
            if len(tags) >= max_tags:
                break

    # Final validation pass
    tags = [t for t in tags if _is_valid_tag(t)]

    return tags[:max_tags]


if __name__ == "__main__":
    sample_text = """
    Machine learning and artificial intelligence are revolutionizing healthcare diagnostics.
    Deep learning models trained on medical imaging datasets can detect tumors and anomalies
    with high accuracy. Natural language processing enables automated extraction of clinical
    insights from electronic health records. Transfer learning techniques allow models to
    generalize across different medical domains with limited labeled data. The integration
    of AI in clinical workflows is accelerating drug discovery and personalized medicine.
    """

    tags = extract_tags(sample_text)
    print("Extracted tags:", tags)
