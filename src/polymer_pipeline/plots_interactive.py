"""Gráficas interactivas con Plotly para el dashboard Streamlit."""

from __future__ import annotations

import logging
from collections import Counter

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from polymer_pipeline.sources import SOURCE_COLORS

logger = logging.getLogger(__name__)

DARK_TEMPLATE = dict(
    template="plotly_dark",
    paper_bgcolor="#0f172a",
    plot_bgcolor="#1e293b",
    font=dict(color="#f8fafc"),
    xaxis=dict(gridcolor="rgba(148,163,184,0.15)"),
    yaxis=dict(gridcolor="rgba(148,163,184,0.15)"),
)


def plot_publications_by_year(df: pd.DataFrame) -> go.Figure:
    if "year" not in df.columns or df["year"].dropna().empty:
        fig = go.Figure()
        fig.update_layout(**DARK_TEMPLATE, title="Evolución de Publicaciones por Año (sin datos)")
        return fig
    year = pd.to_numeric(df["year"], errors="coerce").dropna().astype(int)
    year_counts = year.value_counts().sort_index().reset_index()
    year_counts.columns = ["year", "count"]

    fig = px.line(year_counts, x="year", y="count",
                  title="Evolución de Publicaciones por Año",
                  markers=True)
    fig.update_traces(fill="tozeroy", line_color="#38bdf8", line_width=2.5,
                      marker_size=6)
    fig.update_layout(**DARK_TEMPLATE, height=350,
                      xaxis_title="Año", yaxis_title="Cantidad de Artículos")
    return fig


def plot_top_journals(df: pd.DataFrame, top_n: int = 10) -> go.Figure:
    if "journal" not in df.columns:
        fig = go.Figure()
        fig.update_layout(**DARK_TEMPLATE, title=f"Top {top_n} Revistas (sin datos)")
        return fig
    journal = df["journal"].replace("No disponible", pd.NA).dropna()
    counts = journal.value_counts().head(top_n)

    fig = px.bar(x=counts.values, y=counts.index, orientation="h",
                 title=f"Top {top_n} Revistas",
                 color_discrete_sequence=["#14b8a6"])
    fig.update_layout(**DARK_TEMPLATE, height=400,
                      xaxis_title="Cantidad de Artículos", yaxis_title="")
    fig.update_traces(texttemplate="%{x}", textposition="outside")
    return fig


def plot_top_keywords(data: list[dict], top_n: int = 10) -> go.Figure:
    stop_words = {"and", "of", "the", "for", "a", "toward", "with", "from",
                  "on", "in", "to", "as", "by", "an", "its", "via", "based",
                  "using", "at", "their", "are", "is", "be"}

    all_words: list[str] = []
    for item in data:
        words = (item.get("title", "").lower()
                 .replace("/", " ").replace("(", " ").replace(")", " ").split())
        all_words.extend(words)

    keywords = [w for w in all_words if w not in stop_words and len(w) > 2]
    top = Counter(keywords).most_common(top_n)
    if not top:
        fig = go.Figure()
        fig.update_layout(**DARK_TEMPLATE, title="Top Palabras Clave (sin datos)")
        return fig

    words, freqs = zip(*top)

    fig = px.bar(x=list(words), y=list(freqs),
                 title=f"Top {top_n} Palabras Clave en Títulos",
                 color_discrete_sequence=["#f87171"])
    fig.update_layout(**DARK_TEMPLATE, height=350,
                      xaxis_title="Palabra", yaxis_title="Frecuencia")
    fig.update_traces(texttemplate="%{y}", textposition="outside")
    fig.update_xaxes(tickangle=40)
    return fig


def plot_source_distribution(df: pd.DataFrame) -> go.Figure:
    if "source" not in df.columns or df["source"].dropna().empty:
        fig = go.Figure()
        fig.update_layout(**DARK_TEMPLATE, title="Distribución por Fuente (sin datos)")
        return fig
    counts = df["source"].value_counts()
    colors = [SOURCE_COLORS.get(s, "#fbbf24") for s in counts.index]

    fig = px.pie(values=counts.values, names=counts.index,
                 title="Distribución por Fuente (API)",
                 color_discrete_sequence=colors,
                 hole=0.3)
    fig.update_layout(**DARK_TEMPLATE, height=350)
    fig.update_traces(textinfo="label+percent",
                      textfont_size=11,
                      marker=dict(line=dict(color="#0f172a", width=2)))
    return fig


def plot_level_distribution(df: pd.DataFrame) -> go.Figure:
    if "level" not in df.columns or df["level"].dropna().empty:
        fig = go.Figure()
        fig.update_layout(**DARK_TEMPLATE, title="Distribución por Nivel (sin datos)")
        return fig
    level_labels = {
        "L1": "L1 Blends", "L2": "L2 Aditivos",
        "L3": "L3 Empaques", "L4": "L4 Biodegradables",
    }
    level_colors = {
        "L1": "#10b981", "L2": "#f59e0b",
        "L3": "#3b82f6", "L4": "#ec4899",
    }
    counts = df["level"].value_counts()
    labels = [level_labels.get(lvl, lvl) for lvl in counts.index]
    colors = [level_colors.get(lvl, "#94a3b8") for lvl in counts.index]

    fig = px.bar(x=labels, y=counts.values,
                 title="Distribución por Nivel",
                 color=labels, color_discrete_sequence=colors)
    fig.update_layout(**DARK_TEMPLATE, height=300, showlegend=False,
                      xaxis_title="", yaxis_title="Cantidad")
    fig.update_traces(texttemplate="%{y}", textposition="outside")
    return fig


def generate_interactive_plots(data: list[dict]) -> dict[str, go.Figure]:
    """Genera todas las gráficas interactivas para Streamlit."""
    df = pd.json_normalize(data)
    logger.info("[Plots] Generando gráficas interactivas...")
    return {
        "year": plot_publications_by_year(df),
        "journals": plot_top_journals(df),
        "keywords": plot_top_keywords(data),
        "sources": plot_source_distribution(df),
        "levels": plot_level_distribution(df),
    }
