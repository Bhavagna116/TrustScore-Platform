"""
test_scraper.py
---------------
Unit tests for the scraping layer.
Uses mocking to avoid actual network requests.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestBlogScraper:
    def test_infer_region_edu(self):
        from scraper.blog_scraper import _infer_region
        assert _infer_region("mit.edu") == "United States"

    def test_infer_region_gov(self):
        from scraper.blog_scraper import _infer_region
        assert _infer_region("cdc.gov") == "United States"

    def test_infer_region_uk(self):
        from scraper.blog_scraper import _infer_region
        assert _infer_region("bbc.co.uk") == "United Kingdom"

    def test_infer_region_unknown(self):
        from scraper.blog_scraper import _infer_region
        result = _infer_region("randomxyz123.zz")
        assert isinstance(result, str)

    def test_extract_with_bs4_minimal(self):
        from scraper.blog_scraper import _extract_with_bs4
        html = """
        <html><head><title>Test Article</title>
        <meta name="author" content="Jane Doe">
        <meta property="article:published_time" content="2024-03-15">
        <meta name="description" content="A great article about AI.">
        </head>
        <body><article><p>This is a long enough article about artificial intelligence
        and its applications in modern technology and healthcare systems. The text 
        goes on for a sufficient length to pass validation checks.</p></article>
        </body></html>
        """
        result = _extract_with_bs4("https://example.com/test", html)
        assert result["title"] == "Test Article"


class TestYoutubeScraper:
    def test_extract_video_id_standard(self):
        from scraper.youtube_scraper import _extract_video_id
        vid_id = _extract_video_id("https://www.youtube.com/watch?v=aircAruvnKk")
        assert vid_id == "aircAruvnKk"

    def test_extract_video_id_short(self):
        from scraper.youtube_scraper import _extract_video_id
        vid_id = _extract_video_id("https://youtu.be/aircAruvnKk")
        assert vid_id == "aircAruvnKk"

    def test_extract_video_id_invalid(self):
        from scraper.youtube_scraper import _extract_video_id
        vid_id = _extract_video_id("https://example.com/not-a-video")
        assert vid_id is None


class TestPubmedScraper:
    def test_pubmed_ids_defined(self):
        from scraper.pubmed_scraper import PUBMED_IDS
        assert len(PUBMED_IDS) >= 1
        assert all(id_.isdigit() for id_ in PUBMED_IDS)
