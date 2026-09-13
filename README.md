# Polymer Data Pipeline

Scientific literature aggregation system for polymer and packaging research. Queries 8 academic databases in parallel, deduplicates results, and provides an interactive dashboard for exploration and export.

## Overview

This tool automates the systematic review process for polymer science research. It searches multiple academic APIs simultaneously, normalizes the results into a common format, applies relevance filters, and presents everything through a web interface with filtering, visualization, and export capabilities.

The pipeline supports three search modes:
- **Presets**: Pre-configured searches across 4 research levels (blends, additives, packaging, biodegradation)
- **Free search**: Custom boolean queries with full control over search terms
- **Visual builder**: GUI-based query construction for users unfamiliar with boolean syntax

## Features

- **Async HTTP**: All 8 APIs queried concurrently with aiohttp
- **Rate limiting**: Per-API limits to avoid being blocked (Crossref 40/s, PubMed 9/s, etc.)
- **Automatic retry**: Exponential backoff with jitter on failures
- **Three search modes**: Presets (L1-L4), free boolean search, visual query builder
- **Multi-row selection**: Select multiple articles and export only those
- **Interactive charts**: Plotly visualizations (year, journals, keywords, sources, levels)
- **Data quality metrics**: Coverage stats for DOI, abstracts, PDFs
- **Saved searches**: Store and load search configurations from JSON
- **PDF download**: Download PDFs locally or upload to Cloudflare R2
- **Docker support**: One-command deployment with docker-compose

## Supported Databases

| Database | Rate Limit | Notes |
|----------|-----------|-------|
| Crossref | 40 req/s | Requires email for polite pool |
| PubMed | 9 req/s | NCBI API key recommended |
| Springer | 8 req/s | API key required |
| Elsevier | 5 req/s | Scopus API key required |
| OpenAlex | 9 req/s | Free, polite pool with email |
| MDPI | 9 req/s | Via OpenAlex publisher filter |
| Semantic Scholar | 8 req/s | API key recommended |
| Lens | 8 req/s | API key required |

## Installation

Requires Python 3.10 or higher.

```bash
# Clone the repository
git clone https://github.com/SantiagoSabogall/polymer-data-pipeline.git
cd polymer-data-pipeline

# Install with uv (recommended)
uv sync

# Or with pip
pip install .
```

## Configuration

Copy the example environment file and fill in your API keys:

```bash
cp .env.example API_KEY.env
```

Edit `API_KEY.env` with your keys:

```
# Required for Crossref polite pool
CROSSREF_POLITE_EMAIL=your.email@university.edu

# Optional — increases rate limits
NCBI_EMAIL=your.email@university.edu
PUBMED_API_KEY=your_ncbi_key
SPRINGER_META_API_KEY=your_springer_key
ELSEVIER_API_KEY=your_elsevier_key
OPENALEX_EMAIL=your.email@university.edu
SEMANTIC_SCHOLAR_API_KEY=your_s2_key
LENS_API_KEY=your_lens_key

# Optional — Cloudflare R2 for PDF storage
R2_ACCESS_KEY=your_r2_access_key
R2_SECRET_KEY=your_r2_secret_key
R2_ENDPOINT=https://your_account_id.r2.cloudflarestorage.com
R2_BUCKET_NAME=polymer-papers
```

Keys for Springer, Elsevier, Semantic Scholar, and Lens are optional but significantly increase rate limits. Crossref and PubMed work without keys at reduced rates. R2 is optional — the pipeline works without it.

## Usage

### Web Interface (recommended)

```bash
uv run streamlit run app.py
```

Opens the interactive dashboard at `http://localhost:8501`. From the interface you can:
- Select search mode (presets, free search, or visual builder)
- Choose which databases to query
- Set maximum results per query
- Apply post-search filters (text, year, source, level)
- Select multiple articles in the results table
- Export selected or all results as CSV, BibTeX, or JSON
- Download PDFs locally or upload to Cloudflare R2

### Command Line

```bash
uv run python main.py
```

Runs the full pipeline across all databases and all preset levels. Generates:
- `consolidated_results.json` — Normalized article data
- `consolidated_results.csv` — Spreadsheet format
- `consolidated_results.bib` — BibTeX for LaTeX
- `dashboard.html` — Static HTML dashboard

## Search Modes

### Presets (L1-L4)

Pre-configured searches for polymer research. Select one or more levels:

- **L1 (Blends)**: Polyester blends with barrier properties
- **L2 (Additives)**: Polyester with nanofillers/additives and barrier
- **L3 (Packaging)**: Packaging materials with barrier and polyester
- **L4 (Biodegradable)**: Biopolymers with barrier in packaging

Each level has built-in relevance filtering to reduce noise.

### Free Search

Write boolean queries directly using AND/OR syntax.

**Format:**

```
(grupo1) AND (grupo2) AND (grupo3)
```

Inside each group, terms are joined with OR automatically by the system.

**Examples:**

| Query | What it finds |
|-------|--------------|
| `(polyester OR PET) AND (barrier OR permeability)` | Polyester articles with barrier properties |
| `(PLA OR PHB) AND (food packaging)` | Biopolymers for food packaging |
| `("high oxygen barrier") AND (polyester OR PET)` | Exact phrase + material |
| `(nanoclay OR graphene) AND (polyester) AND (barrier)` | Nanocomposites with barrier |

**Optional filter:** Add comma-separated terms in the filter field to show only articles whose title + abstract contains at least one of those terms. Useful when the query returns too many irrelevant results.

### Visual Builder

Build queries using groups of terms with a GUI. No boolean syntax needed.

1. **Create groups** — Each group represents a concept (material, property, application)
2. **Add terms** — Write synonyms inside each group, one per line
3. **Choose operator** — `AND` (all groups must match) or `OR` (any group matches)
4. **Preview** — See the generated boolean query in real time

**Example — Nanocomposite search:**

| Group | Terms (one per line) |
|-------|----------------------|
| Material | polyester, PET |
| Nanomaterial | nanoclay, graphene, silica |
| Property | barrier, permeability |

With `AND` operator, the generated query is:

```
(polyester OR PET) AND (nanoclay OR graphene OR silica) AND (barrier OR permeability)
```

**Relevance filter:** When enabled, the system checks that at least 2 of your groups appear in each article's title + abstract. This reduces false positives significantly.

### How Queries Translate to Each API

Each API has its own query syntax. The system translates your query automatically:

| Term | Crossref | PubMed | Elsevier | Semantic Scholar |
|------|----------|--------|----------|------------------|
| `polyester` | `polyester*` | `polyester[Title/Abstract]` | `TITLE-ABS-KEY(polyester)` | `polyester` |
| `"high barrier"` | `"high barrier"` | `"high barrier"[Title/Abstract]` | `TITLE-ABS-KEY("high barrier")` | `"high barrier"` |
| `PET` | `PET*` | `PET[Title/Abstract]` | `TITLE-ABS-KEY(PET)` | `PET` |

## Project Structure

```
polymer-data-pipeline/
├── app.py                          # Streamlit web interface
├── main.py                         # CLI entry point
├── API_KEY.env                     # API keys (not tracked)
├── Dockerfile                      # Docker image definition
├── docker-compose.yml              # Docker Compose config
├── .env.example                    # Environment variable template
├── .dockerignore                   # Docker build exclusions
├── .streamlit/config.toml          # Streamlit theme config
├── src/polymer_pipeline/
│   ├── core.py                     # Pipeline orchestration (async)
│   ├── http.py                     # HTTP client with retry/backoff
│   ├── rate_limiter.py             # Per-API rate limiting
│   ├── cache.py                    # JSON file cache with TTL
│   ├── filters.py                  # Title-based relevance filtering
│   ├── dict.py                     # Term lists and boolean queries
│   ├── query_builder.py            # Query translation per API
│   ├── sources.py                  # Database registry and colors
│   ├── settings.py                 # Centralized config and API keys
│   ├── models.py                   # TypedDict definitions
│   ├── downloader.py               # PDF downloader with R2 upload
│   ├── r2_storage.py               # Cloudflare R2 client
│   ├── r2_manage.py                # R2 management functions
│   ├── plots_interactive.py        # Plotly visualizations
│   ├── _plot_common.py             # Shared plot utilities
│   ├── plots.py                    # Matplotlib static plots
│   ├── export.py                   # CSV and BibTeX export
│   ├── dashboard.py                # HTML dashboard generator
│   ├── _dashboard_assets.py        # Dashboard HTML/CSS assets
│   ├── pipeline.py                 # CLI pipeline logic
│   └── fetchers/
│       ├── __init__.py             # Fetcher registry
│       ├── openalex_base.py        # Shared OpenAlex/MDPI logic
│       ├── crossref.py
│       ├── springer.py
│       ├── elsevier.py
│       ├── pubmed.py
│       ├── openalex.py
│       ├── mdpi.py
│       ├── semantic_scholar.py
│       └── lens.py
└── tests/
    ├── test_query_builder.py       # Query construction tests
    ├── test_core.py                # Pipeline orchestration tests
    ├── test_downloader.py          # PDF downloader tests
    └── test_r2_storage.py          # R2 storage tests
```

## Architecture

All fetchers run asynchronously using `aiohttp`. The pipeline uses `asyncio` to query all selected databases concurrently, with per-API rate limiters to avoid being blocked. Failed requests are retried with exponential backoff and jitter.

Results are normalized to a common schema:
```json
{
  "title": "Article title",
  "author": "First author",
  "journal": "Journal name",
  "year": "2024",
  "doi": "10.xxxx/xxxxx",
  "source": "Crossref",
  "abstract": "Full abstract text",
  "pdf_url": "https://...",
  "level": "L1"
}
```

## Data Quality

The pipeline applies relevance filtering based on title keywords. Each search level has specific filter rules:
- **L1 (Blends)**: Requires terms from at least 2 of 3 groups (polyester + barrier + packaging)
- **L2 (Additives)**: Requires additive-related terms
- **L3 (Packaging)**: Requires packaging-specific terminology
- **L4 (Biodegradation)**: Requires biodegradation-related terms

Custom searches bypass these filters or use user-defined rules.

## Deployment

### Streamlit Cloud

1. Push this repository to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repository
4. Set main file path to `app.py`
5. Add your API keys in the Streamlit Cloud settings under "Secrets" using the same format as `API_KEY.env`

### Local with Docker

```bash
docker compose up --build
```

The app will be available at `http://localhost:8501`.

To use Cloudflare R2 for PDF storage, add your R2 credentials to `API_KEY.env` before building.

### Cloudflare R2 Setup

1. Create a Cloudflare R2 bucket named `polymer-papers` (or set `R2_BUCKET_NAME` in your env)
2. Generate R2 API credentials in the Cloudflare dashboard
3. Add the credentials to your `API_KEY.env`:
   ```
   R2_ACCESS_KEY=your_access_key
   R2_SECRET_KEY=your_secret_key
   R2_ENDPOINT=https://your_account_id.r2.cloudflarestorage.com
   R2_BUCKET_NAME=polymer-papers
   ```
4. PDFs will automatically upload to R2 when you use the "Upload to R2" button in the app

## Testing

```bash
# Run all tests
python -m unittest discover -s tests -v

# Run specific test file
python -m unittest tests.test_core -v
```

Tests cover:
- **test_core.py**: Pipeline orchestration, deduplication, filtering, metrics
- **test_downloader.py**: PDF validation, rate limiting, download logic
- **test_r2_storage.py**: R2 client operations, error handling
- **test_query_builder.py**: Boolean query construction and API translation

## License

MIT
