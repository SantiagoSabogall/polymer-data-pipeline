from __future__ import annotations

import logging

from polymer_pipeline.cache import get_cached, set_cache
from polymer_pipeline.fetchers.openalex_base import paginated_fetch
from polymer_pipeline.query_builder import build_openalex_query
from polymer_pipeline.settings import OPENALEX_API_KEY, OPENALEX_EMAIL

logger = logging.getLogger(__name__)

OPENALEX_SLEEP = 0.2


async def fetch_openalex(
    query: str,
    max_results: int = 100,
    sleep: float = 0.2,
    mailto: str | None = None,
    api_key: str | None = None,
    title_abs_only: bool = False,
) -> list[dict]:
    """Fetch from OpenAlex. mailto for polite pool, api_key for higher quota."""
    cache_key = f"OpenAlex:{query}"
    cached = get_cached(cache_key)
    if cached is not None:
        logger.info("[OpenAlex] Usando cache para: %s...", query[:60])
        return cached

    translated = build_openalex_query(query)

    resolved_mailto = mailto or OPENALEX_EMAIL
    resolved_api_key = api_key or OPENALEX_API_KEY

    normalized, complete = await paginated_fetch(
        query=translated,
        max_results=max_results,
        sleep=sleep or OPENALEX_SLEEP,
        mailto=resolved_mailto,
        api_key=resolved_api_key,
        source_label="OpenAlex",
        title_abs_only=title_abs_only,
    )

    logger.info(
        "[OpenAlex] %d resultados para: %s... (completo=%s)",
        len(normalized), query[:60], complete,
    )

    if complete:
        set_cache(cache_key, normalized)
    else:
        logger.info(
            "[OpenAlex] Resultado parcial, no se cachea: %s...",
            query[:60],
        )

    return normalized
