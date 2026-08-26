"""Fetcher de artículos MDPI a través de la API OpenAlex (async)."""

from __future__ import annotations

import logging

from polymer_pipeline.cache import get_cached, set_cache
from polymer_pipeline.settings import OPENALEX_EMAIL, OPENALEX_API_KEY
from polymer_pipeline.query_builder import build_openalex_query
from polymer_pipeline.fetchers.openalex_base import paginated_fetch

logger = logging.getLogger(__name__)

MDPI_PUBLISHER_ID = "https://openalex.org/P4310310987"
MDPI_SLEEP = 0.2


async def fetch_mdpi(query: str, max_results: int = 100, sleep: float = 0.2,
               mailto: str | None = None, api_key: str | None = None) -> list[dict]:
    """Obtiene artículos de MDPI vía OpenAlex con filtro de publisher."""
    cache_key = f"MDPI:{query}"
    cached = get_cached(cache_key)
    if cached is not None:
        logger.info("[MDPI] Usando cache para: %s...", query[:60])
        return cached

    translated = build_openalex_query(query)

    resolved_mailto = mailto or OPENALEX_EMAIL
    resolved_api_key = api_key or OPENALEX_API_KEY

    normalized, complete = await paginated_fetch(
        query=translated,
        max_results=max_results,
        sleep=sleep or MDPI_SLEEP,
        mailto=resolved_mailto,
        api_key=resolved_api_key,
        source_label="MDPI",
        extra_params={
            "filter": f"primary_location.source.host_organization:{MDPI_PUBLISHER_ID}",
        },
    )

    logger.info("[MDPI] %d resultados para: %s... (completo=%s)", len(normalized), query[:60], complete)

    if complete:
        set_cache(cache_key, normalized)
    else:
        logger.info("[MDPI] Resultado parcial, no se cachea: %s...", query[:60])

    return normalized
