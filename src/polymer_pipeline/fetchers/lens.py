"""Fetcher de artículos desde Lens.org.

Lens.org es la única fuente que vincula papers con patentes.
API gratuita para uso académico. Requiere API key (registro gratis
con justificación de uso).
"""

from __future__ import annotations

import logging
import time

from polymer_pipeline.cache import get_cached, set_cache
from polymer_pipeline.settings import LENS_API_KEY
from polymer_pipeline.query_builder import build_lens_query
from polymer_pipeline.http import make_session

logger = logging.getLogger(__name__)

LENS_API_URL = "https://api.lens.org/scholarly/search"

# Lens.org: ~10 req/s. Máximo 1000 por request.
LENS_MAX_SIZE = 1000


def fetch_lens(query: str, max_results: int = 100) -> list[dict]:
    """Obtiene artículos de Lens.org con vinculación papers-patentes.

    Args:
        query: Consulta booleana genérica (misma sintaxis que otros fetchers).
        max_results: Máximo de resultados a devolver.
    """
    cache_key = f"Lens:{query}"
    cached = get_cached(cache_key)
    if cached is not None:
        logger.info("[Lens] Usando cache para: %s...", query[:60])
        return cached

    if not LENS_API_KEY:
        logger.warning("[Lens] Saltando: No se configuró LENS_API_KEY en API_KEY.env")
        return []

    translated = build_lens_query(query)

    headers = {
        "Authorization": f"Bearer {LENS_API_KEY}",
        "Content-Type": "application/json"
    }

    body = {
        "query": {
            "query_string": {
                "query": translated,
                "default_operator": "and"
            }
        },
        "size": min(max_results, LENS_MAX_SIZE),
        "include": [
            "lens_id", "title", "abstract", "authors", "year_published",
            "source", "external_ids", "scholarly_citations_count",
            "patent_citations_count", "open_access"
        ]
    }

    normalized: list[dict] = []
    retries = 0
    max_retries = 3

    with make_session(backoff_factor=2.0) as session:
        while len(normalized) < max_results:
            try:
                resp = session.post(
                    LENS_API_URL,
                    json=body,
                    headers=headers,
                    timeout=30
                )

                if resp.status_code == 429:
                    retries += 1
                    if retries > max_retries:
                        logger.warning("[Lens] Reintentos agotados. Abortando.")
                        break
                    retry_after = int(resp.headers.get("x-rate-limit-retry-after-seconds", 10))
                    logger.info("[Lens] 429. Esperando %ds (intento %d/%d).",
                                retry_after, retries, max_retries)
                    time.sleep(retry_after)
                    continue

                retries = 0

                if resp.status_code != 200:
                    logger.error("[Lens] Error %d: %r", resp.status_code, resp.text[:200])
                    break

                data = resp.json()
                results = data.get("data", [])
                if not results:
                    break

                for doc in results:
                    if not isinstance(doc, dict):
                        continue

                    title = doc.get("title") or "Sin título"
                    if isinstance(title, list):
                        title = title[0] if title else "Sin título"
                    abstract = doc.get("abstract", "")
                    if not isinstance(abstract, str):
                        abstract = ""

                    authors = doc.get("authors") or []
                    author = "Desconocido"
                    if authors:
                        first = authors[0]
                        if isinstance(first, dict):
                            author = f"{first.get('first_name', '')} {first.get('last_name', '')}".strip()
                        elif isinstance(first, str):
                            author = first
                        if not author:
                            author = "Desconocido"

                    source = doc.get("source", {})
                    if isinstance(source, dict):
                        journal = source.get("title", "No disponible")
                    else:
                        journal = str(source) if source else "No disponible"

                    year = str(doc.get("year_published", "")) if doc.get("year_published") else ""

                    external_ids = doc.get("external_ids") or []
                    doi = ""
                    for eid in external_ids:
                        if isinstance(eid, dict) and eid.get("type") == "doi":
                            doi = (eid.get("value") or "").lower().strip()
                            break

                    pdf_url = ""
                    oa = doc.get("open_access") or {}
                    if isinstance(oa, dict):
                        locations = oa.get("locations") or {}
                        if isinstance(locations, dict):
                            # Esquema actual de Lens: locations.pdf_urls es una lista.
                            pdf_urls = locations.get("pdf_urls") or []
                            if pdf_urls:
                                pdf_url = pdf_urls[0]
                        elif isinstance(locations, list):
                            # Esquema antiguo: lista de {pdf_url, ...}.
                            for loc in locations:
                                if isinstance(loc, dict):
                                    url = loc.get("pdf_url", "") or ""
                                    if url:
                                        pdf_url = url
                                        break

                    normalized.append({
                        "title": title,
                        "author": author,
                        "journal": journal,
                        "year": year,
                        "doi": doi,
                        "source": "Lens",
                        "abstract": abstract,
                        "pdf_url": pdf_url,
                    })

                    if len(normalized) >= max_results:
                        break

                # Lens.org no tiene paginación simple en POST, terminamos
                break

            except Exception as e:
                logger.error("[Lens] Excepción: %s: %s", type(e).__name__, e)
                break

    logger.info("[Lens] %d resultados para: %s...", len(normalized), query[:60])

    if normalized:
        set_cache(cache_key, normalized)
    return normalized
