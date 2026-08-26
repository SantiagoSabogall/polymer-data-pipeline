# Polymer Data Pipeline

Scientific literature aggregation system for polymer and packaging research. Queries 8 academic databases in parallel, deduplicates results, and provides an interactive dashboard for exploration and export.

## Overview

This tool automates the systematic review process for polymer science research. It searches multiple academic APIs simultaneously, normalizes the results into a common format, applies relevance filters, and presents everything through a web interface with filtering, visualization, and export capabilities.

The pipeline supports three search modes:
- **Presets**: Pre-configured searches across 4 research levels (blends, additives, packaging, biodegradation)
- **Free search**: Custom boolean queries with full control over search terms
- **Visual builder**: GUI-based query construction for users unfamiliar with boolean syntax

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
pip install -e .
```

## Configuration

Create an `API_KEY.env` file in the project root with your API keys:

```
CROSSREF_EMAIL=your.email@university.edu
SPRINGER_META_API_KEY=your_springer_key
ELSEVIER_API_KEY=your_elsevier_key
SEMANTIC_SCHOLAR_API_KEY=your_s2_key
LENS_API_KEY=your_lens_key
PUBMED_API_KEY=your_ncbi_key
```

Keys for Springer, Elsevier, Semantic Scholar, and Lens are optional but significantly increase rate limits. Crossref and PubMed work without keys at reduced rates.

## Usage

### Web Interface (recommended)

```bash
uv run streamlit run app.py
```

Opens the interactive dashboard at `http://localhost:8501`. From the sidebar you can:
- Select search mode (presets, free search, or visual builder)
- Choose which databases to query
- Set maximum results per query
- Apply post-search filters (text, year, source, level)
- Export filtered results as CSV, BibTeX, or JSON

### Command Line

```bash
uv run python main.py
```

Runs the full pipeline across all databases and all preset levels. Generates:
- `consolidated_results.json` - Normalized article data
- `consolidated_results.csv` - Spreadsheet format
- `consolidated_results.bib` - BibTeX for LaTeX
- `dashboard.html` - Static HTML dashboard

## Project Structure

```
polymer-data-pipeline/
├── app.py                          # Streamlit web interface
├── main.py                         # CLI entry point
├── API_KEY.env                     # API keys (not tracked)
├── src/polymer_pipeline/
│   ├── core.py                     # Pipeline orchestration (async)
│   ├── http.py                     # HTTP client with retry/backoff
│   ├── rate_limiter.py             # Per-API rate limiting
│   ├── cache.py                    # JSON file cache with TTL
│   ├── filters.py                  # Title-based relevance filtering
│   ├── dict.py                     # Term lists and boolean queries
│   ├── query_builder.py            # Query translation per API
│   ├── sources.py                  # Database registry and colors
│   ├── models.py                   # TypedDict definitions
│   ├── plots_interactive.py        # Plotly visualizations
│   ├── export.py                   # CSV and BibTeX export
│   ├── pipeline.py                 # CLI pipeline logic
│   └── fetchers/
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
    └── test_query_builder.py       # Unit tests for query construction
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

## Testing

```bash
uv run pytest tests/ -v
```

## License

MIT
