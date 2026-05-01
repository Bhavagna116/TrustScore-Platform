"""
youtube_scraper.py
------------------
Scrapes YouTube video metadata and transcripts.
Uses yt-dlp for metadata (no API key required) and
youtube-transcript-api for captions/transcripts.
Falls back gracefully if transcripts are unavailable.
"""

import logging
import re
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)

# ── Pre-defined YouTube video URLs ───────────────────────────────────────────
YOUTUBE_URLS = [
    "https://www.youtube.com/watch?v=aircAruvnKk",   # 3Blue1Brown: Neural Networks
    "https://www.youtube.com/watch?v=ukzFI9rgwfU",   # What is Machine Learning?
]


def _extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r"(?:v=|/v/|youtu\.be/|/embed/)([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def _get_metadata_yt_dlp(url: str) -> dict:
    """
    Fetch video metadata using yt-dlp (no API key needed).
    Extracts: title, channel, upload date, description, view count.
    """
    try:
        import yt_dlp

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "skip_download": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        # Parse upload date (format: YYYYMMDD)
        raw_date = info.get("upload_date", "")
        pub_date = ""
        if raw_date and len(raw_date) == 8:
            try:
                pub_date = datetime.strptime(raw_date, "%Y%m%d").strftime("%Y-%m-%d")
            except ValueError:
                pub_date = raw_date

        return {
            "title": info.get("title", ""),
            "author": info.get("uploader", info.get("channel", "Unknown")),
            "published_date": pub_date,
            "description": info.get("description", "")[:2000],  # Cap at 2000 chars
            "view_count": info.get("view_count", 0),
            "like_count": info.get("like_count", 0),
            "duration": info.get("duration", 0),
            "channel_url": info.get("channel_url", ""),
            "tags": info.get("tags", [])[:10],
            "success": True,
        }
    except Exception as e:
        logger.warning(f"yt-dlp failed for {url}: {e}")
        return {"success": False}


def _get_transcript(video_id: str) -> str:
    """
    Fetch video transcript using youtube-transcript-api.
    Tries English first, then auto-generated captions.
    Returns concatenated transcript text or empty string.
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

        # Try manually created English transcript first
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        transcript = None
        # Prefer manually created English
        try:
            transcript = transcript_list.find_manually_created_transcript(["en", "en-US", "en-GB"])
        except NoTranscriptFound:
            pass

        # Fall back to auto-generated
        if not transcript:
            try:
                transcript = transcript_list.find_generated_transcript(["en", "en-US"])
            except NoTranscriptFound:
                pass

        # Fall back to any available transcript (translated to English)
        if not transcript:
            for t in transcript_list:
                try:
                    transcript = t.translate("en")
                    break
                except Exception:
                    continue

        if not transcript:
            logger.warning(f"No transcript available for video: {video_id}")
            return ""

        entries = transcript.fetch()
        full_text = " ".join(entry["text"] for entry in entries)
        # Clean up common transcript artifacts
        full_text = re.sub(r"\[.*?\]", "", full_text)  # Remove [Music], [Applause] etc.
        full_text = re.sub(r"\s+", " ", full_text).strip()
        return full_text

    except Exception as e:
        logger.warning(f"Transcript extraction failed for {video_id}: {e}")
        return ""


def scrape_youtube(url: str) -> Optional[dict]:
    """
    Scrape a single YouTube video.
    Returns structured data dict or None on failure.
    """
    logger.info(f"Scraping YouTube: {url}")

    video_id = _extract_video_id(url)
    if not video_id:
        logger.error(f"Could not extract video ID from URL: {url}")
        return None

    # Get metadata
    meta = _get_metadata_yt_dlp(url)
    if not meta.get("success"):
        # Minimal fallback using just transcript
        meta = {
            "title": f"YouTube Video ({video_id})",
            "author": "Unknown",
            "published_date": "",
            "description": "",
            "view_count": 0,
            "like_count": 0,
            "duration": 0,
            "channel_url": "",
            "tags": [],
            "success": False,
        }

    # Get transcript
    transcript_text = _get_transcript(video_id)
    has_transcript = bool(transcript_text)

    # Combine description + transcript as the main content
    text_content = ""
    if meta.get("description"):
        text_content += f"Description:\n{meta['description']}\n\n"
    if transcript_text:
        text_content += f"Transcript:\n{transcript_text}"
    elif meta.get("description"):
        text_content = meta["description"]
        logger.info(f"Using description as content (no transcript) for {video_id}")

    from scraper.blog_scraper import _infer_region
    domain = "youtube.com"
    region = "United States"  # YouTube is US-based

    return {
        "source_url": url,
        "source_type": "youtube",
        "title": meta.get("title", ""),
        "author": meta.get("author", "Unknown"),
        "published_date": meta.get("published_date", ""),
        "description": meta.get("description", ""),
        "text": text_content,
        "domain": domain,
        "region": region,
        "has_transcript": has_transcript,
        "video_id": video_id,
        "view_count": meta.get("view_count", 0),
        "tags": meta.get("tags", []),
    }


def scrape_all_youtube() -> list:
    """
    Scrape all pre-defined YouTube URLs.
    Returns list of scraped video dicts.
    """
    results = []
    for url in YOUTUBE_URLS:
        result = scrape_youtube(url)
        if result:
            results.append(result)
        else:
            logger.warning(f"Failed to scrape YouTube video: {url}")
            video_id = _extract_video_id(url) or "unknown"
            results.append({
                "source_url": url,
                "source_type": "youtube",
                "title": f"YouTube Video ({video_id})",
                "author": "Unknown",
                "published_date": "",
                "description": "",
                "text": "",
                "domain": "youtube.com",
                "region": "United States",
                "has_transcript": False,
                "video_id": video_id,
                "view_count": 0,
                "tags": [],
                "error": "Scraping failed"
            })
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    videos = scrape_all_youtube()
    for v in videos:
        print(f"\n--- {v['source_url']} ---")
        print(f"Title: {v['title']}")
        print(f"Author: {v['author']}")
        print(f"Date: {v['published_date']}")
        print(f"Has Transcript: {v['has_transcript']}")
        print(f"Text preview: {v['text'][:200]}...")
