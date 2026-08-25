"""Lógica compartida para fetchers que usan la API de OpenAlex.

OpenAlex y MDPI comparten la misma paginación por cursor, normalización
de DOI y reconstrucción de abstracts. Este módulo evita duplicación.
"""

from __future__ import annotations

import time

from polymer_pipeline.http import make_session

OPENALEX_API_URL = "https://api.openalex.org/works"
MAX_RETRIES = 5
MAX_PER_PAGE = 200


def extract_doi(raw_doi: str) -> str:
    """Normaliza el DOI de OpenAlex (URL completa) a solo el identificador."""
    if not raw_doi:
        return ""
    return raw_doi.replace("https://doi.org/", "").lower().strip()


def reconstruct_abstract(inverted_index: dict | None) -> str:
    """Reconstruye el abstract a partir del índice invertido de OpenAlex."""
    if not inverted_index:
        return ""
    word_positions: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort(key=lambda x: x[0])
    return " ".join(word for _, word in word_positions)


def normalize_work(work: dict, source_label: str) -> dict:
    """Normaliza un work de OpenAlex al formato estándar del pipeline."""
    title = work.get("title") or work.get("display_name") or "Sin título"
    doi = extract_doi(work.get("doi", ""))

    authorships = work.get("authorships", [])
    author = "Desconocido"
    if authorships:
        author_obj = authorships[0].get("author", {})
        author = author_obj.get("display_name", "Desconocido")

    primary_location = work.get("primary_location") or {}
    loc_source = primary_location.get("source") or {}
    journal = loc_source.get("display_name", "Desconocido")

    year = work.get("publication_year", "")
    abstract = reconstruct_abstract(work.get("abstract_inverted_index"))

    pdf_url = ""
    oa = work.get("open_access") or {}
    pdf_url = oa.get("oa_url", "") or ""
    if not pdf_url:
        best_loc = work.get("best_oa_location") or {}
        pdf_url = best_loc.get("pdf_url", "") or ""

    return {
        "title": title,
        "author": author,
        "journal": journal,
        "year": str(year) if year else "",
        "doi": doi,
        "source": source_label,
        "abstract": abstract,
        "pdf_url": pdf_url,
    }


def paginated_fetch(
    *,
    query: str,
    max_results: int,
    sleep: float,
    mailto: str | None,
    api_key: str | None,
    source_label: str,
    extra_params: dict | None = None,
) -> tuple[list[dict], bool]:
    """Ejecuta una búsqueda paginada por cursor en OpenAlex.

    Devuelve (resultados, es_completo).
    """
    normalized: list[dict] = []
    retries = 0
    complete = True
    per_page = min(MAX_PER_PAGE, max_results)
    cursor = "*"

    with make_session(backoff_factor=2.0) as session:
        session.headers.update({
            "User-Agent": f"polymer-pipeline/1.0 (mailto:{mailto or 'unknown'})"
        })

        while len(normalized) < max_results:
            params: dict = {
                "search": query,
                "per_page": per_page,
                "cursor": cursor,
            }
            if mailto:
                params["mailto"] = mailto
            if api_key:
                params["api_key"] = api_key
            if extra_params:
                params.update(extra_params)

            try:
                resp = session.get(OPENALEX_API_URL, params=params, timeout=20)

                if resp.status_code == 429:
                    retry_after = resp.headers.get("Retry-After", "")
                    try:
                        retry_after_s = int(retry_after)
                    except ValueError:
                        retry_after_s = 0
                    if retry_after_s > 120:
                        print(f"[{source_label}] Cuota diaria agotada en OpenAlex "
                              f"(Retry-After={retry_after_s}s = {retry_after_s // 3600}h). "
                              f"Abortando query.")
                        complete = False
                        break
                    retries += 1
                    if retries > MAX_RETRIES:
                        print(f"[{source_label}] Reintentos agotados (cursor={cursor}). "
                              f"Abortando query.")
                        complete = False
                        break
                    wait = min(2 ** retries, 60)
                    print(f"[{source_label}] 429. Backoff {wait}s "
                          f"(intento {retries}/{MAX_RETRIES}).")
                    time.sleep(wait)
                    continue

                retries = 0

                if resp.status_code != 200:
                    print(f"[{source_label}] Error {resp.status_code} (cursor={cursor}). "
                          f"Cuerpo: {resp.text[:200]!r}")
                    complete = False
                    break

                data = resp.json()
                results = data.get("results", [])
                if not results:
                    break

                for work in results:
                    normalized.append(normalize_work(work, source_label))
                    if len(normalized) >= max_results:
                        break

                cursor = data.get("meta", {}).get("next_cursor")
                if not cursor:
                    break

                time.sleep(sleep)

            except Exception as e:
                print(f"[{source_label}] Excepción (cursor={cursor}): "
                      f"{type(e).__name__}: {e}")
                complete = False
                break

    return normalized, complete
