"""Gráficas interactivas con Plotly para el dashboard Streamlit."""

from __future__ import annotations

import logging

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from polymer_pipeline._plot_common import (
    extract_level_distribution,
    extract_source_distribution,
    extract_top_journals,
    extract_top_keywords,
    extract_year_counts,
)
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
    years, counts = extract_year_counts(df)
    if not years:
        fig = go.Figure()
        fig.update_layout(**DARK_TEMPLATE, title="Evolución de Publicaciones por Año (sin datos)")
        return fig

    year_counts = pd.DataFrame({"year": years, "count": counts})
    fig = px.line(year_counts, x="year", y="count",
                  title="Evolución de Publicaciones por Año",
                  markers=True)
    fig.update_traces(fill="tozeroy", line_color="#38bdf8", line_width=2.5,
                      marker_size=6)
    fig.update_layout(**DARK_TEMPLATE, height=350,
                      xaxis_title="Año", yaxis_title="Cantidad de Artículos")
    return fig


def plot_top_journals(df: pd.DataFrame, top_n: int = 10) -> go.Figure:
    names, counts = extract_top_journals(df, top_n)
    if not names:
        fig = go.Figure()
        fig.update_layout(**DARK_TEMPLATE, title=f"Top {top_n} Revistas (sin datos)")
        return fig

    fig = px.bar(x=counts, y=names, orientation="h",
                 title=f"Top {top_n} Revistas",
                 color_discrete_sequence=["#14b8a6"])
    fig.update_layout(**DARK_TEMPLATE, height=400,
                      xaxis_title="Cantidad de Artículos", yaxis_title="")
    fig.update_traces(texttemplate="%{x}", textposition="outside")
    return fig


def plot_top_keywords(data: list[dict], top_n: int = 10) -> go.Figure:
    words, freqs = extract_top_keywords(data, top_n)
    if not words:
        fig = go.Figure()
        fig.update_layout(**DARK_TEMPLATE, title="Top Palabras Clave (sin datos)")
        return fig

    fig = px.bar(x=list(words), y=list(freqs),
                 title=f"Top {top_n} Palabras Clave en Títulos",
                 color_discrete_sequence=["#f87171"])
    fig.update_layout(**DARK_TEMPLATE, height=350,
                      xaxis_title="Palabra", yaxis_title="Frecuencia")
    fig.update_traces(texttemplate="%{y}", textposition="outside")
    fig.update_xaxes(tickangle=40)
    return fig


def plot_source_distribution(df: pd.DataFrame) -> go.Figure:
    names, counts = extract_source_distribution(df)
    if not names:
        fig = go.Figure()
        fig.update_layout(**DARK_TEMPLATE, title="Distribución por Fuente (sin datos)")
        return fig

    colors = [SOURCE_COLORS.get(s, "#fbbf24") for s in names]
    fig = px.pie(values=counts, names=names,
                 title="Distribución por Fuente (API)",
                 color_discrete_sequence=colors,
                 hole=0.3)
    fig.update_layout(**DARK_TEMPLATE, height=350)
    fig.update_traces(textinfo="label+percent",
                      textfont_size=11,
                      marker=dict(line=dict(color="#0f172a", width=2)))
    return fig


def plot_level_distribution(df: pd.DataFrame) -> go.Figure:
    labels, counts = extract_level_distribution(df)
    if not labels:
        fig = go.Figure()
        fig.update_layout(**DARK_TEMPLATE, title="Distribución por Nivel (sin datos)")
        return fig

    level_colors = {
        "L1 Blends": "#10b981", "L2 Aditivos": "#f59e0b",
        "L3 Empaques": "#3b82f6", "L4 Biodegradables": "#ec4899",
    }
    colors = [level_colors.get(lvl, "#94a3b8") for lvl in labels]

    fig = px.bar(x=labels, y=counts,
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
