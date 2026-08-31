"""Lógica de negocio compartida entre CLI y Streamlit (async).

Extrae la orquestación del pipeline en funciones async que cualquier
interfaz (CLI, Streamlit, FastAPI) puede llamar con asyncio.run().
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Callable

from polymer_pipeline.dict import LEVEL_FILTER_RULES, SEARCH_QUERIES
from polymer_pipeline.downloader import ArticleDownloader, DownloadResult
from polymer_pipeline.fetchers import (
    fetch_crossref,
    fetch_elsevier,
    fetch_lens,
    fetch_mdpi,
    fetch_openalex,
    fetch_pubmed,
    fetch_semantic_scholar,
    fetch_springer,
)
from polymer_pipeline.filters import passes_filter
from polymer_pipeline.settings import TOTAL_RESULTS_PER_QUERY

logger = logging.getLogger(__name__)

ENABLE_SEMANTIC_SCHOLAR = True

_FETCHER_MAP: dict[str, tuple[Callable, tuple, dict]] = {
    "Crossref":        (fetch_crossref,        (),    {}),
    "Springer":        (fetch_springer,        (),    {}),
    "Elsevier":        (fetch_elsevier,        (),    {}),
    "PubMed":          (fetch_pubmed,          (),    {}),
    "OpenAlex":        (fetch_openalex,        (),    {}),
    "MDPI":            (fetch_mdpi,            (),    {}),
    "SemanticScholar": (fetch_semantic_scholar, (),   {}),
    "Lens":            (fetch_lens,            (),    {}),
}

_FETCHERS_WITH_MAX_RESULTS = {"PubMed", "OpenAlex", "MDPI", "SemanticScholar", "Lens"}
_FETCHERS_WITH_TITLE_ABS_ONLY = {"Crossref", "OpenAlex", "MDPI"}


def _build_fetcher_specs(
    query: str,
    sources: list[str] | None = None,
    max_results: int = TOTAL_RESULTS_PER_QUERY,
    title_abs_only: bool = False,
    preserve_quotes: bool = False,
) -> list[tuple[Callable, tuple, dict]]:
    """Devuelve las specs (fn, args, kwargs) de los fetchers solicitados."""
    specs = []
    for name, (fn, args, kwargs) in _FETCHER_MAP.items():
        if sources and name not in sources:
            continue
        if name == "SemanticScholar" and not ENABLE_SEMANTIC_SCHOLAR:
            continue
        final_kwargs = dict(kwargs)
        if name in _FETCHERS_WITH_MAX_RESULTS:
            final_kwargs["max_results"] = max_results
        if name in _FETCHERS_WITH_TITLE_ABS_ONLY:
            final_kwargs["title_abs_only"] = title_abs_only
        if preserve_quotes:
            final_kwargs["preserve_quotes"] = True
        specs.append((fn, (query,) + args, final_kwargs))
    return specs


async def _fetch_task(
    level: str,
    query: str,
    fn: Callable,
    args: tuple,
    kwargs: dict,
) -> dict:
    """Ejecuta un fetcher individual de forma asíncrona."""
    name = fn.__name__
    t0 = time.monotonic()
    try:
        articles = await fn(*args, **kwargs)
        elapsed = time.monotonic() - t0
        logger.info("[%s] Terminado en %.1fs -> %d artículos.", name, elapsed, len(articles))
        return {"level": level, "query": query, "source": name, "ok": True, "articles": articles}
    except Exception as e:
        elapsed = time.monotonic() - t0
        logger.error("[Error] %s falló tras %.1fs: %s", name, elapsed, e)
        return {"level": level, "query": query, "source": name, "ok": False, "articles": []}


async def _collect(
    tasks: list[tuple],
    progress_callback: Callable | None = None,
) -> dict:
    """Ejecuta todas las tareas en paralelo con asyncio.gather."""
    results_by_query: dict = {}
    total = len(tasks)
    completed = 0

    async_tasks = [
        asyncio.create_task(_fetch_task(*t))
        for t in tasks
    ]

    for coro in asyncio.as_completed(async_tasks):
        result = await coro
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
    title_abs_only: bool = False,
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
                if not passes_filter(art, level, filter_rules, title_abs_only=title_abs_only):
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


async def run_pipeline(
    levels: list[str] | None = None,
    sources: list[str] | None = None,
    max_results: int = 250,
    progress_callback: Callable | None = None,
    custom_queries: dict[str, list[str]] | None = None,
    custom_filter_rules: dict[str, list[list[str]]] | None = None,
) -> list[dict]:
    """Ejecuta el pipeline completo de forma asíncrona.

    Args:
        levels: Lista de niveles a ejecutar (default: todos).
        sources: Lista de fuentes API a usar (default: todas).
        max_results: Máximo de resultados por query por fuente.
        progress_callback: fn(completed, total, source_name) para progreso.
        custom_queries: Queries personalizadas {level: [query_strings]}.
        custom_filter_rules: Reglas de filtro personalizadas {level: [groups]}.

    Returns:
        Lista de artículos normalizados, filtrados y deduplicados.
    """
    title_abs_only = bool(custom_queries)
    preserve_quotes = bool(custom_queries)

    if custom_queries:
        queries = custom_queries
    elif levels:
        queries = {k: v for k, v in SEARCH_QUERIES.items() if k in levels}
    else:
        queries = dict(SEARCH_QUERIES)

    if custom_filter_rules is not None:
        filter_rules = custom_filter_rules
    else:
        filter_rules = {k: v for k, v in LEVEL_FILTER_RULES.items() if k in queries}
        for level in queries:
            if level not in filter_rules:
                filter_rules[level] = []

    if title_abs_only and custom_queries:
        from polymer_pipeline.query_builder import parse_boolean_query

        for lvl, qs in queries.items():
            if lvl not in filter_rules or not filter_rules[lvl]:
                combined_groups: list[list[str]] = []
                for q in qs:
                    groups = parse_boolean_query(q)
                    for g in groups:
                        cleaned = [t.strip('"').strip("'") for t in g if t.strip('"').strip("'")]
                        if cleaned:
                            combined_groups.append(cleaned)
                if combined_groups:
                    filter_rules[lvl] = combined_groups
                elif qs and qs[0].strip():
                    raw = qs[0].strip().strip('"').strip("'")
                    if raw and " AND " not in qs[0] and " OR " not in qs[0]:
                        filter_rules[lvl] = [[raw]]

    tasks: list[tuple] = []
    for level, level_queries in queries.items():
        for q in level_queries:
            for fn, args, kwargs in _build_fetcher_specs(
                q, sources, max_results, title_abs_only, preserve_quotes,
            ):
                tasks.append((level, q, fn, args, kwargs))

    logger.info("[Pipeline] %d tareas a ejecutar", len(tasks))

    results_by_query = await _collect(tasks, progress_callback)

    articles = _dedupe(results_by_query, queries, filter_rules, title_abs_only=title_abs_only)
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
        "unknown_journal": sum(
            1 for a in articles
            if a.get("journal") in ("No disponible", "Desconocido")
        ),
    }


async def download_pdfs(
    articles: list[dict],
    max_concurrent: int = 3,
) -> list[DownloadResult]:
    """Descarga PDFs de artículos open-access de forma asíncrona.

    Args:
        articles: Lista de artículos (deben tener campo ``pdf_url``).
        max_concurrent: Descargas simultáneas máximo.

    Returns:
        Lista de ``DownloadResult`` con el resultado de cada descarga.
    """
    downloader = ArticleDownloader(max_concurrent=max_concurrent)
    return await downloader.download_batch(articles)
