"""Fetcher de artículos desde Semantic Scholar (async)."""

from __future__ import annotations

import asyncio
import logging
import time

from polymer_pipeline.cache import get_cached, set_cache
from polymer_pipeline.http import make_session, request_with_retry
from polymer_pipeline.query_builder import build_semanticscholar_query
from polymer_pipeline.rate_limiter import get_rate_limiter
from polymer_pipeline.settings import SEMANTIC_SCHOLAR_API_KEY

logger = logging.getLogger(__name__)

SEMANTIC_SCHOLAR_BULK_URL = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
MAX_RETRIES = 5
MIN_REQUEST_INTERVAL = 1.0
FIELDS = "title,abstract,authors,year,venue,externalIds,citationCount,fieldsOfStudy,openAccessPdf"

_last_request_ts = 0.0


async def _throttle() -> None:
    """Garantiza >= MIN_REQUEST_INTERVAL entre peticiones (async-safe, sin lock)."""
    global _last_request_ts
    elapsed = time.monotonic() - _last_request_ts
    if elapsed < MIN_REQUEST_INTERVAL:
        await asyncio.sleep(MIN_REQUEST_INTERVAL - elapsed)
    _last_request_ts = time.monotonic()


def _normalize_paper(paper: dict) -> dict:
    authors = paper.get("authors") or []
    external_ids = paper.get("externalIds") or {}
    open_access_pdf = paper.get("openAccessPdf") or {}
    return {
        "title": paper.get("title") or "Sin título",
        "author": authors[0].get("name", "Desconocido") if authors else "Desconocido",
        "journal": paper.get("venue") or "",
        "year": str(paper["year"]) if paper.get("year") else "",
        "doi": (external_ids.get("DOI") or "").lower().strip(),
        "source": "SemanticScholar",
        "abstract": paper.get("abstract") or "",
        "pdf_url": open_access_pdf.get("url") or "",
    }


async def fetch_semantic_scholar(query: str, max_results: int = 100) -> list[dict]:
    """Obtiene artículos de Semantic Scholar vía búsqueda masiva (bulk, async)."""
    cache_key = f"SemanticScholar:{query}"
    cached = get_cached(cache_key)
    if cached is not None:
        logger.info("[SemanticScholar] Usando cache para: %s...", query[:60])
        return cached

    translated = build_semanticscholar_query(query)

    normalized: list[dict] = []
    token: str | None = None
    retries = 0

    limiter = get_rate_limiter("SemanticScholar")

    async with limiter:
        async with await make_session(timeout=30) as session:
            session.headers.update({"User-Agent": "polymer-pipeline/1.0"})
            if SEMANTIC_SCHOLAR_API_KEY:
                session.headers.update({"x-api-key": SEMANTIC_SCHOLAR_API_KEY})

            while len(normalized) < max_results:
                params: dict = {
                    "query": translated,
                    "fields": FIELDS,
                    "limit": min(max_results - len(normalized), 1000),
                }
                if token:
                    params["token"] = token

                try:
                    await _throttle()
                    resp = await request_with_retry(
                        session, "GET", SEMANTIC_SCHOLAR_BULK_URL,
                        params=params, max_retries=3,
                    )

                    if resp is None:
                        logger.warning("[SemanticScholar] Sin respuesta. Abortando.")
                        break

                    if resp.status == 429:
                        retries += 1
                        if retries > MAX_RETRIES:
                            logger.warning("[SemanticScholar] Reintentos agotados. Abortando.")
                            break
                        wait = min(2 ** retries, 60) + 0.5
                        logger.info(
                            "[SemanticScholar] 429. Esperando %ds"
                            " (intento %d/%d).",
                            wait, retries, MAX_RETRIES,
                        )
                        await asyncio.sleep(wait)
                        continue

                    retries = 0

                    if resp.status != 200:
                        logger.error(
                            "[SemanticScholar] Error %d: %r",
                            resp.status, (await resp.text())[:200],
                        )
                        break

                    data = await resp.json()
                    results = data.get("data") or []
                    normalized.extend(_normalize_paper(p) for p in results)

                    token = data.get("token")
                    if not token or not results:
                        break

                except Exception as e:
                    logger.error("[SemanticScholar] Excepción: %s: %s", type(e).__name__, e)
                    break

    normalized = normalized[:max_results]
    logger.info("[SemanticScholar] %d resultados para: %s...", len(normalized), query[:60])

    if normalized:
        set_cache(cache_key, normalized)
    return normalized
