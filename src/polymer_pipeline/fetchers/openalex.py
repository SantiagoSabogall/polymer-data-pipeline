import time
from polymer_pipeline.cache import get_cached, set_cache
from polymer_pipeline.settings import OPENALEX_EMAIL, OPENALEX_API_KEY
from polymer_pipeline.query_builder import build_openalex_query
from polymer_pipeline.http import make_session

OPENALEX_API_URL = "https://api.openalex.org/works"
MAX_RETRIES = 5
MAX_PER_PAGE = 200  # límite duro impuesto por OpenAlex


def _extract_doi(raw_doi: str) -> str:
    """OpenAlex devuelve el DOI como URL completa (https://doi.org/10.xxxx).
    Lo normalizamos a solo el identificador para que sea comparable con el
    DOI que devuelven Crossref/PubMed en tu pipeline (misma clave de dedup)."""
    if not raw_doi:
        return ""
    return raw_doi.replace("https://doi.org/", "").lower().strip()


def _reconstruct_abstract(inverted_index: dict | None) -> str:
    """Reconstruye el abstract a partir del índice invertido de OpenAlex.

    OpenAlex almacena el abstract como un dict donde las keys son palabras
    y los values son listas de posiciones. Esta función reconstruye el texto
    original ordenando por posición.
    """
    if not inverted_index:
        return ""
    word_positions = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort(key=lambda x: x[0])
    return " ".join(word for _, word in word_positions)


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

    query = build_openalex_query(query)

    mailto = mailto or OPENALEX_EMAIL
    api_key = api_key or OPENALEX_API_KEY

    normalized = []
    retries = 0
    complete = True
    per_page = min(MAX_PER_PAGE, max_results)
    cursor = "*"  # OpenAlex exige paginación por cursor para recorridos completos;
                  # offset+page se rompe (error 403) pasado el resultado #10,000.

    with make_session(backoff_factor=2.0) as session:
        session.headers.update({"User-Agent": "polymer-pipeline/1.0 (mailto:%s)" % (mailto or "unknown")})

        while len(normalized) < max_results:
            params = {
                "search": query,
                "per_page": per_page,
                "cursor": cursor,
            }
            if mailto:
                params["mailto"] = mailto
            if api_key:
                params["api_key"] = api_key

            try:
                resp = session.get(OPENALEX_API_URL, params=params, timeout=20)

                if resp.status_code == 429:
                    retries += 1
                    if retries > MAX_RETRIES:
                        print(f"[OpenAlex] Reintentos agotados (cursor={cursor}). Abortando query.")
                        complete = False
                        break
                    wait = 2 ** retries
                    print(f"[OpenAlex] 429. Backoff {wait}s (intento {retries}/{MAX_RETRIES}).")
                    time.sleep(wait)
                    continue

                retries = 0

                if resp.status_code != 200:
                    print(f"[OpenAlex] Error {resp.status_code} (cursor={cursor}). "
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

                    normalized.append({
                        "title": title,
                        "author": author,
                        "journal": journal,
                        "year": str(year) if year else "",
                        "doi": doi,
                        "source": "OpenAlex",
                        "abstract": abstract,
                    })

                    if len(normalized) >= max_results:
                        break

                cursor = data.get("meta", {}).get("next_cursor")
                if not cursor:
                    break  # no hay más páginas

                time.sleep(sleep)

            except Exception as e:
                print(f"[OpenAlex] Excepción (cursor={cursor}): {type(e).__name__}: {e}")
                complete = False
                break

    print(f"[OpenAlex] {len(normalized)} resultados para: {query[:60]}... (completo={complete})")

    if complete:
        set_cache(cache_key, normalized)
    else:
        print(f"[OpenAlex] Resultado parcial, no se cachea: {query[:60]}...")

    return normalized
