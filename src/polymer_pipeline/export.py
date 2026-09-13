from __future__ import annotations

import csv
import io
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _csv_string(articles: list[dict]) -> str:
    """Genera CSV como string en memoria."""
    output = io.StringIO()
    fieldnames = [
        "level", "title", "author", "journal", "year", "doi", "source", "pdf_url",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for art in articles:
        writer.writerow({k: art.get(k, "") for k in fieldnames})
    return output.getvalue()


def _bibtex_string(articles: list[dict]) -> str:
    """Genera BibTeX como string en memoria."""
    lines: list[str] = []
    for i, art in enumerate(articles):
        source = art.get("source", "Unknown")[:3]
        year = art.get("year", "nodate")
        key = f"{source}_{year}_{i+1}"
        title = _sanitize_bibtex(art.get("title", ""))
        author = _sanitize_bibtex(art.get("author", ""))
        journal = _sanitize_bibtex(art.get("journal", ""))
        doi = art.get("doi", "")
        lines.append(f"@article{{{key},")
        lines.append(f"  title = {{{title}}},")
        lines.append(f"  author = {{{author}}},")
        lines.append(f"  journal = {{{journal}}},")
        lines.append(f"  year = {{{year}}},")
        lines.append(f"  doi = {{{doi}}},")
        lines.append(f"  source = {{{art.get('source', '')}}}")
        lines.append("}\n")
    return "\n".join(lines)


def export_csv(
    articles: list[dict],
    filepath: str | None = None,
) -> str | None:
    """Exporta artículos a CSV.

    Si *filepath* se provee, escribe el archivo y devuelve ``None``.
    Si no, devuelve el contenido CSV como string.
    """
    if not articles:
        logger.warning("[Export] No hay artículos para exportar a CSV.")
        return "" if filepath is None else None

    csv_str = _csv_string(articles)

    if filepath is not None:
        Path(filepath).write_text(csv_str, encoding="utf-8")
        logger.info("[Export] CSV guardado en %s", filepath)
        return None

    return csv_str


def export_bibtex(
    articles: list[dict],
    filepath: str | None = None,
) -> str | None:
    """Exporta artículos a BibTeX.

    Si *filepath* se provee, escribe el archivo y devuelve ``None``.
    Si no, devuelve el contenido BibTeX como string.
    """
    if not articles:
        logger.warning("[Export] No hay artículos para exportar a BibTeX.")
        return "" if filepath is None else None

    bib_str = _bibtex_string(articles)

    if filepath is not None:
        Path(filepath).write_text(bib_str, encoding="utf-8")
        logger.info("[Export] BibTeX guardado en %s", filepath)
        return None

    return bib_str


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
    text = text.replace("&", "\\&")
    text = text.replace("{", "\\{").replace("}", "\\}")
    return text
