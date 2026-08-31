from __future__ import annotations

import csv
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def export_csv(articles: list[dict], filepath: str = "consolidated_results.csv") -> None:
    if not articles:
        logger.warning("[Export] No hay artículos para exportar a CSV.")
        return
    fieldnames = ["level", "title", "author", "journal", "year", "doi", "source", "pdf_url"]
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for art in articles:
            writer.writerow({k: art.get(k, "") for k in fieldnames})
    logger.info("[Export] CSV guardado en %s", filepath)


def export_bibtex(articles: list[dict], filepath: str = "consolidated_results.bib") -> None:
    if not articles:
        logger.warning("[Export] No hay artículos para exportar a BibTeX.")
        return
    with open(filepath, "w", encoding="utf-8") as f:
        for i, art in enumerate(articles):
            source = art.get("source", "Unknown")[:3]
            year = art.get("year", "nodate")
            key = f"{source}_{year}_{i+1}"
            title = _sanitize_bibtex(art.get("title", ""))
            author = _sanitize_bibtex(art.get("author", ""))
            journal = _sanitize_bibtex(art.get("journal", ""))
            doi = art.get("doi", "")
            f.write(f"@article{{{key},\n")
            f.write(f"  title = {{{title}}},\n")
            f.write(f"  author = {{{author}}},\n")
            f.write(f"  journal = {{{journal}}},\n")
            f.write(f"  year = {{{year}}},\n")
            f.write(f"  doi = {{{doi}}},\n")
            f.write(f"  source = {{{art.get('source', '')}}}\n")
            f.write("}\n\n")
    logger.info("[Export] BibTeX guardado en %s", filepath)


def export_json(articles: list[dict], filepath: str = "consolidated_results.json") -> None:
    if not articles:
        logger.warning("[Export] No hay artículos para exportar a JSON.")
        return
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(articles, f, indent=4, ensure_ascii=False)
    logger.info("[Export] JSON guardado en %s", filepath)


def export_all(
    articles: list[dict],
    output_dir: Path | str,
    formats: list[str] | None = None,
) -> dict[str, Path]:
    """Exporta artículos en múltiples formatos.

    Args:
        articles: Lista de artículos a exportar.
        output_dir: Directorio de salida.
        formats: Lista de formatos ("csv", "bibtex", "json"). Default: todos.

    Returns:
        Dict con los formatos exportados y sus rutas.
    """
    if formats is None:
        formats = ["csv", "bibtex", "json"]

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    results: dict[str, Path] = {}

    for fmt in formats:
        if fmt == "csv":
            path = out / "consolidated_results.csv"
            export_csv(articles, filepath=str(path))
            results["csv"] = path
        elif fmt == "bibtex":
            path = out / "consolidated_results.bib"
            export_bibtex(articles, filepath=str(path))
            results["bibtex"] = path
        elif fmt == "json":
            path = out / "consolidated_results.json"
            export_json(articles, filepath=str(path))
            results["json"] = path

    return results


def _sanitize_bibtex(text: str) -> str:
    text = text.replace("{", "\\{").replace("}", "\\}")
    text = text.replace("&", "\\&")
    return text
