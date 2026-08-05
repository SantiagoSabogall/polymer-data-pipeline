from polymer_pipeline.settings import (
    BATCH_SIZE, TOTAL_RESULTS_PER_QUERY,
    SLEEP_BETWEEN_BATCHES, ELSEVIER_API_KEY,
)
from polymer_pipeline.cache import get_cached, set_cache
from polymer_pipeline.query_builder import build_elsevier_query
from polymer_pipeline.http import PageFetcher, make_session

URL = "https://api.elsevier.com/content/search/scopus"
HEADERS = {
    "X-ELS-APIKey": ELSEVIER_API_KEY,
    "Accept": "application/json",
}


def fetch_elsevier(query):
    cache_key = f"Elsevier:{query}"
    cached = get_cached(cache_key)
    if cached is not None:
        print(f"[Elsevier] Usando cache para: {query[:60]}...")
        return cached

    if not ELSEVIER_API_KEY:
        print("[Elsevier] Saltando: No se configuró ELSEVIER_API_KEY en API_KEY.env")
        return []

    translated = build_elsevier_query(query)

    def build_params(start):
        return {
            "query": translated,
            "count": BATCH_SIZE,
            "start": start,
        }

    def extract_items(data):
        entries = data.get("search-results", {}).get("entry", [])
        if not entries or "error" in entries[0]:
            return []
        normalized = []
        for entry in entries:
            title = entry.get("dc:title", "Sin título")
            author = entry.get("dc:creator", "Desconocido")
            journal = entry.get("prism:publicationName", "No disponible")

            cover_date = entry.get("prism:coverDate", "")
            year = cover_date[:4] if cover_date else ""

            doi = entry.get("prism:doi", "").lower().strip()

            normalized.append({
                "title": title,
                "author": author,
                "journal": journal,
                "year": year,
                "doi": doi,
                "source": "Elsevier",
            })
        return normalized

    def extract_total(data):
        return int(data.get("search-results", {}).get("opensearch:totalResults", 0))

    fetcher = PageFetcher(
        url=URL,
        batch_size=BATCH_SIZE,
        sleep_between=SLEEP_BETWEEN_BATCHES,
        total_limit=TOTAL_RESULTS_PER_QUERY,
        build_params=build_params,
        extract_items=extract_items,
        extract_total=extract_total,
        name="Elsevier",
    )

    with make_session() as session:
        session.headers.update(HEADERS)
        normalized = fetcher.run(session)

    set_cache(cache_key, normalized)
    return normalized