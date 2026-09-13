"""Lógica compartida asíncrona para fetchers que usan la API de OpenAlex."""

from __future__ import annotations

import asyncio
import logging

from polymer_pipeline.http import make_session, request_with_retry
from polymer_pipeline.rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)

OPENALEX_API_URL = "https://api.openalex.org/works"
MAX_RETRIES = 5
MAX_PER_PAGE = 200


def extract_doi(raw_doi: str) -> str:
    """Normaliza el DOI de OpenAlex."""
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


async def paginated_fetch(
    *,
    query: str,
    max_results: int,
    sleep: float,
    mailto: str | None,
    api_key: str | None,
    source_label: str,
    extra_params: dict | None = None,
    title_abs_only: bool = False,
) -> tuple[list[dict], bool]:
    """Ejecuta una búsqueda paginada por cursor en OpenAlex (async)."""
    normalized: list[dict] = []
    retries = 0
    complete = True
    per_page = min(MAX_PER_PAGE, max_results)
    cursor = "*"

    limiter = get_rate_limiter(source_label)

    async with limiter:
        async with await make_session(timeout=20) as session:
            session.headers.update({
                "User-Agent": f"polymer-pipeline/1.0 (mailto:{mailto or 'unknown'})"
            })

            while len(normalized) < max_results:
                search_key = "title_and_abstract.search" if title_abs_only else "search"
                params: dict = {
                    search_key: query,
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
                    resp = await request_with_retry(
                        session, "GET", OPENALEX_API_URL, params=params,
                        max_retries=3,
                    )

                    if resp is None:
                        logger.warning("[%s] Sin respuesta (cursor=%s)", source_label, cursor)
                        complete = False
                        break

                    if resp.status == 429:
                        retry_after = resp.headers.get("Retry-After", "")
                        try:
                            retry_after_s = int(retry_after)
                        except ValueError:
                            retry_after_s = 0
                        if retry_after_s > 120:
                            logger.warning(
                                "[%s] Cuota diaria agotada en OpenAlex"
                                " (Retry-After=%ds). Abortando.",
                                source_label, retry_after_s,
                            )
                            complete = False
                            break
                        retries += 1
                        if retries > MAX_RETRIES:
                            logger.warning(
                                "[%s] Reintentos agotados (cursor=%s). Abortando.",
                                source_label, cursor,
                            )
                            complete = False
                            break
                        wait = min(2 ** retries, 60) + 0.5
                        logger.info(
                            "[%s] 429. Backoff %ds (intento %d/%d).",
                            source_label, wait, retries, MAX_RETRIES,
                        )
                        await asyncio.sleep(wait)
                        continue

                    retries = 0

                    if resp.status != 200:
                        logger.error(
                            "[%s] Error %d (cursor=%s).",
                            source_label, resp.status, cursor,
                        )
                        complete = False
                        break

                    data = await resp.json()
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

                    await asyncio.sleep(sleep)

                except Exception as e:
                    logger.error(
                        "[%s] Excepción (cursor=%s): %s: %s",
                        source_label, cursor, type(e).__name__, e,
                    )
                    complete = False
                    break

    return normalized, complete
