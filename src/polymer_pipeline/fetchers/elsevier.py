from __future__ import annotations

import logging

from polymer_pipeline.settings import (
    BATCH_SIZE, TOTAL_RESULTS_PER_QUERY,
    SLEEP_BETWEEN_BATCHES, ELSEVIER_API_KEY,
)
from polymer_pipeline.cache import get_cached, set_cache
from polymer_pipeline.query_builder import build_elsevier_query
from polymer_pipeline.http import PageFetcher, make_session
from polymer_pipeline.rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)

URL = "https://api.elsevier.com/content/search/scopus"


async def fetch_elsevier(query: str) -> list[dict]:
    cache_key = f"Elsevier:{query}"
    cached = get_cached(cache_key)
    if cached is not None:
        logger.info("[Elsevier] Usando cache para: %s...", query[:60])
        return cached

    if not ELSEVIER_API_KEY:
        logger.warning("[Elsevier] Saltando: No se configuró ELSEVIER_API_KEY en API_KEY.env")
        return []

    translated = build_elsevier_query(query)

    def build_params(start: int) -> dict:
        return {
            "query": translated,
            "count": BATCH_SIZE,
            "start": start,
        }

    def extract_items(data: dict) -> list[dict]:
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

            abstract = entry.get("dc:description", "")

            pdf_url = ""

            normalized.append({
                "title": title,
                "author": author,
                "journal": journal,
                "year": year,
                "doi": doi,
                "source": "Elsevier",
                "abstract": abstract,
                "pdf_url": pdf_url,
            })
        return normalized

    def extract_total(data: dict) -> int:
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

    headers = {
        "X-ELS-APIKey": ELSEVIER_API_KEY,
        "Accept": "application/json",
    }

    limiter = get_rate_limiter("Elsevier")
    async with limiter:
        async with await make_session() as session:
            session.headers.update(headers)
            normalized = await fetcher.run(session)

            # Leer headers de rate limit de Elsevier
            if hasattr(session, '_response_headers'):
                pass  # Los headers se leen por petición en PageFetcher

    set_cache(cache_key, normalized)
    return normalized
