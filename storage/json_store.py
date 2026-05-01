"""
json_store.py
-------------
Handles all JSON and optional SQLite storage for scraped sources.
"""

import json
import os
import sqlite3
import logging
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger(__name__)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output", "scraped_data")
ALL_SOURCES_FILE = os.path.join(os.path.dirname(__file__), "..", "output", "scraped_data.json")
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "sources.db")


def ensure_output_dirs():
    """Create output directories if they don't exist."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(ALL_SOURCES_FILE), exist_ok=True)


def save_json(data: List[dict], filename: str) -> str:
    """Save a list of source dicts to a JSON file."""
    ensure_output_dirs()
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    logger.info(f"Saved {len(data)} records to {filepath}")
    return filepath


def load_json(filename: str) -> List[dict]:
    """Load sources from a JSON file."""
    filepath = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(filepath):
        logger.warning(f"File not found: {filepath}")
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_all_sources(sources: List[dict]) -> str:
    """Merge all sources into one combined JSON file."""
    ensure_output_dirs()
    with open(ALL_SOURCES_FILE, "w", encoding="utf-8") as f:
        json.dump(sources, f, indent=2, ensure_ascii=False, default=str)
    logger.info(f"Saved {len(sources)} total records to {ALL_SOURCES_FILE}")
    return ALL_SOURCES_FILE


def load_all_sources() -> List[dict]:
    """Load all sources from the combined JSON file."""
    if not os.path.exists(ALL_SOURCES_FILE):
        # Try to load from individual files
        sources = []
        for fname in ["blogs.json", "youtube.json", "pubmed.json"]:
            sources.extend(load_json(fname))
        return sources

    with open(ALL_SOURCES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def build_output_schema(source: dict) -> dict:
    """
    Convert a scraped+scored source dict to the required output schema.
    Strips internal fields not in the schema.
    """
    return {
        "source_url": source.get("source_url", ""),
        "source_type": source.get("source_type", ""),
        "title": source.get("title", ""),
        "author": source.get("author", "Unknown"),
        "published_date": source.get("published_date", ""),
        "language": source.get("language", "English"),
        "region": source.get("region", "Unknown"),
        "topic_tags": source.get("topic_tags", []),
        "trust_score": source.get("trust_score", 0.0),
        "score_breakdown": source.get("score_breakdown", {}),
        "explanation": source.get("explanation", ""),
        "content_chunks": source.get("content_chunks", []),
        # Extra fields for dashboard
        "journal": source.get("journal", ""),
        "domain": source.get("domain", ""),
        "has_transcript": source.get("has_transcript", None),
    }


def init_sqlite_db():
    """Initialize SQLite database with sources table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_url TEXT UNIQUE,
            source_type TEXT,
            title TEXT,
            author TEXT,
            published_date TEXT,
            language TEXT,
            region TEXT,
            topic_tags TEXT,
            trust_score REAL,
            explanation TEXT,
            content_chunks TEXT,
            score_breakdown TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_to_sqlite(sources: List[dict]):
    """Save sources to SQLite database."""
    init_sqlite_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for source in sources:
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO sources
                (source_url, source_type, title, author, published_date,
                 language, region, topic_tags, trust_score, explanation,
                 content_chunks, score_breakdown, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                source.get("source_url", ""),
                source.get("source_type", ""),
                source.get("title", ""),
                source.get("author", ""),
                source.get("published_date", ""),
                source.get("language", ""),
                source.get("region", ""),
                json.dumps(source.get("topic_tags", [])),
                source.get("trust_score", 0.0),
                source.get("explanation", ""),
                json.dumps(source.get("content_chunks", [])),
                json.dumps(source.get("score_breakdown", {})),
                datetime.now().isoformat(),
            ))
        except Exception as e:
            logger.error(f"SQLite insert failed for {source.get('source_url')}: {e}")

    conn.commit()
    conn.close()
    logger.info(f"Saved {len(sources)} records to SQLite: {DB_PATH}")
