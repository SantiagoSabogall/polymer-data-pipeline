from __future__ import annotations

import json
import logging
import time
import webbrowser
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from polymer_pipeline.settings import (
    load_settings, TOTAL_RESULTS_PER_QUERY, MAX_WORKERS,
)
from polymer_pipeline.dict import SEARCH_QUERIES
from polymer_pipeline.filters import passes_filter
from polymer_pipeline.plots import generate_all_plots
from polymer_pipeline.dashboard import generate_dashboard
from polymer_pipeline.export import export_csv, export_bibtex
from polymer_pipeline.downloader import ArticleDownloader
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

# Semantic Scholar activa: usa /paper/search/bulk con throttle de 1 req/s
# (límite estándar con API key) y backoff ante 429. Funciona también sin key.
ENABLE_SEMANTIC_SCHOLAR = True


def _fetcher_specs(query: str) -> list[tuple]:
    """Especificaciones (fn, args, kwargs) de todos los fetchers para una consulta."""
    specs = [
        (fetch_crossref, (query,), {}),
        (fetch_springer, (query,), {}),
        (fetch_elsevier, (query,), {}),
        (fetch_pubmed, (query,), {"max_results": TOTAL_RESULTS_PER_QUERY}),
        (fetch_openalex, (query,), {"max_results": TOTAL_RESULTS_PER_QUERY}),
        (fetch_mdpi, (query,), {"max_results": TOTAL_RESULTS_PER_QUERY}),
    ]
    if ENABLE_SEMANTIC_SCHOLAR:
        specs.append((fetch_semantic_scholar, (query,), {"max_results": TOTAL_RESULTS_PER_QUERY}))
    specs.append((fetch_lens, (query,), {"max_results": TOTAL_RESULTS_PER_QUERY}))
    return specs


def _fetch_task(level: str, query: str, fn, args: tuple, kwargs: dict) -> dict:
    name = fn.__name__
    logger.info("[%s] Iniciando: %s...", name, query[:60])
    t0 = time.monotonic()
    try:
        articles = fn(*args, **kwargs)
        elapsed = time.monotonic() - t0
        logger.info("[%s] Terminado en %.1fs -> %d artículos.", name, elapsed, len(articles))
        return {
            "level": level,
            "query": query,
            "source": name,
            "ok": True,
            "articles": articles,
        }
    except Exception as e:
        elapsed = time.monotonic() - t0
        logger.error("[Error] %s falló tras %.1fs para %s: %s", name, elapsed, query[:60], e)
        return {
            "level": level,
            "query": query,
            "source": name,
            "ok": False,
            "articles": [],
        }


def _collect(tasks: list[tuple]) -> dict:
    """Ejecuta todas las tareas (nivel, consulta, fetcher) en un pool global."""
    results_by_query: dict = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(_fetch_task, *t): t for t in tasks}
        for future in as_completed(futures):
            result = future.result()
            key = (result["level"], result["query"])
            results_by_query.setdefault(key, []).append(result)
    return results_by_query


def _filter_and_dedupe(
    results_by_query: dict,
    seen_dois: set[str],
    seen_titles: set[str],
) -> tuple[list[dict], list[tuple]]:
    """Filtra y deduplica; devuelve artículos únicos y un log de stats por consulta."""
    all_normalized_articles: list[dict] = []
    stats: list[tuple] = []

    for level, queries in SEARCH_QUERIES.items():
        logger.info(">>> Procesando nivel: %s", level)

        for q in queries:
            logger.info("  Consulta: %s...", q[:80])

            combined_raw: list[dict] = []
            for result in results_by_query.get((level, q), []):
                combined_raw.extend(result["articles"])

            accepted, rejected_items = [], []
            for art in combined_raw:
                if passes_filter(art, level):
                    accepted.append(art)
                else:
                    rejected_items.append(art)

            if rejected_items:
                rejected_by_source: dict[str, int] = {}
                for art in rejected_items:
                    src = art.get("source", "")
                    rejected_by_source[src] = rejected_by_source.get(src, 0) + 1
                logger.warning(
                    "    [Filtro] Rechazados: %d/%d -> %s",
                    len(rejected_items), len(combined_raw), rejected_by_source,
                )

            new_additions_count = 0
            duplicates_count = 0

            for art in accepted:
                doi = art.get("doi", "")
                title = art.get("title", "").lower().strip()

                if doi and doi not in seen_dois:
                    seen_dois.add(doi)
                    art["level"] = level
                    all_normalized_articles.append(art)
                    new_additions_count += 1
                elif not doi and title not in seen_titles:
                    seen_titles.add(title)
                    art["level"] = level
                    all_normalized_articles.append(art)
                    new_additions_count += 1
                else:
                    duplicates_count += 1

            logger.info(
                "  --> Agregados: %d nuevos | Duplicados omitidos: %d",
                new_additions_count, duplicates_count,
            )
            stats.append((level, q, new_additions_count, duplicates_count))

    return all_normalized_articles, stats


def main() -> None:
    load_settings()

    logger.info("=" * 60)
    logger.info(" INICIANDO PIPELINE DE BÚSQUEDA CIENTÍFICA CONSOLIDADA ")
    logger.info("=" * 60)

    tasks: list[tuple] = []
    for level, queries in SEARCH_QUERIES.items():
        for q in queries:
            for fn, args, kwargs in _fetcher_specs(q):
                tasks.append((level, q, fn, args, kwargs))

    logger.info("[Pipeline] Lanzando %d tareas (nivel, consulta, API) en paralelo...", len(tasks))
    results_by_query = _collect(tasks)

    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

    seen_dois: set[str] = set()
    seen_titles: set[str] = set()
    all_normalized_articles, _ = _filter_and_dedupe(results_by_query, seen_dois, seen_titles)

    json_output_path = PROJECT_ROOT / "consolidated_results.json"
    with open(json_output_path, "w", encoding="utf-8") as f:
        json.dump(all_normalized_articles, f, indent=4, ensure_ascii=False)
    logger.info(
        "[Éxito] Se guardaron %d artículos unificados en %s",
        len(all_normalized_articles), json_output_path,
    )

    plots = generate_all_plots(all_normalized_articles, pdf_dir=str(PROJECT_ROOT / "plots_output"))

    html_content = generate_dashboard(all_normalized_articles, plots=plots)
    html_output_path = PROJECT_ROOT / "dashboard.html"
    with open(html_output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    logger.info("[Éxito] Dashboard interactivo generado en %s", html_output_path)
    logger.info("[Éxito] PDFs de gráficas guardados en ./plots_output/")

    export_csv(all_normalized_articles, filepath=str(PROJECT_ROOT / "consolidated_results.csv"))
    export_bibtex(all_normalized_articles, filepath=str(PROJECT_ROOT / "consolidated_results.bib"))

    # TODO: Habilitar cuando el downloader esté listo para producción
    # logger.info("[Pipeline] Descargando PDFs de acceso abierto...")
    # downloader = ArticleDownloader(download_dir=PROJECT_ROOT / "downloads")
    # download_results = downloader.download_batch(all_normalized_articles)
    # ok = sum(1 for r in download_results if r.success)
    # fail = sum(1 for r in download_results if not r.success)
    # logger.info("[Pipeline] Descargas: %d exitosas, %d fallidas", ok, fail)

    webbrowser.open(str(html_output_path))
    logger.info("Proceso finalizado con éxito!")
