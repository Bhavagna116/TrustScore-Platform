"""
test_processing.py
------------------
Unit tests for the processing layer.
Tests: text cleaning, language detection, chunking, tagging.
"""

import pytest


class TestCleaner:
    def test_clean_html_tags(self):
        from processing.cleaner import clean_text
        result = clean_text("<h1>Hello</h1> <p>World</p>")
        assert "<h1>" not in result
        assert "Hello" in result

    def test_clean_html_entities(self):
        from processing.cleaner import clean_text
        result = clean_text("Hello &amp; World &lt;test&gt;")
        assert "&amp;" not in result
        assert "Hello" in result

    def test_clean_urls(self):
        from processing.cleaner import clean_text
        result = clean_text("Visit https://example.com for more info.")
        assert "https://example.com" not in result

    def test_deduplicate_sentences(self):
        from processing.cleaner import clean_text
        text = "AI is great. AI is great. Machine learning is important."
        result = clean_text(text)
        # Should not have exact duplicate sentence
        assert result.count("AI is great") <= 1

    def test_clean_author_by_prefix(self):
        from processing.cleaner import clean_author
        assert clean_author("By John Smith") == "John Smith"

    def test_clean_author_pipe(self):
        from processing.cleaner import clean_author
        result = clean_author("Jane Doe | The Guardian")
        assert result == "Jane Doe"

    def test_clean_author_empty(self):
        from processing.cleaner import clean_author
        assert clean_author("") == "Unknown"

    def test_clean_date_iso(self):
        from processing.cleaner import clean_date
        assert clean_date("2024-03-15") == "2024-03-15"

    def test_clean_date_human_readable(self):
        from processing.cleaner import clean_date
        result = clean_date("March 15, 2024")
        assert "2024" in result

    def test_clean_date_empty(self):
        from processing.cleaner import clean_date
        assert clean_date("") == ""

    def test_extract_references(self):
        from processing.cleaner import extract_references
        text = "See [1] and [2] for more. Also (Smith, 2020) showed this."
        count = extract_references(text)
        assert count >= 2

    def test_detect_medical_disclaimer(self):
        from processing.cleaner import detect_medical_disclaimer
        text = "This content is for informational purposes only. Consult your doctor."
        assert detect_medical_disclaimer(text) is True

    def test_no_medical_disclaimer(self):
        from processing.cleaner import detect_medical_disclaimer
        text = "Machine learning algorithms improve predictive accuracy significantly."
        assert detect_medical_disclaimer(text) is False

    def test_keyword_stuffing_detection(self):
        from processing.cleaner import detect_keyword_stuffing
        # Need >30 content words with high density to trigger the detector
        stuffed = ("buy cheap deals " * 40) + "some other words here"
        penalty = detect_keyword_stuffing(stuffed)
        assert penalty > 0.0

    def test_no_keyword_stuffing(self):
        from processing.cleaner import detect_keyword_stuffing
        normal = "Machine learning enables computers to learn from data automatically."
        penalty = detect_keyword_stuffing(normal)
        assert penalty < 0.3


class TestLanguageDetector:
    def test_detect_english(self):
        from processing.language_detector import detect_language
        code, name = detect_language("Machine learning is transforming artificial intelligence research.")
        assert code == "en"
        assert name == "English"

    def test_detect_short_text_default(self):
        from processing.language_detector import detect_language
        code, name = detect_language("Hi")
        assert code == "en"

    def test_infer_region_edu(self):
        from processing.language_detector import infer_region_from_domain
        assert infer_region_from_domain("mit.edu") == "United States"

    def test_infer_region_uk(self):
        from processing.language_detector import infer_region_from_domain
        assert infer_region_from_domain("bbc.co.uk") == "United Kingdom"

    def test_combined_detection(self):
        from processing.language_detector import detect_language_and_region
        result = detect_language_and_region(
            "Artificial intelligence research is growing rapidly.",
            "nature.com"
        )
        assert "language" in result
        assert "region" in result
        assert "language_code" in result


class TestChunker:
    def test_short_text_single_chunk(self):
        from processing.chunker import chunk_text
        text = "This is a short paragraph about machine learning."
        chunks = chunk_text(text)
        assert len(chunks) == 1

    def test_long_text_multiple_chunks(self):
        from processing.chunker import chunk_text
        # Create text with paragraph breaks and > 300 words each paragraph
        para = " ".join([f"word{i}" for i in range(350)])
        text = para + "\n\n" + para  # two long paragraphs
        chunks = chunk_text(text)
        assert len(chunks) >= 2

    def test_chunk_max_words(self):
        from processing.chunker import chunk_text, MAX_CHUNK_WORDS
        long_text = ". ".join([
            "This is a sentence about artificial intelligence and machine learning" * 3
        ] * 20)
        chunks = chunk_text(long_text)
        for chunk in chunks:
            assert len(chunk.split()) <= MAX_CHUNK_WORDS + 20  # small buffer for sentence boundary

    def test_empty_text(self):
        from processing.chunker import chunk_text
        assert chunk_text("") == []
        assert chunk_text("   ") == []

    def test_paragraph_splitting(self):
        from processing.chunker import chunk_text
        text = "First paragraph content here.\n\nSecond paragraph content here."
        chunks = chunk_text(text)
        assert len(chunks) >= 1


class TestTagger:
    def test_extract_tags_returns_list(self):
        from processing.tagger import extract_tags
        text = "Machine learning and artificial intelligence are transforming healthcare."
        tags = extract_tags(text)
        assert isinstance(tags, list)

    def test_extract_tags_not_empty(self):
        from processing.tagger import extract_tags
        text = (
            "Deep learning neural networks process large datasets to identify patterns "
            "in medical imaging for cancer detection and diagnosis."
        )
        tags = extract_tags(text)
        assert len(tags) > 0

    def test_extract_tags_max_count(self):
        from processing.tagger import extract_tags, MAX_TAGS
        text = " ".join([
            "artificial intelligence machine learning deep learning neural networks "
            "healthcare medicine drug discovery clinical trials data science"
        ] * 5)
        tags = extract_tags(text)
        assert len(tags) <= MAX_TAGS

    def test_no_stop_words_in_tags(self):
        from processing.tagger import extract_tags
        text = "The quick brown fox jumps over the lazy dog in the forest."
        tags = extract_tags(text)
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at"}
        for tag in tags:
            for word in tag.split():
                assert word not in stop_words

    def test_empty_text_returns_empty(self):
        from processing.tagger import extract_tags
        assert extract_tags("") == []
        assert extract_tags("   ") == []
