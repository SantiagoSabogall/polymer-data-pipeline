from __future__ import annotations

import logging

from polymer_pipeline.settings import (
    BATCH_SIZE, TOTAL_RESULTS_PER_QUERY,
    SLEEP_BETWEEN_BATCHES, SPRINGER_API_KEY,
)
from polymer_pipeline.cache import get_cached, set_cache
from polymer_pipeline.query_builder import build_springer_query
from polymer_pipeline.http import PageFetcher, make_session
from polymer_pipeline.rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)

URL = "https://api.springernature.com/meta/v2/json"


async def fetch_springer(query: str) -> list[dict]:
    cache_key = f"Springer:{query}"
    cached = get_cached(cache_key)
    if cached is not None:
        logger.info("[Springer] Usando cache para: %s...", query[:60])
        return cached

    if not SPRINGER_API_KEY:
        logger.warning("[Springer] Saltando: No se configuró SPRINGER_META_API_KEY en API_KEY.env")
        return []

    translated = build_springer_query(query)

    def build_params(start: int) -> dict:
        return {
            "q": translated,
            "p": BATCH_SIZE,
            "s": start,
            "api_key": SPRINGER_API_KEY,
        }

    def extract_items(data: dict) -> list[dict]:
        records = data.get("records", [])
        normalized = []
        for record in records:
            title = record.get("title", "Sin título")
            doi = record.get("doi", "").lower().strip()
            journal = record.get("publicationName", "No disponible")

            creators = record.get("creators", [])
            author = creators[0].get("creator", "Desconocido") if creators else "Desconocido"

            pub_date = record.get("publicationDate", "")
            year = pub_date[:4] if pub_date else ""

            abstract = record.get("abstract", "")

            pdf_url = ""
            for u in record.get("url", []):
                if isinstance(u, dict) and "pdf" in u.get("format", "").lower():
                    pdf_url = u.get("value", "")
                    break

            normalized.append({
                "title": title,
                "author": author,
                "journal": journal,
                "year": year,
                "doi": doi,
                "source": "Springer",
                "abstract": abstract,
                "pdf_url": pdf_url,
            })
        return normalized

    def extract_total(data: dict) -> int:
        result_info = data.get("result", [{}])
        return int(result_info[0].get("total", 0)) if result_info else 0

    fetcher = PageFetcher(
        url=URL,
        batch_size=BATCH_SIZE,
        sleep_between=SLEEP_BETWEEN_BATCHES,
        total_limit=TOTAL_RESULTS_PER_QUERY,
        build_params=build_params,
        extract_items=extract_items,
        extract_total=extract_total,
        name="Springer",
        initial_start=1,
    )

    limiter = get_rate_limiter("Springer")
    async with limiter:
        async with await make_session() as session:
            normalized = await fetcher.run(session)

    set_cache(cache_key, normalized)
    return normalized
