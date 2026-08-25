"""Fetcher de artículos MDPI a través de la API OpenAlex.

MDPI no ofrece API propia; este fetcher consulta OpenAlex filtrando por el
publisher MDPI (ID: P4310310987). Reutiliza la paginación por cursor del
módulo compartido ``openalex_base``.
"""

from polymer_pipeline.cache import get_cached, set_cache
from polymer_pipeline.settings import OPENALEX_EMAIL, OPENALEX_API_KEY
from polymer_pipeline.query_builder import build_openalex_query
from polymer_pipeline.fetchers.openalex_base import paginated_fetch

MDPI_PUBLISHER_ID = "https://openalex.org/P4310310987"
MDPI_SLEEP = 0.2


def fetch_mdpi(query: str, max_results: int = 100, sleep: float = 0.2,
               mailto: str | None = None, api_key: str | None = None) -> list:
    """Obtiene artículos de MDPI vía OpenAlex con filtro de publisher.

    Args:
        query: Consulta booleana genérica (misma sintaxis que otros fetchers).
        max_results: Máximo de resultados a devolver.
        sleep: Pausa entre páginas (segundos).
        mailto: Email para polite pool de OpenAlex.
        api_key: API key opcional de OpenAlex.
    """
    cache_key = f"MDPI:{query}"
    cached = get_cached(cache_key)
    if cached is not None:
        print(f"[MDPI] Usando cache para: {query[:60]}...")
        return cached

    translated = build_openalex_query(query)

    resolved_mailto = mailto or OPENALEX_EMAIL
    resolved_api_key = api_key or OPENALEX_API_KEY

    normalized, complete = paginated_fetch(
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

    print(f"[MDPI] {len(normalized)} resultados para: {query[:60]}... "
          f"(completo={complete})")

    if complete:
        set_cache(cache_key, normalized)
    else:
        print(f"[MDPI] Resultado parcial, no se cachea: {query[:60]}...")

    return normalized
