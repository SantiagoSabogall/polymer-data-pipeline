from polymer_pipeline.cache import get_cached, set_cache
from polymer_pipeline.settings import OPENALEX_EMAIL, OPENALEX_API_KEY
from polymer_pipeline.query_builder import build_openalex_query
from polymer_pipeline.fetchers.openalex_base import paginated_fetch

OPENALEX_SLEEP = 0.2


def fetch_openalex(query: str, max_results: int = 100, sleep: float = 0.2,
                    mailto: str | None = None, api_key: str | None = None) -> list:
    """
    mailto: tu correo, para entrar al 'polite pool' de OpenAlex (respuestas más
        rápidas y estables). No es autenticación, es cortesía identificable.
        Por defecto toma OPENALEX_EMAIL de settings/API_KEY.env.
    api_key: opcional. Desde feb-2026 OpenAlex tiene cuota diaria gratuita por
        key en búsquedas con filtro; sin key, sigues teniendo acceso pero con
        prioridad menor. Pásala explícitamente o vía variable de entorno
        OPENALEX_API_KEY — nunca la hardcodees en el código fuente.
    """
    cache_key = f"OpenAlex:{query}"
    cached = get_cached(cache_key)
    if cached is not None:
        print(f"[OpenAlex] Usando cache para: {query[:60]}...")
        return cached

    translated = build_openalex_query(query)

    resolved_mailto = mailto or OPENALEX_EMAIL
    resolved_api_key = api_key or OPENALEX_API_KEY

    normalized, complete = paginated_fetch(
        query=translated,
        max_results=max_results,
        sleep=sleep or OPENALEX_SLEEP,
        mailto=resolved_mailto,
        api_key=resolved_api_key,
        source_label="OpenAlex",
    )

    print(f"[OpenAlex] {len(normalized)} resultados para: {query[:60]}... "
          f"(completo={complete})")

    if complete:
        set_cache(cache_key, normalized)
    else:
        print(f"[OpenAlex] Resultado parcial, no se cachea: {query[:60]}...")

    return normalized
