# 🔍 TrustScore AI — Multi-Source Data Scraping & Trust Scoring Platform

A production-quality end-to-end system that **scrapes content** from blogs, YouTube, and PubMed, **processes it with NLP**, assigns **trust scores**, and visualizes everything in a **premium Flask web dashboard**.

---

## 🗂️ Project Structure

```
Task 1/
├── scraper/
│   ├── blog_scraper.py        # newspaper3k + BeautifulSoup, 3 blog posts
│   ├── youtube_scraper.py     # yt-dlp + youtube-transcript-api, 2 videos
│   └── pubmed_scraper.py      # Biopython Entrez API, 1 PubMed article
├── processing/
│   ├── cleaner.py             # HTML removal, dedup, reference counting
│   ├── language_detector.py   # langdetect, region inference
│   ├── chunker.py             # ≤300 word paragraph/sentence chunks
│   └── tagger.py              # RAKE-NLTK + TF-IDF topic tags
├── scoring/
│   ├── trust_scorer.py        # Weighted formula + XAI explanations
│   ├── domain_checker.py      # Domain authority heuristics
│   └── abuse_detector.py      # Spam, fake authors, recency scoring
├── storage/
│   └── json_store.py          # JSON + SQLite persistence
├── app/
│   ├── routes.py              # Flask routes + JSON API
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html         # Main dashboard
│   │   └── detail.html        # Source detail + radar chart
│   └── static/
│       ├── css/style.css      # Dark mode glassmorphism design
│       └── js/dashboard.js    # Chart.js + filter/search logic
├── output/
│   ├── scraped_data/
│   │   ├── blogs.json
│   │   ├── youtube.json
│   │   └── pubmed.json
│   └── scraped_data.json
├── tests/
│   ├── test_scraper.py
│   ├── test_scoring.py
│   └── test_processing.py
├── main.py                    # CLI entry point
├── requirements.txt
└── README.md
```

---

## ⚡ Quick Start

### 1. Install Dependencies

```bash
cd "Task 1"
pip install -r requirements.txt
```

**Download required NLTK data:**
```bash
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('punkt_tab')"
```

### 2. Option A: Run with Demo Data (No Internet Required)

```bash
python main.py demo
```
Opens the dashboard at **http://localhost:5000** with pre-built sample data.

### 3. Option B: Run Full Pipeline (Scrapes Real Data)

```bash
# Step 1: Scrape all sources
python main.py scrape

# Step 2: Process + score
python main.py score

# Step 3: Launch dashboard
python main.py serve
```

Or all in one command:
```bash
python main.py all
```

### 4. Run Tests

```bash
pytest tests/ -v
```

---

## 🌐 Web Dashboard Features

| Feature | Description |
|---|---|
| Source Cards | All sources with trust score progress bars |
| Filter by Type | Blog / YouTube / PubMed buttons |
| Min Score Slider | Filter by minimum trust score |
| Tag Filter | Click any tag to filter sources |
| Search | Search by title or author |
| Score Breakdown Chart | Bar chart by source type |
| Tag Frequency Chart | Horizontal bar of top tags |
| Distribution Chart | Doughnut: High/Medium/Low trust |
| Detail Page | Full content chunks + radar chart |
| XAI Explanation | Human-readable score breakdown |

### API Endpoints

```
GET /                         Dashboard UI
GET /source/<id>              Source detail page
GET /api/sources              JSON: all sources (with filters)
GET /api/sources?source_type=blog&min_score=0.7
GET /api/sources?tag=AI&q=machine+learning
GET /api/stats                JSON: aggregate statistics
GET /api/source/<id>          JSON: single source
```

---

## 🔍 Trust Score Formula

```
Trust Score = (
  0.25 × author_credibility  +
  0.20 × citation_count      +
  0.25 × domain_authority    +
  0.20 × recency             +
  0.10 × medical_disclaimer
) − spam_penalty
```

### Component Descriptions

| Component | Range | Method |
|---|---|---|
| **Author Credibility** | 0–1 | Named author patterns, credentials, multi-author bonus |
| **Citation Count** | 0–1 | Counts [N], (Author, Year), DOI links in text |
| **Domain Authority** | 0–1 | Curated domain lists + TLD heuristics |
| **Recency** | 0–1 | Exponential decay from publication date |
| **Medical Disclaimer** | 0 or 1 | Pattern matching for disclaimer language |
| **Spam Penalty** | −0–0.3 | Keyword stuffing + misleading claims |

### Trust Score Interpretation

| Score | Label | Color |
|---|---|---|
| ≥ 0.80 | ✅ HIGH TRUST | Green |
| 0.60–0.79 | 🟡 MODERATE TRUST | Yellow |
| 0.40–0.59 | 🟠 LOW-MODERATE TRUST | Orange |
| < 0.40 | 🔴 LOW TRUST | Red |

---

## 📊 Output Schema

Each source produces:
```json
{
  "source_url": "https://...",
  "source_type": "blog | youtube | pubmed",
  "title": "...",
  "author": "...",
  "published_date": "YYYY-MM-DD",
  "language": "English",
  "region": "United States",
  "topic_tags": ["ai", "machine learning", "healthcare"],
  "trust_score": 0.87,
  "score_breakdown": {
    "author_credibility": 0.8,
    "citation_count": 0.75,
    "domain_authority": 0.95,
    "recency": 0.85,
    "medical_disclaimer": 0.0
  },
  "explanation": "HIGH TRUST (score: 0.87). Strong factors: domain authority, recency.",
  "component_explanations": {
    "author_credibility": "Named author with credentials found",
    "domain_authority": "Known high-authority domain (nature.com)"
  },
  "content_chunks": [
    "First 300-word chunk...",
    "Second 300-word chunk..."
  ]
}
```

---

## 🛡️ Abuse Prevention Logic

- **Keyword Stuffing**: Detects if top content word exceeds 5% density → penalty applied
- **Fake Authors**: Flags single-letter names, pure numbers, generic names (admin, user)
- **Misleading Medical Claims**: Pattern-matches "miracle cure", "100% guaranteed", "doctors don't want you to know"
- **Outdated Content**: Age-decay curve → content >5 years scores <0.40 for recency
- **Low-Quality Domains**: `.xyz`, `.tk`, `.click` TLDs → low domain authority scores
- **SEO Spam**: Excessive ALL CAPS, excessive `!` marks → spam penalty

---

## 🧠 NLP Tagging Strategy

1. **RAKE (Rapid Automatic Keyword Extraction)**: Multi-word phrase extraction scored by word co-occurrence frequency. Produces contextually rich tags.
2. **TF-IDF Fallback**: If RAKE produces fewer than 3 tags, supplements with TF-IDF scored single words.
3. **Validation**: Tags filtered for stop words, minimum 3 characters, max 4 words per tag.

---

## ⚙️ Edge Cases Handled

| Case | Handling |
|---|---|
| Missing author | Score 0.3 (neutral), explanation notes missing data |
| Missing date | Recency defaults to 0.4 (moderate age assumed) |
| No YouTube transcript | Uses video description as content |
| Non-English content | langdetect identifies language, processing continues |
| Very long articles | Chunker splits into ≤300 word segments |
| Multiple authors | Lists all authors, boosts credibility score |
| Scraping failure | Returns placeholder with error flag, pipeline continues |

---

## ⚠️ Limitations

| Limitation | Details |
|---|---|
| **No real-time scraping** | Sources are pre-defined URLs; no live search/discovery |
| **YouTube transcripts** | Only available for videos with captions enabled; falls back to description |
| **Blog JS rendering** | `newspaper3k` may fail on heavily JavaScript-rendered pages (Playwright needed for those) |
| **PubMed citation count** | Entrez elink may return incomplete counts vs. full citation databases (e.g., Scopus, Web of Science) |
| **Author credibility** | Heuristic-only; no cross-reference with academic author databases (e.g., ORCID) |
| **Domain authority** | Based on curated lists + TLD; no live PageRank or Moz DA lookup |
| **Language detection** | Low-confidence for very short texts (<50 words); defaults to English |
| **Scale** | Demo scrapes 6 fixed sources; production deployment would require async scraping + rate-limit management |

---

## 📚 Report

### Scraping Strategy
- **Blogs**: `newspaper3k` (primary) → `BeautifulSoup` (fallback). Removes nav/ads via tag decomposition and CSS class pattern matching.
- **YouTube**: `yt-dlp` for metadata (no API key needed) + `youtube-transcript-api` for captions. Falls back to description if no transcript.
- **PubMed**: NCBI Entrez API via `biopython`. Structured XML parsing extracts all metadata fields. Rate-limited to 3 req/sec.

### Trust Scoring Logic
Weighted sum of 5 normalized components. Domain authority uses a curated list of 50+ known high-authority domains plus TLD heuristics. Spam penalty is subtracted after the weighted sum, capped at 0.30.

### Tagging Method
RAKE extracts multi-word keyword phrases ranked by degree/frequency ratio. Supplemented by TF-IDF for single-word terms. Maximum 8 tags per source.

### Edge Case Handling
All scrapers return placeholder records on failure so the pipeline never crashes. Missing metadata fields are handled with sensible defaults. Multiple authors are averaged for credibility scoring.
