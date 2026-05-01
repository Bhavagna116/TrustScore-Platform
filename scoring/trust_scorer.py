"""
trust_scorer.py
---------------
Main trust scoring engine.
Calculates a weighted trust score (0.0-1.0) for each scraped source
with full explainability (XAI) of each component.

Trust Score = 0.25 * author_credibility
            + 0.20 * citation_count_normalized
            + 0.25 * domain_authority
            + 0.20 * recency
            + 0.10 * medical_disclaimer_presence
            - spam_penalty (up to -0.3)
"""

import logging
logger = logging.getLogger(__name__)

WEIGHTS = {
    "author_credibility":  0.25,
    "citation_count":      0.20,
    "domain_authority":    0.25,
    "recency":             0.20,
    "medical_disclaimer":  0.10,
}
MAX_SPAM_PENALTY = 0.30


def calculate_trust_score(source: dict) -> dict:
    """
    Calculate complete trust score for a source dict.
    Returns dict with trust_score, score_breakdown, explanation.
    """
    from scoring.domain_checker import get_domain_authority
    from scoring.abuse_detector import (
        score_author_credibility, score_recency,
        score_citation_count, calculate_spam_penalty,
    )
    from processing.cleaner import detect_medical_disclaimer, extract_references

    source_type = source.get("source_type", "blog")
    url = source.get("source_url", "")
    author = source.get("author", "Unknown")
    pub_date = source.get("published_date", "")
    text = source.get("text", "")
    citation_count_raw = source.get("citation_count", None)

    # 1. Author Credibility
    author_score, author_expl = score_author_credibility(author, text)

    # 2. Citation Count
    ref_count = citation_count_raw if citation_count_raw is not None else extract_references(text)
    citation_score, citation_expl = score_citation_count(ref_count, source_type)

    # 3. Domain Authority
    domain_score, domain_expl = get_domain_authority(url)

    # 4. Recency
    recency_score, recency_expl = score_recency(pub_date)

    # 5. Medical Disclaimer
    has_disclaimer = detect_medical_disclaimer(text)
    disclaimer_score = 1.0 if has_disclaimer else 0.0
    disclaimer_expl = (
        "Medical disclaimer found" if has_disclaimer else "No medical disclaimer"
    )

    # Weighted sum
    raw_score = (
        WEIGHTS["author_credibility"]  * author_score +
        WEIGHTS["citation_count"]      * citation_score +
        WEIGHTS["domain_authority"]    * domain_score +
        WEIGHTS["recency"]             * recency_score +
        WEIGHTS["medical_disclaimer"]  * disclaimer_score
    )

    # Spam penalty
    spam_penalty = min(calculate_spam_penalty(text) * MAX_SPAM_PENALTY, MAX_SPAM_PENALTY)
    final_score = round(max(0.0, min(raw_score - spam_penalty, 1.0)), 3)

    # XAI explanation
    verdict = (
        "HIGH TRUST" if final_score >= 0.80 else
        "MODERATE TRUST" if final_score >= 0.60 else
        "LOW-MODERATE TRUST" if final_score >= 0.40 else
        "LOW TRUST"
    )
    factors = {"domain authority": domain_score, "author credibility": author_score,
               "citation count": citation_score, "recency": recency_score}
    strong = [k for k, v in factors.items() if v >= 0.75]
    weak = [k for k, v in factors.items() if v < 0.40]
    parts = []
    if strong:
        parts.append(f"Strong factors: {', '.join(strong)}")
    if weak:
        parts.append(f"Weak factors: {', '.join(weak)}")
    if has_disclaimer:
        parts.append("medical disclaimer present")
    if spam_penalty > 0.1:
        parts.append(f"spam penalty: {spam_penalty:.2f}")
    explanation = f"{verdict} (score: {final_score:.2f}). " + ". ".join(parts) + "."

    return {
        "trust_score": final_score,
        "score_breakdown": {
            "author_credibility": round(author_score, 3),
            "citation_count": round(citation_score, 3),
            "domain_authority": round(domain_score, 3),
            "recency": round(recency_score, 3),
            "medical_disclaimer": round(disclaimer_score, 3),
        },
        "weights": WEIGHTS,
        "penalties": {"spam_penalty": round(spam_penalty, 3)},
        "component_explanations": {
            "author_credibility": author_expl,
            "citation_count": citation_expl,
            "domain_authority": domain_expl,
            "recency": recency_expl,
            "medical_disclaimer": disclaimer_expl,
        },
        "explanation": explanation,
        "reference_count": ref_count,
    }


def score_source(source: dict) -> dict:
    """Enrich a source dict with trust score data."""
    try:
        result = calculate_trust_score(source)
        return {**source, **result}
    except Exception as e:
        logger.error(f"Trust scoring failed for {source.get('source_url', '?')}: {e}")
        return {**source, "trust_score": 0.0, "score_breakdown": {}, "explanation": str(e)}
