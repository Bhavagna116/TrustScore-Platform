"""
routes.py
---------
Flask web dashboard routes for the Trust Scoring Platform.
Provides: main dashboard, source detail view, JSON API endpoints.
"""

import json
import os
import csv
import io
from flask import Flask, render_template, jsonify, request, abort, Response
from storage.json_store import load_all_sources, save_all_sources

app = Flask(__name__, template_folder="templates", static_folder="static")


def _get_sources():
    """Load all sources, adding sequential IDs."""
    sources = load_all_sources()
    for i, s in enumerate(sources):
        s["id"] = i
    return sources


@app.route("/")
def index():
    """Main dashboard page."""
    sources = _get_sources()
    stats = _compute_stats(sources)
    return render_template("index.html", sources=sources, stats=stats)


@app.route("/source/<int:source_id>")
def source_detail(source_id):
    """Detail page for a single source."""
    sources = _get_sources()
    if source_id >= len(sources) or source_id < 0:
        abort(404)
    source = sources[source_id]
    return render_template("detail.html", source=source)


@app.route("/api/sources")
def api_sources():
    """
    JSON API: return all sources with optional filtering.
    Query params:
      - source_type: blog|youtube|pubmed
      - min_score: float (0.0-1.0)
      - max_score: float (0.0-1.0)
      - tag: string (filter by tag)
      - q: string (search in title/author)
    """
    sources = _get_sources()

    # Filter: source type
    source_type = request.args.get("source_type", "").lower()
    if source_type and source_type != "all":
        sources = [s for s in sources if s.get("source_type", "").lower() == source_type]

    # Filter: trust score range
    try:
        min_score = float(request.args.get("min_score", 0.0))
        max_score = float(request.args.get("max_score", 1.0))
        sources = [s for s in sources if min_score <= s.get("trust_score", 0) <= max_score]
    except ValueError:
        pass

    # Filter: tag
    tag = request.args.get("tag", "").lower()
    if tag:
        sources = [s for s in sources if any(tag in t.lower() for t in s.get("topic_tags", []))]

    # Search: title/author
    query = request.args.get("q", "").lower()
    if query:
        sources = [
            s for s in sources
            if query in s.get("title", "").lower() or query in s.get("author", "").lower()
        ]

    import json
    return app.response_class(
        response=json.dumps(sources, indent=4),
        status=200,
        mimetype='application/json'
    )

@app.route("/api/stats")
def api_stats():
    """JSON API: aggregate statistics for charts."""
    sources = _get_sources()
    stats = _compute_stats(sources)
    return jsonify(stats)


@app.route("/api/source/<int:source_id>")
def api_source_detail(source_id):
    """JSON API: single source detail."""
    sources = _get_sources()
    if source_id >= len(sources) or source_id < 0:
        return jsonify({"error": "Not found"}), 404
    return jsonify(sources[source_id])


@app.route("/api/export")
def api_export():
    """Export filtered sources as CSV or JSON."""
    fmt = request.args.get("format", "csv")
    # Reuse the filter logic by calling the api_sources function internally,
    # or just fetching the raw request since api_sources returns JSON.
    # To keep it simple, we duplicate the filter logic or just apply it here.
    sources = _get_sources()

    # Apply filters
    source_type = request.args.get("source_type", "").lower()
    if source_type and source_type != "all":
        sources = [s for s in sources if s.get("source_type", "").lower() == source_type]

    try:
        min_score = float(request.args.get("min_score", 0.0))
        max_score = float(request.args.get("max_score", 1.0))
        sources = [s for s in sources if min_score <= s.get("trust_score", 0) <= max_score]
    except ValueError:
        pass

    tag = request.args.get("tag", "").lower()
    if tag:
        sources = [s for s in sources if any(tag in t.lower() for t in s.get("topic_tags", []))]

    query = request.args.get("q", "").lower()
    if query:
        sources = [s for s in sources if query in s.get("title", "").lower() or query in s.get("author", "").lower()]

    if fmt == "json":
        return jsonify(sources)
    
    # CSV Export
    si = io.StringIO()
    cw = csv.writer(si)
    # Header
    cw.writerow(["Title", "URL", "Source Type", "Author", "Published Date", "Trust Score", "Tags", "Explanation"])
    for s in sources:
        cw.writerow([
            s.get("title", ""),
            s.get("source_url", ""),
            s.get("source_type", ""),
            s.get("author", ""),
            s.get("published_date", ""),
            s.get("trust_score", 0.0),
            ", ".join(s.get("topic_tags", [])),
            s.get("explanation", "")
        ])
    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=trustscore_export.csv"}
    )


@app.route("/api/scrape", methods=["POST"])
def api_scrape():
    """On-demand scraping endpoint."""
    data = request.json
    url = data.get("url")
    if not url:
        return jsonify({"error": "URL is required"}), 400

    from processing.cleaner import clean_text, clean_author, clean_date
    from processing.language_detector import detect_language_and_region
    from processing.chunker import chunk_text, chunk_transcript
    from processing.tagger import extract_tags
    from scoring.trust_scorer import score_source
    from storage.json_store import build_output_schema

    # Determine type
    if "youtube.com" in url or "youtu.be" in url:
        from scraper.youtube_scraper import scrape_youtube_video
        raw_source = scrape_youtube_video(url)
    elif "pubmed.ncbi.nlm.nih.gov" in url:
        from scraper.pubmed_scraper import fetch_pubmed_article
        # Extract ID from URL
        import re
        match = re.search(r'pubmed\.ncbi\.nlm\.nih\.gov/(\d+)', url)
        if match:
            raw_source = fetch_pubmed_article(match.group(1))
            if raw_source:
                raw_source["source_url"] = url
        else:
            return jsonify({"error": "Invalid PubMed URL"}), 400
    else:
        from scraper.blog_scraper import scrape_blog
        raw_source = scrape_blog(url)

    if not raw_source:
        return jsonify({"error": "Failed to scrape URL"}), 500

    # Process & Score
    text = clean_text(raw_source.get("text", ""))
    raw_source["text"] = text
    raw_source["author"] = clean_author(raw_source.get("author", "Unknown"))
    raw_source["published_date"] = clean_date(raw_source.get("published_date", ""))
    
    lang_info = detect_language_and_region(text, raw_source.get("domain", ""))
    raw_source["language"] = lang_info["language"]
    if not raw_source.get("region") or raw_source.get("region") == "Unknown":
        raw_source["region"] = lang_info["region"]

    tag_text = text if text else raw_source.get("description", "")
    raw_source["topic_tags"] = extract_tags(tag_text)

    if raw_source.get("source_type") == "youtube" and raw_source.get("has_transcript"):
        raw_source["content_chunks"] = chunk_transcript(text)
    else:
        raw_source["content_chunks"] = chunk_text(text)

    scored = score_source(raw_source)
    final = build_output_schema(scored)
    final["score_breakdown"] = scored.get("score_breakdown", {})
    final["explanation"] = scored.get("explanation", "")
    final["component_explanations"] = scored.get("component_explanations", {})

    # Save
    sources = load_all_sources()
    sources.insert(0, final) # Add to top
    save_all_sources(sources)

    final["id"] = 0 # New ID will be 0 since we inserted at top, but just for UI response
    return jsonify(final)


def _compute_stats(sources):
    """Compute aggregate statistics for the dashboard."""
    if not sources:
        return {}

    scores = [s.get("trust_score", 0) for s in sources]
    by_type = {}
    for s in sources:
        t = s.get("source_type", "unknown")
        by_type.setdefault(t, []).append(s.get("trust_score", 0))

    # Tag frequency
    tag_freq = {}
    for s in sources:
        for tag in s.get("topic_tags", []):
            tag_freq[tag] = tag_freq.get(tag, 0) + 1
    top_tags = sorted(tag_freq.items(), key=lambda x: -x[1])[:15]

    return {
        "total": len(sources),
        "avg_score": round(sum(scores) / len(scores), 3) if scores else 0,
        "max_score": round(max(scores), 3) if scores else 0,
        "min_score": round(min(scores), 3) if scores else 0,
        "by_type": {k: {"count": len(v), "avg_score": round(sum(v)/len(v), 3)}
                    for k, v in by_type.items()},
        "top_tags": [{"tag": t, "count": c} for t, c in top_tags],
        "score_distribution": {
            "high": sum(1 for s in scores if s >= 0.7),
            "medium": sum(1 for s in scores if 0.4 <= s < 0.7),
            "low": sum(1 for s in scores if s < 0.4),
        },
    }


if __name__ == "__main__":
    app.run(debug=True, port=5000)
