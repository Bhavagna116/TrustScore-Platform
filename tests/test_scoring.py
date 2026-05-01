"""
test_scoring.py
---------------
Unit tests for the scoring layer.
Tests each component scorer and the combined trust score formula.
"""

import pytest


class TestDomainChecker:
    def test_high_authority_edu(self):
        from scoring.domain_checker import get_domain_authority
        score, expl = get_domain_authority("https://mit.edu/research")
        assert score >= 0.85

    def test_high_authority_gov(self):
        from scoring.domain_checker import get_domain_authority
        score, _ = get_domain_authority("https://cdc.gov/report")
        assert score >= 0.85

    def test_known_high_domain(self):
        from scoring.domain_checker import get_domain_authority
        score, _ = get_domain_authority("https://nature.com/articles/test")
        assert score >= 0.90

    def test_known_medium_domain(self):
        from scoring.domain_checker import get_domain_authority
        score, _ = get_domain_authority("https://medium.com/post")
        assert 0.50 <= score <= 0.80

    def test_low_tld(self):
        from scoring.domain_checker import get_domain_authority
        score, _ = get_domain_authority("http://spam-site.xyz/article")
        assert score < 0.50

    def test_score_in_range(self):
        from scoring.domain_checker import get_domain_authority
        for url in ["https://example.com", "https://bbc.co.uk", "http://test.info"]:
            score, _ = get_domain_authority(url)
            assert 0.0 <= score <= 1.0


class TestAbuseDetector:
    def test_recency_very_recent(self):
        from scoring.abuse_detector import score_recency
        score, _ = score_recency("2025-12-01")
        assert score >= 0.85

    def test_recency_old(self):
        from scoring.abuse_detector import score_recency
        score, _ = score_recency("2010-01-01")
        assert score <= 0.40

    def test_recency_empty(self):
        from scoring.abuse_detector import score_recency
        score, expl = score_recency("")
        assert 0.0 <= score <= 1.0
        assert "unknown" in expl.lower()

    def test_author_credibility_unknown(self):
        from scoring.abuse_detector import score_author_credibility
        score, _ = score_author_credibility("Unknown")
        assert score <= 0.40

    def test_author_credibility_named(self):
        from scoring.abuse_detector import score_author_credibility
        score, _ = score_author_credibility("Dr. John Smith")
        assert score >= 0.60

    def test_author_credibility_multiple(self):
        from scoring.abuse_detector import score_author_credibility
        score, _ = score_author_credibility("Alice Brown, Bob Chen, Carol Davis")
        assert score >= 0.60

    def test_citation_count_zero(self):
        from scoring.abuse_detector import score_citation_count
        score, _ = score_citation_count(0)
        assert score == 0.0

    def test_citation_count_high_pubmed(self):
        from scoring.abuse_detector import score_citation_count
        score, _ = score_citation_count(100, "pubmed")
        assert score == 1.0

    def test_spam_penalty_stuffed(self):
        from scoring.abuse_detector import calculate_spam_penalty
        # Create heavily stuffed text
        stuffed = ("buy cheap discount deals buy cheap discount deals " * 50)
        penalty = calculate_spam_penalty(stuffed)
        assert penalty > 0.0

    def test_spam_penalty_normal(self):
        from scoring.abuse_detector import calculate_spam_penalty
        normal = (
            "Machine learning is transforming healthcare by enabling more accurate "
            "diagnosis and personalized treatment plans for patients worldwide."
        )
        penalty = calculate_spam_penalty(normal)
        assert penalty < 0.3

    def test_misleading_claims(self):
        from scoring.abuse_detector import detect_misleading_claims
        text = "This miracle cure will cure cancer guaranteed 100%."
        has_misleading, patterns = detect_misleading_claims(text)
        assert has_misleading

    def test_no_misleading_claims(self):
        from scoring.abuse_detector import detect_misleading_claims
        text = "Researchers studied the effects of treatment on patient outcomes."
        has_misleading, _ = detect_misleading_claims(text)
        assert not has_misleading


class TestTrustScorer:
    def _make_source(self, **kwargs):
        base = {
            "source_url": "https://nature.com/articles/test",
            "source_type": "blog",
            "author": "Dr. Jane Smith",
            "published_date": "2024-06-01",
            "text": "Artificial intelligence is transforming healthcare research.",
        }
        base.update(kwargs)
        return base

    def test_score_in_range(self):
        from scoring.trust_scorer import calculate_trust_score
        result = calculate_trust_score(self._make_source())
        assert 0.0 <= result["trust_score"] <= 1.0

    def test_high_trust_authoritative(self):
        from scoring.trust_scorer import calculate_trust_score
        source = self._make_source(
            source_url="https://nature.com/article",
            author="Dr. John Smith, Dr. Alice Wang",
            published_date="2024-01-01",
        )
        result = calculate_trust_score(source)
        assert result["trust_score"] >= 0.45

    def test_score_breakdown_keys(self):
        from scoring.trust_scorer import calculate_trust_score
        result = calculate_trust_score(self._make_source())
        breakdown = result["score_breakdown"]
        for key in ["author_credibility", "citation_count", "domain_authority",
                    "recency", "medical_disclaimer"]:
            assert key in breakdown

    def test_score_source_enrichment(self):
        from scoring.trust_scorer import score_source
        source = self._make_source()
        result = score_source(source)
        assert "trust_score" in result
        assert "score_breakdown" in result
        assert "explanation" in result

    def test_medical_disclaimer_boost(self):
        from scoring.trust_scorer import calculate_trust_score
        with_disclaimer = self._make_source(
            text="This is not medical advice. Consult your doctor. AI research content."
        )
        without_disclaimer = self._make_source(
            text="AI research content without any medical guidance information."
        )
        score_with = calculate_trust_score(with_disclaimer)["trust_score"]
        score_without = calculate_trust_score(without_disclaimer)["trust_score"]
        assert score_with >= score_without
