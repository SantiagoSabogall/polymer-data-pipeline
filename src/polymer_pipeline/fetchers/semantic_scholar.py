"""Fetcher de artículos desde Semantic Scholar.

Semantic Scholar indexa 214M+ papers con abstracts, citation counts,
TLDR summaries y campos de estudio. Con API key gratuita el límite es
1 req/s a través de TODOS los endpoints, así que este fetcher:

- Usa ``/paper/search/bulk`` (recomendada para volúmenes grandes): hasta
  1,000 resultados por respuesta y paginación mediante parámetro ``token``.
- Aplica un throttle global (thread-safe) que garantiza como mínimo
  1 segundo entre peticiones, incluso con varias consultas corriendo en
  paralelo en el pipeline.
- Respeta ``Retry-After`` y aplica backoff exponencial ante 429.
"""

from __future__ import annotations

import logging
import threading
import time

from polymer_pipeline.cache import get_cached, set_cache
from polymer_pipeline.query_builder import build_semanticscholar_query
from polymer_pipeline.http import make_session
from polymer_pipeline.settings import SEMANTIC_SCHOLAR_API_KEY

logger = logging.getLogger(__name__)

SEMANTIC_SCHOLAR_BULK_URL = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
MAX_RETRIES = 5
MIN_REQUEST_INTERVAL = 1.0  # segundos; límite estándar: 1 req/s con API key
FIELDS = "title,abstract,authors,year,venue,externalIds,citationCount,fieldsOfStudy,openAccessPdf"

_throttle_lock = threading.Lock()
_last_request_ts = 0.0


def _throttle() -> None:
    """Garantiza >= MIN_REQUEST_INTERVAL entre peticiones a nivel global.

    El pipeline lanza varias consultas concurrentes contra esta API; sin
    este lock cada hilo dormiría por su cuenta y juntos violarían 1 req/s.
    """
    global _last_request_ts
    with _throttle_lock:
        elapsed = time.monotonic() - _last_request_ts
        if elapsed < MIN_REQUEST_INTERVAL:
            time.sleep(MIN_REQUEST_INTERVAL - elapsed)
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


def fetch_semantic_scholar(query: str, max_results: int = 100) -> list[dict]:
    """Obtiene artículos de Semantic Scholar vía búsqueda masiva (bulk).

    Args:
        query: Consulta booleana genérica (misma sintaxis que otros fetchers).
        max_results: Máximo de resultados a devolver.
    """
    cache_key = f"SemanticScholar:{query}"
    cached = get_cached(cache_key)
    if cached is not None:
        logger.info("[SemanticScholar] Usando cache para: %s...", query[:60])
        return cached

    translated = build_semanticscholar_query(query)

    normalized: list[dict] = []
    token: str | None = None
    retries = 0

    with make_session(backoff_factor=2.0) as session:
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
                _throttle()
                resp = session.get(SEMANTIC_SCHOLAR_BULK_URL, params=params, timeout=30)

                if resp.status_code == 429:
                    retries += 1
                    if retries > MAX_RETRIES:
                        logger.warning("[SemanticScholar] Reintentos agotados. Abortando.")
                        break
                    wait = min(2 ** retries, 60)
                    logger.info("[SemanticScholar] 429. Esperando %ds (intento %d/%d).",
                                wait, retries, MAX_RETRIES)
                    time.sleep(wait)
                    continue

                retries = 0

                if resp.status_code != 200:
                    logger.error("[SemanticScholar] Error %d: %r", resp.status_code, resp.text[:200])
                    break

                data = resp.json()
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
