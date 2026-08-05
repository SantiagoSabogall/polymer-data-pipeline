import json
import webbrowser
from concurrent.futures import ThreadPoolExecutor, as_completed

from polymer_pipeline.settings import (
    load_settings, TOTAL_RESULTS_PER_QUERY, MAX_WORKERS,
)
from polymer_pipeline.dict import SEARCH_QUERIES
from polymer_pipeline.filters import passes_filter
from polymer_pipeline.plots import generate_all_plots
from polymer_pipeline.dashboard import generate_dashboard
from polymer_pipeline.export import export_csv, export_bibtex
from polymer_pipeline.fetchers import (
    fetch_crossref,
    fetch_springer,
    fetch_elsevier,
    fetch_pubmed,
    fetch_openalex,
)


def _fetcher_specs(query):
    """Especificaciones (fn, args, kwargs) de todos los fetchers para una consulta."""
    return [
        (fetch_crossref, (query,), {}),
        (fetch_springer, (query,), {}),
        (fetch_elsevier, (query,), {}),
        (fetch_pubmed, (query,), {"max_results": TOTAL_RESULTS_PER_QUERY}),
        (fetch_openalex, (query,), {"max_results": TOTAL_RESULTS_PER_QUERY}),
    ]


def _fetch_task(level, query, fn, args, kwargs):
    try:
        return {
            "level": level,
            "query": query,
            "source": fn.__name__,
            "ok": True,
            "articles": fn(*args, **kwargs),
        }
    except Exception as e:
        print(f"  [Error] {fn.__name__} falló para {query[:60]}: {e}")
        return {
            "level": level,
            "query": query,
            "source": fn.__name__,
            "ok": False,
            "articles": [],
        }


def _collect(tasks):
    """Ejecuta todas las tareas (nivel, consulta, fetcher) en un pool global."""
    results_by_query = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(_fetch_task, *t): t for t in tasks}
        for future in as_completed(futures):
            result = future.result()
            key = (result["level"], result["query"])
            results_by_query.setdefault(key, []).append(result)
    return results_by_query


def _filter_and_dedupe(results_by_query, seen_dois, seen_titles):
    """Filtra y deduplica; devuelve artículos únicos y un log de stats por consulta."""
    all_normalized_articles = []
    stats = []

    for level, queries in SEARCH_QUERIES.items():
        print(f"\n>>> Procesando nivel: {level}")

        for q in queries:
            print(f"  Consulta: {q[:80]}...")

            combined_raw = []
            for result in results_by_query.get((level, q), []):
                combined_raw.extend(result["articles"])

            accepted, rejected_items = [], []
            for art in combined_raw:
                if passes_filter(art, level):
                    accepted.append(art)
                else:
                    rejected_items.append(art)

            if rejected_items:
                rejected_by_source = {}
                for art in rejected_items:
                    rejected_by_source[art["source"]] = rejected_by_source.get(art["source"], 0) + 1
                print(f"    [Filtro] Rechazados: {len(rejected_items)}/{len(combined_raw)} -> {rejected_by_source}")

            new_additions_count = 0
            duplicates_count = 0

            for art in accepted:
                doi = art["doi"]
                title = art["title"].lower().strip()

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

            print(f"  --> Agregados: {new_additions_count} nuevos | Duplicados omitidos: {duplicates_count}")
            stats.append((level, q, new_additions_count, duplicates_count))

    return all_normalized_articles, stats


def main():
    load_settings()

    print("=" * 60)
    print(" INICIANDO PIPELINE DE BÚSQUEDA CIENTÍFICA CONSOLIDADA ")
    print("=" * 60)

    tasks = []
    for level, queries in SEARCH_QUERIES.items():
        for q in queries:
            for fn, args, kwargs in _fetcher_specs(q):
                tasks.append((level, q, fn, args, kwargs))

    print(f"[Pipeline] Lanzando {len(tasks)} tareas (nivel, consulta, API) en paralelo...")
    results_by_query = _collect(tasks)

    seen_dois = set()
    seen_titles = set()
    all_normalized_articles, _ = _filter_and_dedupe(results_by_query, seen_dois, seen_titles)

    json_output_path = "consolidated_results.json"
    with open(json_output_path, "w", encoding="utf-8") as f:
        json.dump(all_normalized_articles, f, indent=4, ensure_ascii=False)
    print(f"\n[Exito] Se guardaron {len(all_normalized_articles)} articulos unificados en {json_output_path}")

    plots = generate_all_plots(all_normalized_articles, pdf_dir="plots_output")

    html_content = generate_dashboard(all_normalized_articles, plots=plots)
    html_output_path = "dashboard.html"
    with open(html_output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[Exito] Dashboard interactivo generado en {html_output_path}")
    print(f"[Exito] PDFs de graficas guardados en ./plots_output/")

    export_csv(all_normalized_articles)
    export_bibtex(all_normalized_articles)

    webbrowser.open(html_output_path)
    print("\nProceso finalizado con exito!")