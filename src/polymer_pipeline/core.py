"""Lógica de negocio compartida entre CLI y Streamlit.

Extrae la orquestación del pipeline en funciones puras que cualquier
interfaz (CLI, Streamlit, FastAPI) puede llamar sin side effects.
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

from polymer_pipeline.settings import TOTAL_RESULTS_PER_QUERY, MAX_WORKERS
from polymer_pipeline.dict import SEARCH_QUERIES, LEVEL_FILTER_RULES, build_boolean_query
from polymer_pipeline.filters import passes_filter
from polymer_pipeline.fetchers import (
    fetch_crossref,
    fetch_springer,
    fetch_elsevier,
    fetch_pubmed,
    fetch_openalex,
    fetch_mdpi,
    fetch_semantic_scholar,
    fetch_lens,
)

logger = logging.getLogger(__name__)

ENABLE_SEMANTIC_SCHOLAR = True

_FETCHER_MAP: dict[str, tuple[Callable, tuple, dict]] = {
    "Crossref":        (fetch_crossref,        (),    {}),
    "Springer":        (fetch_springer,        (),    {}),
    "Elsevier":        (fetch_elsevier,        (),    {}),
    "PubMed":          (fetch_pubmed,          (),    {"max_results": TOTAL_RESULTS_PER_QUERY}),
    "OpenAlex":        (fetch_openalex,        (),    {"max_results": TOTAL_RESULTS_PER_QUERY}),
    "MDPI":            (fetch_mdpi,            (),    {"max_results": TOTAL_RESULTS_PER_QUERY}),
    "SemanticScholar": (fetch_semantic_scholar, (),   {"max_results": TOTAL_RESULTS_PER_QUERY}),
    "Lens":            (fetch_lens,            (),    {"max_results": TOTAL_RESULTS_PER_QUERY}),
}


def _build_fetcher_specs(
    query: str,
    sources: list[str] | None = None,
) -> list[tuple[Callable, tuple, dict]]:
    """Devuelve las specs (fn, args, kwargs) de los fetchers solicitados."""
    specs = []
    for name, (fn, args, kwargs) in _FETCHER_MAP.items():
        if sources and name not in sources:
            continue
        if name == "SemanticScholar" and not ENABLE_SEMANTIC_SCHOLAR:
            continue
        specs.append((fn, (query,) + args, kwargs))
    return specs


def _fetch_task(
    level: str,
    query: str,
    fn: Callable,
    args: tuple,
    kwargs: dict,
) -> dict:
    name = fn.__name__
    t0 = time.monotonic()
    try:
        articles = fn(*args, **kwargs)
        elapsed = time.monotonic() - t0
        logger.info("[%s] Terminado en %.1fs -> %d artículos.", name, elapsed, len(articles))
        return {"level": level, "query": query, "source": name, "ok": True, "articles": articles}
    except Exception as e:
        elapsed = time.monotonic() - t0
        logger.error("[Error] %s falló tras %.1fs: %s", name, elapsed, e)
        return {"level": level, "query": query, "source": name, "ok": False, "articles": []}


def _collect(
    tasks: list[tuple],
    progress_callback: Callable | None = None,
) -> dict:
    """Ejecuta todas las tareas en un pool global con callback de progreso."""
    results_by_query: dict = {}
    total = len(tasks)
    completed = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(_fetch_task, *t): t for t in tasks}
        for future in as_completed(futures):
            result = future.result()
            key = (result["level"], result["query"])
            results_by_query.setdefault(key, []).append(result)
            completed += 1
            if progress_callback:
                progress_callback(completed, total, result["source"])

    return results_by_query


def _dedupe(
    results_by_query: dict,
    queries: dict[str, list[str]],
    filter_rules: dict[str, list[list[str]]] | None = None,
) -> list[dict]:
    """Filtra y deduplica artículos de las queries dadas."""
    seen_dois: set[str] = set()
    seen_titles: set[str] = set()
    all_articles: list[dict] = []

    for level, level_queries in queries.items():
        for q in level_queries:
            combined_raw: list[dict] = []
            for result in results_by_query.get((level, q), []):
                combined_raw.extend(result["articles"])

            for art in combined_raw:
                if not passes_filter(art, level, filter_rules):
                    continue

                doi = art.get("doi", "")
                title = art.get("title", "").lower().strip()

                if doi and doi not in seen_dois:
                    seen_dois.add(doi)
                    art["level"] = level
                    all_articles.append(art)
                elif not doi and title not in seen_titles:
                    seen_titles.add(title)
                    art["level"] = level
                    all_articles.append(art)

    return all_articles


def run_pipeline(
    levels: list[str] | None = None,
    sources: list[str] | None = None,
    max_results: int = 250,
    progress_callback: Callable | None = None,
    custom_queries: dict[str, list[str]] | None = None,
    custom_filter_rules: dict[str, list[list[str]]] | None = None,
) -> list[dict]:
    """Ejecuta el pipeline completo con los niveles y fuentes indicados.

    Args:
        levels: Lista de niveles a ejecutar (default: todos).
        sources: Lista de fuentes API a usar (default: todas).
        max_results: Máximo de resultados por query por fuente.
        progress_callback: fn(completed, total, source_name) para progreso.
        custom_queries: Queries personalizadas {level: [query_strings]}.
                        Si se provee, tiene prioridad sobre SEARCH_QUERIES.
        custom_filter_rules: Reglas de filtro personalizadas {level: [groups]}.
                             Si se provee, tiene prioridad sobre LEVEL_FILTER_RULES.

    Returns:
        Lista de artículos normalizados, filtrados y deduplicados.
    """
    # Seleccionar queries: custom_queries tiene prioridad
    if custom_queries:
        queries = custom_queries
    elif levels:
        queries = {k: v for k, v in SEARCH_QUERIES.items() if k in levels}
    else:
        queries = dict(SEARCH_QUERIES)

    # Seleccionar reglas de filtro
    if custom_filter_rules is not None:
        filter_rules = custom_filter_rules
    else:
        filter_rules = {k: v for k, v in LEVEL_FILTER_RULES.items() if k in queries}
        # Si algún nivel no tiene reglas, no filtrar por título (lista vacía = sin filtro)
        for level in queries:
            if level not in filter_rules:
                filter_rules[level] = []

    # Construir tareas
    tasks: list[tuple] = []
    for level, level_queries in queries.items():
        for q in level_queries:
            for fn, args, kwargs in _build_fetcher_specs(q, sources):
                tasks.append((level, q, fn, args, kwargs))

    logger.info("[Pipeline] %d tareas a ejecutar", len(tasks))

    # Ejecutar
    results_by_query = _collect(tasks, progress_callback)

    # Filtrar y deduplicar
    articles = _dedupe(results_by_query, queries, filter_rules)
    logger.info("[Pipeline] %d artículos únicos después de filtrado", len(articles))

    return articles


def filter_articles(
    articles: list[dict],
    query: str = "",
    year_range: tuple[int, int] | None = None,
    sources: list[str] | None = None,
    levels: list[str] | None = None,
) -> list[dict]:
    """Filtra artículos según criterios del usuario (post-pipeline)."""
    result = articles

    if query:
        q = query.lower()
        result = [
            a for a in result
            if q in a.get("title", "").lower()
            or q in a.get("author", "").lower()
            or q in a.get("doi", "").lower()
            or q in a.get("journal", "").lower()
        ]

    if year_range:
        y_min, y_max = year_range
        result = [
            a for a in result
            if _safe_year(a) and y_min <= _safe_year(a) <= y_max
        ]

    if sources:
        result = [a for a in result if a.get("source") in sources]

    if levels:
        result = [a for a in result if a.get("level") in levels]

    return result


def _safe_year(article: dict) -> int | None:
    try:
        return int(article.get("year", ""))
    except (ValueError, TypeError):
        return None


def compute_quality_metrics(articles: list[dict]) -> dict:
    """Calcula métricas de calidad de datos."""
    total = len(articles)
    if total == 0:
        return {"total": 0, "with_doi": 0, "with_abstract": 0, "with_pdf": 0,
                "unknown_author": 0, "unknown_journal": 0}
    return {
        "total": total,
        "with_doi": sum(1 for a in articles if a.get("doi")),
        "with_abstract": sum(1 for a in articles if a.get("abstract")),
        "with_pdf": sum(1 for a in articles if a.get("pdf_url")),
        "unknown_author": sum(1 for a in articles if a.get("author") == "Desconocido"),
        "unknown_journal": sum(1 for a in articles if a.get("journal") in ("No disponible", "Desconocido")),
    }
