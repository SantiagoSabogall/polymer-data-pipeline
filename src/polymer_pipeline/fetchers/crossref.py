from polymer_pipeline.settings import (
    TOTAL_RESULTS_PER_QUERY,
    SLEEP_BETWEEN_BATCHES, CROSSREF_EMAIL,
)
from polymer_pipeline.cache import get_cached, set_cache
from polymer_pipeline.query_builder import build_crossref_query
from polymer_pipeline.http import PageFetcher, make_session
import re

URL = "https://api.crossref.org/works"

# Crossref polite pool: ~50 req/s. Optimizado para máximo rendimiento.
CROSSREF_BATCH_SIZE = 100
CROSSREF_SLEEP = 0.1


def _strip_jats_tags(text: str) -> str:
    """Elimina tags JATS/XML del abstract (ej: <jats:p>, <jats:sec>)."""
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


def fetch_crossref(query):
    cache_key = f"Crossref:{query}"
    cached = get_cached(cache_key)
    if cached is not None:
        print(f"[Crossref] Usando cache para: {query[:60]}...")
        return cached

    translated = build_crossref_query(query)
    headers = {
        "User-Agent": f"PolymerDataPipeline/1.0 (mailto:{CROSSREF_EMAIL})"
    }

    def build_params(start):
        return {
            "query": translated,
            "rows": CROSSREF_BATCH_SIZE,
            "offset": start,
        }

    def extract_items(data):
        items = data.get("message", {}).get("items", [])
        normalized = []
        for item in items:
            title = item.get("title", [""])[0] if item.get("title") else "Sin título"
            doi = item.get("DOI", "").lower().strip()
            journal = item.get("container-title", [""])[0] if item.get("container-title") else "No disponible"

            authors = item.get("author", [])
            author = "Desconocido"
            if authors:
                given = authors[0].get("given", "")
                family = authors[0].get("family", "")
                author = f"{given} {family}".strip() or "Desconocido"

            year = ""
            if "published-print" in item:
                year = str(item["published-print"]["date-parts"][0][0])
            elif "published-online" in item:
                year = str(item["published-online"]["date-parts"][0][0])

            abstract = _strip_jats_tags(item.get("abstract", ""))

            pdf_url = ""
            for link in item.get("link", []):
                ct = link.get("content-type", "")
                if "pdf" in ct.lower():
                    pdf_url = link.get("URL", "")
                    break

            normalized.append({
                "title": title,
                "author": author,
                "journal": journal,
                "year": year,
                "doi": doi,
                "source": "Crossref",
                "abstract": abstract,
                "pdf_url": pdf_url,
            })
        return normalized

    def extract_total(data):
        return data.get("message", {}).get("total-results", 0)

    fetcher = PageFetcher(
        url=URL,
        batch_size=CROSSREF_BATCH_SIZE,
        sleep_between=CROSSREF_SLEEP,
        total_limit=TOTAL_RESULTS_PER_QUERY,
        build_params=build_params,
        extract_items=extract_items,
        extract_total=extract_total,
        name="Crossref",
    )

    with make_session() as session:
        session.headers.update(headers)
        normalized = fetcher.run(session)

    set_cache(cache_key, normalized)
    return normalized