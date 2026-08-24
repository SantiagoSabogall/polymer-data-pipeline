"""Fetcher de artículos desde Semantic Scholar.

Semantic Scholar indexa 214M+ papers con abstracts, citation counts,
TLDR summaries y campos de estudio. API gratuita sin key (1 req/sec)
o con key para mayor velocidad.
"""

import time
from polymer_pipeline.cache import get_cached, set_cache
from polymer_pipeline.query_builder import build_semanticscholar_query
from polymer_pipeline.http import make_session

SEMANTIC_SCHOLAR_API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
MAX_RETRIES = 5


def fetch_semantic_scholar(query: str, max_results: int = 100) -> list:
    """Obtiene artículos de Semantic Scholar.

    Args:
        query: Consulta booleana genérica (misma sintaxis que otros fetchers).
        max_results: Máximo de resultados a devolver (máx 1000 para relevance search).
    """
    cache_key = f"SemanticScholar:{query}"
    cached = get_cached(cache_key)
    if cached is not None:
        print(f"[SemanticScholar] Usando cache para: {query[:60]}...")
        return cached

    translated = build_semanticscholar_query(query)

    normalized = []
    retries = 0
    offset = 0
    limit = min(max_results, 100)

    with make_session(backoff_factor=2.0) as session:
        session.headers.update({
            "User-Agent": "polymer-pipeline/1.0"
        })

        while len(normalized) < max_results:
            params = {
                "query": translated,
                "limit": limit,
                "offset": offset,
                "fields": "title,abstract,authors,year,venue,externalIds,citationCount,fieldsOfStudy,openAccessPdf"
            }

            try:
                resp = session.get(SEMANTIC_SCHOLAR_API_URL, params=params, timeout=20)

                if resp.status_code == 429:
                    retries += 1
                    if retries > MAX_RETRIES:
                        print(f"[SemanticScholar] Reintentos agotados. Abortando.")
                        break
                    wait = min(2 ** retries, 60)
                    print(f"[SemanticScholar] 429. Esperando {wait}s (intento {retries}/{MAX_RETRIES}).")
                    time.sleep(wait)
                    continue

                retries = 0

                if resp.status_code != 200:
                    print(f"[SemanticScholar] Error {resp.status_code}: {resp.text[:200]!r}")
                    break

                data = resp.json()
                results = data.get("data", [])
                if not results:
                    break

                for paper in results:
                    title = paper.get("title", "Sin título")
                    abstract = paper.get("abstract", "") or ""

                    authors = paper.get("authors", [])
                    author = authors[0].get("name", "Desconocido") if authors else "Desconocido"

                    venue = paper.get("venue", "") or ""
                    year = str(paper.get("year", "")) if paper.get("year") else ""

                    external_ids = paper.get("externalIds", {})
                    doi = external_ids.get("DOI", "").lower().strip() if external_ids else ""

                    open_access_pdf = paper.get("openAccessPdf") or {}
                    pdf_url = open_access_pdf.get("url", "") or ""

                    normalized.append({
                        "title": title,
                        "author": author,
                        "journal": venue,
                        "year": year,
                        "doi": doi,
                        "source": "SemanticScholar",
                        "abstract": abstract,
                        "pdf_url": pdf_url,
                    })

                    if len(normalized) >= max_results:
                        break

                next_offset = data.get("next")
                if next_offset is None or len(results) < limit:
                    break
                offset = next_offset

                time.sleep(1)

            except Exception as e:
                print(f"[SemanticScholar] Excepción: {type(e).__name__}: {e}")
                break

    print(f"[SemanticScholar] {len(normalized)} resultados para: {query[:60]}...")

    if normalized:
        set_cache(cache_key, normalized)
    return normalized
