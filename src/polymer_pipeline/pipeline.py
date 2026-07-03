import json
import webbrowser

from polymer_pipeline.settings import TOTAL_RESULTS_PER_QUERY
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
    fetch_chemrxiv,
)


def main():
    print("=" * 60)
    print(" INICIANDO PIPELINE DE BÚSQUEDA CIENTÍFICA CONSOLIDADA ")
    print("=" * 60)

    seen_dois = set()
    seen_titles = set()
    all_normalized_articles = []

    for level, queries in SEARCH_QUERIES.items():
        print(f"\n>>> Procesando nivel: {level}")

        for q in queries:
            print(f"  Consulta: {q[:80]}...")

            crossref_articles = fetch_crossref(q)
            springer_articles = fetch_springer(q)
            elsevier_articles = fetch_elsevier(q)
            pubmed_articles = fetch_pubmed(q, max_results=TOTAL_RESULTS_PER_QUERY)
            chemrxiv_articles = fetch_chemrxiv(q, max_results=TOTAL_RESULTS_PER_QUERY)

            combined_raw = (crossref_articles + springer_articles + elsevier_articles
                            + pubmed_articles + chemrxiv_articles)

            combined = [art for art in combined_raw if passes_filter(art, level)]
            rejected_items = [art for art in combined_raw if not passes_filter(art, level)]

            if rejected_items:
                rejected_by_source = {}
                for art in rejected_items:
                    rejected_by_source[art["source"]] = rejected_by_source.get(art["source"], 0) + 1
                print(f"    [Filtro] Rechazados: {len(rejected_items)}/{len(combined_raw)} -> {rejected_by_source}")

            new_additions_count = 0
            duplicates_count = 0

            for art in combined:
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
