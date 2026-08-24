"""Fetcher de artículos MDPI a través de la API OpenAlex.

MDPI no ofrece API propia; este fetcher consulta OpenAlex filtrando por el
publisher MDPI (ID: P4310310987). Reutiliza la misma paginación por cursor
y normalización que el fetcher de OpenAlex, pero con filtro de publisher
integrado e cache independiente.
"""

import time
from polymer_pipeline.cache import get_cached, set_cache
from polymer_pipeline.settings import OPENALEX_EMAIL, OPENALEX_API_KEY
from polymer_pipeline.query_builder import build_openalex_query
from polymer_pipeline.http import make_session

OPENALEX_API_URL = "https://api.openalex.org/works"
MDPI_PUBLISHER_ID = "https://openalex.org/P4310310987"
MAX_RETRIES = 5
MAX_PER_PAGE = 200

# MDPI usa OpenAlex API: ~10 req/s. 0.2s entre requests.
MDPI_SLEEP = 0.2


def _extract_doi(raw_doi: str) -> str:
    """Normaliza el DOI de OpenAlex (URL completa) a solo el identificador."""
    if not raw_doi:
        return ""
    return raw_doi.replace("https://doi.org/", "").lower().strip()


def _reconstruct_abstract(inverted_index: dict | None) -> str:
    """Reconstruye el abstract a partir del índice invertido de OpenAlex."""
    if not inverted_index:
        return ""
    word_positions = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort(key=lambda x: x[0])
    return " ".join(word for _, word in word_positions)


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

    query = build_openalex_query(query)

    mailto = mailto or OPENALEX_EMAIL
    api_key = api_key or OPENALEX_API_KEY

    normalized = []
    retries = 0
    complete = True
    per_page = min(MAX_PER_PAGE, max_results)
    cursor = "*"

    with make_session(backoff_factor=2.0) as session:
        session.headers.update({
            "User-Agent": "polymer-pipeline/1.0 (mailto:%s)" % (mailto or "unknown")
        })

        while len(normalized) < max_results:
            params = {
                "search": query,
                "per_page": per_page,
                "cursor": cursor,
                "filter": f"primary_location.source.host_organization:{MDPI_PUBLISHER_ID}",
            }
            if mailto:
                params["mailto"] = mailto
            if api_key:
                params["api_key"] = api_key

            try:
                resp = session.get(OPENALEX_API_URL, params=params, timeout=20)

                if resp.status_code == 429:
                    retry_after = resp.headers.get("Retry-After", "")
                    try:
                        retry_after_s = int(retry_after)
                    except ValueError:
                        retry_after_s = 0
                    if retry_after_s > 120:
                        print(f"[MDPI] Cuota diaria agotada en OpenAlex (Retry-After={retry_after_s}s "
                              f"= {retry_after_s // 3600}h). Abortando query. Reintenta mañana o "
                              f"configura OPENALEX_API_KEY.")
                        complete = False
                        break
                    retries += 1
                    if retries > MAX_RETRIES:
                        print(f"[MDPI] Reintentos agotados (cursor={cursor}). Abortando query.")
                        complete = False
                        break
                    wait = min(2 ** retries, 60)
                    print(f"[MDPI] 429. Backoff {wait}s (intento {retries}/{MAX_RETRIES}).")
                    time.sleep(wait)
                    continue

                retries = 0

                if resp.status_code != 200:
                    print(f"[MDPI] Error {resp.status_code} (cursor={cursor}). "
                          f"Cuerpo: {resp.text[:200]!r}")
                    complete = False
                    break

                data = resp.json()
                results = data.get("results", [])
                if not results:
                    break

                for work in results:
                    title = work.get("title") or work.get("display_name") or "Sin título"
                    doi = _extract_doi(work.get("doi", ""))

                    authorships = work.get("authorships", [])
                    author = "Desconocido"
                    if authorships:
                        author_obj = authorships[0].get("author", {})
                        author = author_obj.get("display_name", "Desconocido")

                    primary_location = work.get("primary_location") or {}
                    source = primary_location.get("source") or {}
                    journal = source.get("display_name", "Desconocido")

                    year = work.get("publication_year", "")

                    abstract = _reconstruct_abstract(work.get("abstract_inverted_index"))

                    pdf_url = ""
                    oa = work.get("open_access") or {}
                    pdf_url = oa.get("oa_url", "") or ""
                    if not pdf_url:
                        best_loc = work.get("best_oa_location") or {}
                        pdf_url = best_loc.get("pdf_url", "") or ""

                    normalized.append({
                        "title": title,
                        "author": author,
                        "journal": journal,
                        "year": str(year) if year else "",
                        "doi": doi,
                        "source": "MDPI",
                        "abstract": abstract,
                        "pdf_url": pdf_url,
                    })

                    if len(normalized) >= max_results:
                        break

                cursor = data.get("meta", {}).get("next_cursor")
                if not cursor:
                    break

                time.sleep(sleep)

            except Exception as e:
                print(f"[MDPI] Excepción (cursor={cursor}): {type(e).__name__}: {e}")
                complete = False
                break

    print(f"[MDPI] {len(normalized)} resultados para: {query[:60]}... (completo={complete})")

    if complete:
        set_cache(cache_key, normalized)
    else:
        print(f"[MDPI] Resultado parcial, no se cachea: {query[:60]}...")

    return normalized
