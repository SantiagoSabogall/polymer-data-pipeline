from __future__ import annotations

import base64
import io
import json
import logging
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from polymer_pipeline._plot_common import (
    extract_source_distribution,
    extract_top_journals,
    extract_top_keywords,
    extract_year_counts,
)
from polymer_pipeline.sources import SOURCE_COLORS

logger = logging.getLogger(__name__)

PALETTE: dict[str, str] = {
    "bg":      "#0f172a",
    "card":    "#1e293b",
    "text":    "#f8fafc",
    "muted":   "#94a3b8",
    "blue":    "#38bdf8",
    "purple":  "#8b5cf6",
    "teal":    "#14b8a6",
    "coral":   "#f87171",
    "amber":   "#fbbf24",
}


def _apply_dark_style(fig: plt.Figure, ax: plt.Axes) -> None:
    fig.patch.set_facecolor(PALETTE["bg"])
    ax.set_facecolor(PALETTE["card"])
    ax.tick_params(colors=PALETTE["muted"], labelsize=9)
    ax.xaxis.label.set_color(PALETTE["muted"])
    ax.yaxis.label.set_color(PALETTE["muted"])
    ax.title.set_color(PALETTE["text"])
    for spine in ax.spines.values():
        spine.set_edgecolor("#1e293b")
    ax.grid(True, linestyle="--", alpha=0.25, color=PALETTE["muted"])


def _fig_to_base64(fig: plt.Figure) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150,
                facecolor=fig.get_facecolor())
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return encoded


def _save_pdf(fig: plt.Figure, path: str) -> None:
    fig.savefig(path, format="pdf", bbox_inches="tight",
                facecolor=fig.get_facecolor())


def plot_publications_by_year(df: pd.DataFrame, pdf_dir: str = ".") -> str:
    years, counts = extract_year_counts(df)
    if not years:
        fig, ax = plt.subplots(figsize=(9, 4))
        ax.set_title("Sin datos", fontsize=14, pad=12)
        _apply_dark_style(fig, ax)
        b64 = _fig_to_base64(fig)
        return b64

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(years, counts, marker="o",
            color=PALETTE["blue"], linewidth=2.5, markersize=6)
    ax.fill_between(years, counts, alpha=0.15, color=PALETTE["blue"])
    ax.set_title("Evolucion de Publicaciones por Anio", fontsize=14, pad=12)
    ax.set_xlabel("Anio")
    ax.set_ylabel("Cantidad de Articulos")
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    _apply_dark_style(fig, ax)

    pdf_path = Path(pdf_dir) / "plot_year.pdf"
    _save_pdf(fig, str(pdf_path))
    logger.info("  [Plots] PDF guardado: %s", pdf_path)

    b64 = _fig_to_base64(fig)
    return b64


def plot_top_journals(df: pd.DataFrame, pdf_dir: str = ".", top_n: int = 10) -> str:
    names, counts = extract_top_journals(df, top_n)
    if not names:
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.set_title("Sin datos", fontsize=14, pad=12)
        _apply_dark_style(fig, ax)
        b64 = _fig_to_base64(fig)
        return b64

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(names[::-1], counts[::-1],
                   color=PALETTE["teal"], edgecolor="none", height=0.6)

    for bar in bars:
        width = bar.get_width()
        ax.text(width + 0.3, bar.get_y() + bar.get_height() / 2,
                str(int(width)), va="center", ha="left",
                color=PALETTE["muted"], fontsize=8)

    ax.set_title(f"Top {top_n} Revistas con Mayor Numero de Publicaciones",
                 fontsize=14, pad=12)
    ax.set_xlabel("Cantidad de Articulos")
    _apply_dark_style(fig, ax)
    ax.invert_yaxis()

    pdf_path = Path(pdf_dir) / "plot_journals.pdf"
    _save_pdf(fig, str(pdf_path))
    logger.info("  [Plots] PDF guardado: %s", pdf_path)

    b64 = _fig_to_base64(fig)
    return b64


def plot_top_keywords(data: list[dict], pdf_dir: str = ".", top_n: int = 10) -> str:
    words, freqs = extract_top_keywords(data, top_n)
    if not words:
        fig, ax = plt.subplots(figsize=(9, 4))
        ax.set_title("Sin datos", fontsize=14, pad=12)
        _apply_dark_style(fig, ax)
        b64 = _fig_to_base64(fig)
        return b64

    fig, ax = plt.subplots(figsize=(9, 4))
    x = np.arange(len(words))
    bars = ax.bar(x, freqs, color=PALETTE["coral"], edgecolor="none", width=0.6)

    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, height + 0.3,
                str(int(height)), ha="center", va="bottom",
                color=PALETTE["muted"], fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(words, rotation=40, ha="right")
    ax.set_title(f"Top {top_n} Palabras Clave en Titulos", fontsize=14, pad=12)
    ax.set_ylabel("Frecuencia")
    _apply_dark_style(fig, ax)

    pdf_path = Path(pdf_dir) / "plot_keywords.pdf"
    _save_pdf(fig, str(pdf_path))
    logger.info("  [Plots] PDF guardado: %s", pdf_path)

    b64 = _fig_to_base64(fig)
    return b64


def plot_source_distribution(df: pd.DataFrame, pdf_dir: str = ".") -> str:
    names, counts = extract_source_distribution(df)
    colors = [SOURCE_COLORS.get(s, PALETTE["amber"]) for s in names]

    fig, ax = plt.subplots(figsize=(6, 5))
    wedges, texts, autotexts = ax.pie(
        counts,
        labels=names,
        colors=colors,
        autopct="%1.1f%%",
        startangle=140,
        wedgeprops=dict(edgecolor=PALETTE["bg"], linewidth=2),
    )
    for t in texts:
        t.set_color(PALETTE["text"])
    for at in autotexts:
        at.set_color(PALETTE["bg"])
        at.set_fontweight("bold")

    ax.set_title("Distribucion por Fuente (API)", fontsize=14, pad=12)
    fig.patch.set_facecolor(PALETTE["bg"])
    ax.set_facecolor(PALETTE["bg"])

    pdf_path = Path(pdf_dir) / "plot_sources.pdf"
    _save_pdf(fig, str(pdf_path))
    logger.info("  [Plots] PDF guardado: %s", pdf_path)

    b64 = _fig_to_base64(fig)
    return b64


def generate_all_plots(data: list[dict], pdf_dir: str = ".") -> dict[str, str]:
    Path(pdf_dir).mkdir(parents=True, exist_ok=True)
    df = pd.json_normalize(data)

    logger.info("[Plots] Generando gráficas...")
    plots = {
        "year":     plot_publications_by_year(df, pdf_dir),
        "journals": plot_top_journals(df, pdf_dir),
        "keywords": plot_top_keywords(data, pdf_dir),
        "sources":  plot_source_distribution(df, pdf_dir),
    }
    logger.info("[Plots] Todas las gráficas generadas!")
    return plots


if __name__ == "__main__":
    with open("consolidated_results.json", "r", encoding="utf-8") as f:
        datos = json.load(f)
    generate_all_plots(datos, pdf_dir="plots_output")
    logger.info("PDFs guardados en ./plots_output/")
