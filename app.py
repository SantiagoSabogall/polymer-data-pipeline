"""Polymer Data Pipeline — App Streamlit interactiva.

Ejecutar con: streamlit run app.py
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import streamlit as st
import pandas as pd

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from polymer_pipeline.settings import load_settings
from polymer_pipeline.dict import LEVELS, SEARCH_QUERIES
from polymer_pipeline.sources import SOURCES, SOURCE_NAMES
from polymer_pipeline.core import run_pipeline, filter_articles, compute_quality_metrics
from polymer_pipeline.plots_interactive import generate_interactive_plots
from polymer_pipeline.export import export_csv, export_bibtex

load_settings()

# ── Page config ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Polymer Data Pipeline",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuración del Pipeline")

    # Modo de búsqueda
    st.subheader("🔍 Modo de búsqueda")
    search_mode = st.radio(
        "Seleccionar modo:",
        ["📋 Presets (niveles)", "📝 Búsqueda libre"],
        label_visibility="collapsed",
    )

    # Configuración según modo
    if search_mode == "📋 Presets (niveles)":
        st.subheader("Niveles de búsqueda")
        selected_levels = []
        for level in LEVELS:
            if st.checkbox(f"{level['label']} ({level['key']})", value=True, key=f"lvl_{level['key']}"):
                selected_levels.append(level['key'])

        raw_query = None
        custom_filter_groups = None
    else:
        st.subheader("Búsqueda personalizada")
        raw_query = st.text_area(
            "Query booleana:",
            value='(polyester OR PET) AND (barrier OR permeability)',
            height=100,
        )
        custom_filter_groups = None
        selected_levels = None

    # Fuentes
    st.subheader("Fuentes (APIs)")
    selected_sources = []
    for source_name in SOURCES:
        if st.checkbox(source_name, value=True, key=f"src_{source_name}"):
            selected_sources.append(source_name)

    # Parámetros
    max_results = st.slider(
        "Resultados por query", min_value=50, max_value=1000, value=250, step=50,
    )

    # Botón de ejecución
    run_clicked = st.button("🚀 Ejecutar Pipeline", type="primary", use_container_width=True)

    # Filtros de visualización
    st.divider()
    st.header("🔍 Filtros de visualización")
    search_filter = st.text_input("Buscar en resultados:", placeholder="título, autor, DOI...")
    year_range = st.slider("Rango de años", 1990, 2026, (2015, 2026))
    filter_by_source = st.multiselect("Filtrar por fuente:", SOURCE_NAMES, default=SOURCE_NAMES)
    filter_by_level = st.multiselect(
        "Filtrar por nivel:",
        ["L1", "L2", "L3", "L4"],
        default=["L1", "L2", "L3", "L4"],
    )

# ── Main content ───────────────────────────────────────────────────────
st.title("🧪 Polymer Data Pipeline")
st.caption("Dashboard de artículos científicos consolidados y deduplicados")

# Ejecutar pipeline
if run_clicked:
    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(current: int, total: int, source: str) -> None:
        progress_bar.progress(current / total, text=f"[{current}/{total}] {source}...")

    if search_mode == "📝 Búsqueda libre" and raw_query:
        from polymer_pipeline.dict import build_boolean_query
        custom_groups = [{"name": "custom", "terms": raw_query.split(" OR ")}]
        articles = run_pipeline(
            levels=["custom"],
            sources=selected_sources,
            max_results=max_results,
            progress_callback=update_progress,
        )
    else:
        articles = run_pipeline(
            levels=selected_levels or ["L1", "L2", "L3", "L4"],
            sources=selected_sources,
            max_results=max_results,
            progress_callback=update_progress,
        )

    progress_bar.empty()
    status_text.empty()

    # Guardar en session_state
    st.session_state["articles"] = articles
    st.session_state["ran"] = True

# Cargar artículos
articles = st.session_state.get("articles", [])
has_data = len(articles) > 0

if not has_data:
    st.info("👈 Configura los parámetros y haz clic en **Ejecutar Pipeline** para comenzar.")
    st.stop()

# Aplicar filtros de visualización
filtered = filter_articles(
    articles,
    query=search_filter,
    year_range=year_range,
    sources=filter_by_source,
    levels=filter_by_level,
)

# ── Métricas ───────────────────────────────────────────────────────────
st.subheader("📊 Resumen")

metrics = compute_quality_metrics(filtered)
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("📄 Total", metrics["total"])
c2.metric("🔗 Con DOI", f"{metrics['with_doi']}", f"{metrics['with_doi']/max(metrics['total'],1)*100:.0f}%")
c3.metric("📝 Con Abstract", f"{metrics['with_abstract']}", f"{metrics['with_abstract']/max(metrics['total'],1)*100:.0f}%")
c4.metric("📎 Con PDF", f"{metrics['with_pdf']}", f"{metrics['with_pdf']/max(metrics['total'],1)*100:.0f}%")
c5.metric("👤 Autor Desc.", f"{metrics['unknown_author']}", f"{metrics['unknown_author']/max(metrics['total'],1)*100:.0f}%")

# ── Gráficas ───────────────────────────────────────────────────────────
st.subheader("📈 Análisis Visual")

plots = generate_interactive_plots(filtered)

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📅 Por Año", "📚 Revistas", "🔤 Keywords", "🌐 Fuentes", "🏷️ Niveles"])

with tab1:
    st.plotly_chart(plots["year"], use_container_width=True)
with tab2:
    st.plotly_chart(plots["journals"], use_container_width=True)
with tab3:
    st.plotly_chart(plots["keywords"], use_container_width=True)
with tab4:
    st.plotly_chart(plots["sources"], use_container_width=True)
with tab5:
    st.plotly_chart(plots["levels"], use_container_width=True)

# ── Tabla de resultados ────────────────────────────────────────────────
st.subheader(f"📋 Resultados ({len(filtered)} artículos)")

display_df = pd.DataFrame(filtered)
if not display_df.empty:
    display_cols = ["level", "title", "author", "journal", "year", "source", "doi"]
    display_df = display_df[[c for c in display_cols if c in display_df.columns]]

    st.dataframe(
        display_df,
        use_container_width=True,
        column_config={
            "level": st.column_config.TextColumn("Nivel", width="small"),
            "title": st.column_config.TextColumn("Título", width="large"),
            "doi": st.column_config.LinkColumn("DOI", display_text="🔗"),
        },
        height=500,
    )

    # Export
    st.subheader("📥 Exportar")
    col_exp1, col_exp2, col_exp3 = st.columns(3)
    with col_exp1:
        if st.button("📄 Exportar CSV"):
            path = export_csv(filtered, filepath="/tmp/export.csv")
            st.success(f"CSV exportado")
    with col_exp2:
        if st.button("📚 Exportar BibTeX"):
            path = export_bibtex(filtered, filepath="/tmp/export.bib")
            st.success(f"BibTeX exportado")
    with col_exp3:
        json_str = json.dumps(filtered, indent=2, ensure_ascii=False)
        st.download_button(
            "💾 Descargar JSON",
            data=json_str,
            file_name="polymer_results.json",
            mime="application/json",
        )
else:
    st.warning("No se encontraron resultados con los filtros actuales.")
