from __future__ import annotations

import csv
import logging

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


def _sanitize_bibtex(text: str) -> str:
    text = text.replace("{", "\\{").replace("}", "\\}")
    text = text.replace("&", "\\&")
    return text
