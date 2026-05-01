"""
main.py
-------
CLI entry point for the Multi-Source Data Scraping & Trust Scoring Platform.

Commands:
  python main.py scrape   — Scrape all sources and save raw JSON
  python main.py score    — Apply trust scoring to scraped data
  python main.py serve    — Start the Flask web dashboard
  python main.py all      — Run full pipeline end-to-end
  python main.py demo     — Load demo data (no internet required)
"""

import sys
import os
import json
import logging
import argparse
from datetime import datetime

# Ensure project root is in Python path
sys.path.insert(0, os.path.dirname(__file__))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


def cmd_scrape():
    """Run all scrapers and save raw JSON files."""
    from scraper.blog_scraper import scrape_all_blogs
    from scraper.youtube_scraper import scrape_all_youtube
    from scraper.pubmed_scraper import scrape_all_pubmed
    from storage.json_store import save_json, ensure_output_dirs

    ensure_output_dirs()
    logger.info("=" * 50)
    logger.info("  Starting Multi-Source Scraping Pipeline")
    logger.info("=" * 50)

    # Scrape blogs
    logger.info("\n[1/3] Scraping Blog Posts...")
    blogs = scrape_all_blogs()
    save_json(blogs, "blogs_raw.json")
    logger.info(f"  ✓ {len(blogs)} blog(s) scraped")

    # Scrape YouTube
    logger.info("\n[2/3] Scraping YouTube Videos...")
    videos = scrape_all_youtube()
    save_json(videos, "youtube_raw.json")
    logger.info(f"  ✓ {len(videos)} video(s) scraped")

    # Scrape PubMed
    logger.info("\n[3/3] Scraping PubMed Articles...")
    articles = scrape_all_pubmed()
    save_json(articles, "pubmed_raw.json")
    logger.info(f"  ✓ {len(articles)} article(s) scraped")

    logger.info("\n✅ Scraping complete. Raw data saved to output/scraped_data/")
    return blogs + videos + articles


def cmd_score(raw_sources=None):
    """Apply NLP processing and trust scoring to scraped sources."""
    from storage.json_store import (
        load_json, save_json, save_all_sources,
        save_to_sqlite, build_output_schema
    )
    from processing.cleaner import clean_text, clean_author, clean_date
    from processing.language_detector import detect_language_and_region
    from processing.chunker import chunk_text, chunk_transcript
    from processing.tagger import extract_tags
    from scoring.trust_scorer import score_source

    logger.info("\n" + "=" * 50)
    logger.info("  Starting Processing & Scoring Pipeline")
    logger.info("=" * 50)

    if raw_sources is None:
        # Load from files
        raw_sources = []
        for fname in ["blogs_raw.json", "youtube_raw.json", "pubmed_raw.json"]:
            raw_sources.extend(load_json(fname))

    if not raw_sources:
        logger.error("No sources to score. Run 'python main.py scrape' first.")
        return []

    processed = []
    for i, source in enumerate(raw_sources):
        url = source.get("source_url", f"source_{i}")
        logger.info(f"\nProcessing [{i+1}/{len(raw_sources)}]: {url[:60]}")

        try:
            # 1. Clean text
            raw_text = source.get("text", "")
            text = clean_text(raw_text)
            source["text"] = text

            # 2. Clean metadata
            source["author"] = clean_author(source.get("author", "Unknown"))
            source["published_date"] = clean_date(source.get("published_date", ""))

            # 3. Language + region detection
            lang_info = detect_language_and_region(text, source.get("domain", ""))
            source["language"] = lang_info["language"]
            source["language_code"] = lang_info["language_code"]
            if not source.get("region") or source.get("region") == "Unknown":
                source["region"] = lang_info["region"]

            # 4. Topic tagging
            tag_text = text if text else source.get("description", "")
            source["topic_tags"] = extract_tags(tag_text)
            logger.info(f"  Tags: {source['topic_tags'][:4]}")

            # 5. Content chunking
            if source.get("source_type") == "youtube" and source.get("has_transcript"):
                source["content_chunks"] = chunk_transcript(text)
            else:
                source["content_chunks"] = chunk_text(text)
            logger.info(f"  Chunks: {len(source['content_chunks'])}")

            # 6. Trust scoring
            scored = score_source(source)
            logger.info(f"  Trust Score: {scored.get('trust_score', 0):.3f} — {scored.get('explanation', '')[:60]}")

            # 7. Build final schema
            final = build_output_schema(scored)
            # Keep extra fields for dashboard
            final["score_breakdown"] = scored.get("score_breakdown", {})
            final["explanation"] = scored.get("explanation", "")
            final["component_explanations"] = scored.get("component_explanations", {})
            processed.append(final)

        except Exception as e:
            logger.error(f"  Failed to process {url}: {e}", exc_info=True)
            # Add with defaults on error
            processed.append({
                "source_url": url,
                "source_type": source.get("source_type", "unknown"),
                "title": source.get("title", ""),
                "author": source.get("author", "Unknown"),
                "published_date": source.get("published_date", ""),
                "language": "English",
                "region": "Unknown",
                "topic_tags": [],
                "trust_score": 0.0,
                "score_breakdown": {},
                "explanation": f"Processing error: {str(e)}",
                "content_chunks": [],
            })

    # Save by type
    blogs = [s for s in processed if s.get("source_type") == "blog"]
    videos = [s for s in processed if s.get("source_type") == "youtube"]
    articles = [s for s in processed if s.get("source_type") == "pubmed"]

    save_json(blogs, "blogs.json")
    save_json(videos, "youtube.json")
    save_json(articles, "pubmed.json")
    save_all_sources(processed)

    # Optional: save to SQLite
    try:
        save_to_sqlite(processed)
    except Exception as e:
        logger.warning(f"SQLite save failed (non-critical): {e}")

    logger.info(f"\n✅ Scoring complete. {len(processed)} sources processed.")
    logger.info("   Output: output/all_sources.json + output/scraped_data/")
    return processed


def cmd_demo():
    """
    Load pre-built demo data (no internet required).
    Creates realistic sample data for testing the dashboard.
    """
    from storage.json_store import save_json, save_all_sources, ensure_output_dirs

    ensure_output_dirs()
    logger.info("Loading demo data...")

    demo_sources = [
        {
            "source_url": "https://www.nature.com/articles/d41586-023-03817-6",
            "source_type": "blog",
            "title": "How AI is transforming drug discovery",
            "author": "Dr. Sarah Chen",
            "published_date": "2024-01-15",
            "language": "English",
            "region": "United States",
            "topic_tags": ["artificial intelligence", "drug discovery", "machine learning", "healthcare", "deep learning"],
            "trust_score": 0.87,
            "score_breakdown": {
                "author_credibility": 0.8,
                "citation_count": 0.75,
                "domain_authority": 0.95,
                "recency": 0.85,
                "medical_disclaimer": 0.0
            },
            "explanation": "HIGH TRUST (score: 0.87). Strong factors: domain authority, author credibility, recency.",
            "component_explanations": {
                "author_credibility": "Named author with credentials found",
                "citation_count": "8 references found",
                "domain_authority": "Known high-authority domain (nature.com)",
                "recency": "Content is recent (< 1 year)",
                "medical_disclaimer": "No medical disclaimer"
            },
            "content_chunks": [
                "Artificial intelligence is revolutionizing the pharmaceutical industry. Machine learning models can now predict how molecules will interact with biological targets with unprecedented accuracy.",
                "Deep learning systems trained on vast chemical databases can identify potential drug candidates in days rather than years. This dramatically reduces the time and cost of early-stage drug discovery.",
                "Clinical trials and regulatory approval still require human oversight, but AI is accelerating every phase from target identification to lead optimization.",
            ],
            "journal": "",
            "domain": "nature.com",
            "has_transcript": None,
        },
        {
            "source_url": "https://hbr.org/2023/07/how-to-use-ai-responsibly",
            "source_type": "blog",
            "title": "How to Use AI Responsibly in Your Organization",
            "author": "Michael Porter, Linda Hill",
            "published_date": "2023-07-12",
            "language": "English",
            "region": "United States",
            "topic_tags": ["ai ethics", "responsible ai", "organizational change", "leadership", "governance"],
            "trust_score": 0.79,
            "score_breakdown": {
                "author_credibility": 0.85,
                "citation_count": 0.6,
                "domain_authority": 0.9,
                "recency": 0.70,
                "medical_disclaimer": 0.0
            },
            "explanation": "HIGH TRUST (score: 0.79). Strong factors: domain authority, author credibility.",
            "component_explanations": {
                "author_credibility": "Multiple named authors with credentials",
                "citation_count": "5 references found",
                "domain_authority": "Known high-authority domain (hbr.org)",
                "recency": "Content is aging (1-2 years)",
                "medical_disclaimer": "No medical disclaimer"
            },
            "content_chunks": [
                "As AI becomes embedded in organizational decision-making, leaders face new challenges around accountability, transparency, and fairness. Responsible AI requires more than technical safeguards.",
                "Organizations must establish clear governance frameworks before deploying AI systems. This includes defining who owns AI decisions, how errors are detected and corrected, and what data practices are acceptable.",
                "Employee trust is essential. Workers who understand how AI tools work and what limitations they have are better equipped to use them effectively and flag problems early.",
            ],
            "journal": "",
            "domain": "hbr.org",
            "has_transcript": None,
        },
        {
            "source_url": "https://www.who.int/news-room/feature-stories/detail/who-can-i-believe-helping-people-navigate-an-infodemic",
            "source_type": "blog",
            "title": "Who can I believe? Helping people navigate an infodemic",
            "author": "WHO Communications Team",
            "published_date": "2020-09-23",
            "language": "English",
            "region": "International",
            "topic_tags": ["infodemic", "misinformation", "health communication", "covid-19", "media literacy"],
            "trust_score": 0.91,
            "score_breakdown": {
                "author_credibility": 0.85,
                "citation_count": 0.5,
                "domain_authority": 0.95,
                "recency": 0.35,
                "medical_disclaimer": 1.0
            },
            "explanation": "HIGH TRUST (score: 0.91). Strong factors: domain authority, medical disclaimer present. Weak: recency (2020).",
            "component_explanations": {
                "author_credibility": "WHO institutional author",
                "citation_count": "4 references found",
                "domain_authority": "Known high-authority domain (who.int)",
                "recency": "Content is old (2020)",
                "medical_disclaimer": "Medical disclaimer found"
            },
            "content_chunks": [
                "The COVID-19 pandemic has been accompanied by a massive infodemic — an overabundance of information, including misinformation, that makes it difficult for people to find trustworthy guidance.",
                "WHO is working with governments, technology companies, and civil society to help people identify reliable information and protect themselves from false claims.",
                "Critical thinking skills are more important than ever. People should verify sources, check whether information is from a credible institution, and look for medical consensus before sharing health-related content.",
            ],
            "journal": "",
            "domain": "who.int",
            "has_transcript": None,
        },
        {
            "source_url": "https://www.youtube.com/watch?v=aircAruvnKk",
            "source_type": "youtube",
            "title": "But what is a neural network? | Deep learning chapter 1",
            "author": "3Blue1Brown",
            "published_date": "2017-10-05",
            "language": "English",
            "region": "United States",
            "topic_tags": ["neural networks", "deep learning", "machine learning", "artificial intelligence", "mathematics"],
            "trust_score": 0.72,
            "score_breakdown": {
                "author_credibility": 0.65,
                "citation_count": 0.0,
                "domain_authority": 0.6,
                "recency": 0.15,
                "medical_disclaimer": 0.0
            },
            "explanation": "MODERATE TRUST (score: 0.72). Strong factors: domain authority. Weak: recency (2017), citation count.",
            "component_explanations": {
                "author_credibility": "Named channel with educational content",
                "citation_count": "No citations in transcript",
                "domain_authority": "Known medium-authority domain (youtube.com)",
                "recency": "Content is very old (2017)",
                "medical_disclaimer": "No medical disclaimer"
            },
            "content_chunks": [
                "When you see a picture of a handwritten digit and ask what number it is, your brain effortlessly recognizes the answer. But teaching a computer to do the same thing is surprisingly complex.",
                "A neural network is a series of layers — each layer a collection of neurons — that transform input data step by step. Each neuron computes a weighted sum of its inputs and passes it through an activation function.",
                "Training a neural network means adjusting millions of weights so the network's outputs match the desired answers. This is done through backpropagation and gradient descent over massive datasets.",
            ],
            "journal": "",
            "domain": "youtube.com",
            "has_transcript": True,
        },
        {
            "source_url": "https://www.youtube.com/watch?v=ukzFI9rgwfU",
            "source_type": "youtube",
            "title": "Machine Learning Explained in 100 Seconds",
            "author": "Fireship",
            "published_date": "2021-05-20",
            "language": "English",
            "region": "United States",
            "topic_tags": ["machine learning", "programming", "data science", "algorithms", "python"],
            "trust_score": 0.58,
            "score_breakdown": {
                "author_credibility": 0.6,
                "citation_count": 0.0,
                "domain_authority": 0.6,
                "recency": 0.55,
                "medical_disclaimer": 0.0
            },
            "explanation": "MODERATE TRUST (score: 0.58). Weak factors: citation count, author credibility.",
            "component_explanations": {
                "author_credibility": "Popular tech channel, unverified credentials",
                "citation_count": "No academic citations",
                "domain_authority": "Known medium-authority domain (youtube.com)",
                "recency": "Content is aging (2021)",
                "medical_disclaimer": "No medical disclaimer"
            },
            "content_chunks": [
                "Machine learning is a subset of artificial intelligence where systems learn from data to make predictions or decisions without being explicitly programmed for each task.",
                "The three main types of machine learning are supervised learning (trained on labeled data), unsupervised learning (finds patterns without labels), and reinforcement learning (learns from rewards).",
            ],
            "journal": "",
            "domain": "youtube.com",
            "has_transcript": False,
        },
        {
            "source_url": "https://pubmed.ncbi.nlm.nih.gov/37638757/",
            "source_type": "pubmed",
            "title": "Large language models in medicine",
            "author": "Thirunavukarasu AJ, Ting DSJ, Elangovan K, Gutierrez L, Tan TF, Ting DSW",
            "published_date": "2023-08-01",
            "language": "English",
            "region": "United States",
            "topic_tags": ["large language models", "clinical medicine", "artificial intelligence", "natural language processing", "healthcare"],
            "trust_score": 0.94,
            "score_breakdown": {
                "author_credibility": 0.85,
                "citation_count": 1.0,
                "domain_authority": 0.95,
                "recency": 0.85,
                "medical_disclaimer": 0.0
            },
            "explanation": "HIGH TRUST (score: 0.94). Strong factors: domain authority, citation count, author credibility, recency.",
            "component_explanations": {
                "author_credibility": "6 academic authors with institutional affiliations",
                "citation_count": "100+ citations in PubMed Central",
                "domain_authority": "Known high-authority domain (pubmed.ncbi.nlm.nih.gov)",
                "recency": "Content is recent (2023)",
                "medical_disclaimer": "No medical disclaimer (academic paper)"
            },
            "content_chunks": [
                "Large language models (LLMs) represent a transformative advancement in natural language processing, with emerging applications across clinical medicine. These models demonstrate remarkable capabilities in medical question answering, clinical documentation, and diagnostic reasoning.",
                "GPT-4 and similar models achieve passing scores on medical licensing examinations, suggesting substantial biomedical knowledge acquisition. However, challenges remain around hallucination, bias, and reliability in high-stakes clinical settings.",
                "Integration of LLMs into clinical workflows requires robust validation frameworks, attention to patient privacy, and careful consideration of how these tools interact with existing clinical decision support systems.",
            ],
            "journal": "Nature Medicine",
            "domain": "pubmed.ncbi.nlm.nih.gov",
            "has_transcript": None,
        },
    ]

    # Save by type
    save_json([s for s in demo_sources if s["source_type"] == "blog"], "blogs.json")
    save_json([s for s in demo_sources if s["source_type"] == "youtube"], "youtube.json")
    save_json([s for s in demo_sources if s["source_type"] == "pubmed"], "pubmed.json")
    save_all_sources(demo_sources)

    logger.info(f"✅ Demo data loaded: {len(demo_sources)} sources")
    return demo_sources


def cmd_serve():
    """Start the Flask web dashboard."""
    logger.info("\n" + "=" * 50)
    logger.info("  Starting TrustScore AI Web Dashboard")
    logger.info("  Open: http://localhost:5000")
    logger.info("=" * 50)

    from app.routes import app
    app.run(debug=False, host="0.0.0.0", port=5000)


def cmd_all():
    """Run the full pipeline: scrape → score → serve."""
    logger.info("\n🚀 Running full pipeline...\n")
    raw = cmd_scrape()
    cmd_score(raw)
    cmd_serve()


def main():
    parser = argparse.ArgumentParser(
        description="TrustScore AI — Multi-Source Data Scraping & Trust Scoring Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  scrape   Scrape all sources (blogs, YouTube, PubMed)
  score    Process + score scraped data
  serve    Start the web dashboard at http://localhost:5000
  demo     Load demo data (no internet), then serve
  all      Full pipeline: scrape + score + serve
        """
    )
    parser.add_argument(
        "command",
        choices=["scrape", "score", "serve", "demo", "all"],
        help="Command to run"
    )

    args = parser.parse_args()

    try:
        if args.command == "scrape":
            cmd_scrape()
        elif args.command == "score":
            cmd_score()
        elif args.command == "serve":
            cmd_serve()
        elif args.command == "demo":
            cmd_demo()
            cmd_serve()
        elif args.command == "all":
            cmd_all()
    except KeyboardInterrupt:
        logger.info("\n\nStopped by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
