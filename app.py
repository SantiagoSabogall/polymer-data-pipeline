"""Polymer Data Pipeline — App Streamlit interactiva.

Ejecutar con: streamlit run app.py
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
import sys
from pathlib import Path

import streamlit as st
import pandas as pd


def _run_async(coro):
    """Ejecuta un coroutine desde contexto sync, incluso con event loop activo."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Cargar API keys ANTES de importar polymer_pipeline
# (settings.py evalúa os.getenv() al importar, así que necesita las env vars listas)
from dotenv import load_dotenv
load_dotenv(
    dotenv_path=Path(__file__).parent / "API_KEY.env",
    override=True,
)

from polymer_pipeline.settings import load_settings
from polymer_pipeline.dict import LEVELS, SEARCH_QUERIES, build_boolean_query
from polymer_pipeline.sources import SOURCES, SOURCE_NAMES
from polymer_pipeline.core import run_pipeline, filter_articles, compute_quality_metrics
from polymer_pipeline.plots_interactive import generate_interactive_plots
from polymer_pipeline.export import export_csv, export_bibtex

load_settings()

# ── Persistencia de presets ────────────────────────────────────────────
PRESETS_DIR = Path.home() / ".polymer-pipeline"
PRESETS_FILE = PRESETS_DIR / "searches.json"


def _load_presets() -> dict:
    if PRESETS_FILE.exists():
        try:
            return json.loads(PRESETS_FILE.read_text("utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_presets(presets: dict) -> None:
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    PRESETS_FILE.write_text(json.dumps(presets, indent=2, ensure_ascii=False), encoding="utf-8")


# ── Page config ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SciSearch",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* Tabla de resultados */
    .stDataFrame td, .stDataFrame th {
        font-size: 15px !important;
    }
    [data-testid="stDataFrame"] td {
        font-size: 15px !important;
        line-height: 1.5;
    }
    [data-testid="stDataFrame"] th {
        font-size: 16px !important;
        font-weight: 600;
    }
    
    /* Metricas */
    [data-testid="stMetric"] {
        background-color: #1e293b;
        padding: 10px;
        border-radius: 8px;
    }
    
    /* Responsive: sidebar mas angosta en pantallas pequenas */
    @media (max-width: 768px) {
        section[data-testid="stSidebar"] {
            width: 280px !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Configuracion del Pipeline")

    # ── Gestión de presets guardados ────────────────────────────────────
    saved_presets = _load_presets()
    if saved_presets:
        st.subheader("Busquedas guardadas")
        preset_names = list(saved_presets.keys())
        selected_preset = st.selectbox("Cargar:", ["(nueva busqueda)"] + preset_names)
    else:
        selected_preset = "(nueva busqueda)"

    st.divider()

    # ── Modo de búsqueda ────────────────────────────────────────────────
    st.subheader("Modo de busqueda")
    search_mode = st.radio(
        "Seleccionar:",
        ["Presets (L1-L4)", "Busqueda libre", "Constructor visual"],
        label_visibility="collapsed",
        key="search_mode",
    )

    # ── Estado inicial desde preset guardado ────────────────────────────
    preset_data = saved_presets.get(selected_preset, {}) if selected_preset != "(nueva busqueda)" else {}

    # Inicializar variables (se definen en cada modo)
    selected_levels = None
    raw_query = None
    builder_groups = None
    bool_operator = "AND"
    custom_filter_groups = None
    use_filter = True

    # ── MODO 1: Presets ─────────────────────────────────────────────────
    if search_mode == "Presets (L1-L4)":
        st.subheader("Niveles de busqueda")
        default_levels = preset_data.get("levels", [l["key"] for l in LEVELS])
        selected_levels = []
        for level in LEVELS:
            if st.checkbox(
                f"{level['label']} ({level['key']})",
                value=level["key"] in default_levels,
                key=f"lvl_{level['key']}",
            ):
                selected_levels.append(level["key"])

        raw_query = None
        builder_groups = None
        bool_operator = "AND"

    # ── MODO 2: Búsqueda libre ──────────────────────────────────────────
    elif search_mode == "Busqueda libre":
        st.subheader("Query booleana")
        default_query = preset_data.get(
            "query",
            '(polyester OR PET) AND (barrier OR permeability)',
        )
        raw_query = st.text_area(
            "Escribe tu consulta:",
            value=default_query,
            height=120,
            help="Formato: (termino1 OR termino2) AND (termino3 OR termino4)",
        )

        # Opcional: reglas de filtro
        st.caption("Reglas de filtro (opcional, separa terminos con coma)")
        filter_input = st.text_input(
            "Filtrar titulos que contengan:",
            value=preset_data.get("filter_text", ""),
            placeholder="polyester, barrier, film",
        )
        custom_filter_groups = None
        if filter_input:
            terms = [t.strip() for t in filter_input.split(",") if t.strip()]
            if terms:
                custom_filter_groups = [terms]

        selected_levels = None
        builder_groups = None
        bool_operator = "AND"

    # ── MODO 3: Constructor visual ──────────────────────────────────────
    else:
        st.subheader("Constructor de consulta")

        # Cargar grupos desde preset o usar defaults
        default_groups = preset_data.get("groups", [
            {"name": "Grupo 1", "terms": ["polyester", "PET"]},
            {"name": "Grupo 2", "terms": ["barrier", "permeability"]},
        ])
        default_operator = preset_data.get("bool_operator", "AND")

        # Editor de grupos
        if "builder_groups" not in st.session_state:
            st.session_state["builder_groups"] = default_groups

        groups = st.session_state["builder_groups"]

        # Operador booleano
        bool_operator = st.radio(
            "Combinar grupos con:",
            ["AND", "OR"],
            index=0 if default_operator == "AND" else 1,
            horizontal=True,
        )

        # Renderizar cada grupo
        new_groups = []
        for i, group in enumerate(groups):
            with st.expander(f"Grupo {i+1}: {group['name']}", expanded=True):
                name = st.text_input("Nombre:", value=group["name"], key=f"gname_{i}")
                terms_str = st.text_area(
                    "Terminos (uno por linea):",
                    value="\n".join(group["terms"]),
                    height=80,
                    key=f"gterms_{i}",
                )
                terms = [t.strip() for t in terms_str.split("\n") if t.strip()]

                col_del, _ = st.columns([1, 4])
                with col_del:
                    if st.button("Eliminar", key=f"del_{i}"):
                        pass  # Se elimina abajo
                    else:
                        new_groups.append({"name": name, "terms": terms})

        # Solo mantener los grupos que no fueron eliminados
        groups = [g for g in new_groups if g["terms"]]

        col_add, col_preview = st.columns([1, 2])
        with col_add:
            if st.button("Agregar grupo"):
                groups.append({"name": f"Grupo {len(groups)+1}", "terms": []})

        # Preview de la query generada
        if groups and all(g["terms"] for g in groups):
            generated_query = build_boolean_query(groups, bool_operator)
            with col_preview:
                st.caption("Query generada:")
                st.code(generated_query, language=None)

        # Reglas de filtro
        st.caption("Filtrar titulos que contengan al menos 2 de los grupos:")
        use_filter = st.checkbox("Aplicar filtro de relevancia", value=True)

        st.session_state["builder_groups"] = groups
        raw_query = None
        builder_groups = groups if all(g["terms"] for g in groups) else None
        selected_levels = None

    # ── Fuentes (común a todos los modos) ───────────────────────────────
    st.divider()
    st.subheader("Fuentes (APIs)")
    default_sources = preset_data.get("sources", SOURCE_NAMES)
    selected_sources = []
    for source_name in SOURCES:
        if st.checkbox(source_name, value=source_name in default_sources, key=f"src_{source_name}"):
            selected_sources.append(source_name)

    # ── Parámetros ──────────────────────────────────────────────────────
    st.subheader("Parametros")
    max_results = st.slider(
        "Resultados por query",
        min_value=50, max_value=1000,
        value=preset_data.get("max_results", 250),
        step=50,
    )

    # ── Guardar preset ──────────────────────────────────────────────────
    st.divider()
    with st.expander("Guardar busqueda actual"):
        save_name = st.text_input("Nombre:", placeholder="mi_busqueda")
        if st.button("Guardar", width="stretch"):
            if save_name:
                preset_config = {
                    "mode": search_mode,
                    "sources": selected_sources,
                    "max_results": max_results,
                }
                if search_mode == "Presets (L1-L4)":
                    preset_config["levels"] = selected_levels
                elif search_mode == "Busqueda libre":
                    preset_config["query"] = raw_query or ""
                    preset_config["filter_text"] = filter_input if 'filter_input' in dir() else ""
                elif search_mode == "Constructor visual":
                    preset_config["groups"] = groups if 'groups' in dir() else []
                    preset_config["bool_operator"] = bool_operator

                saved = _load_presets()
                saved[save_name] = preset_config
                _save_presets(saved)
                st.success(f"Guardado: {save_name}")
                st.rerun()
            else:
                st.warning("Escribe un nombre")

    # ── Botón de ejecución ──────────────────────────────────────────────
    st.divider()
    run_clicked = st.button("Ejecutar Pipeline", type="primary", width="stretch")

    # ── Filtros de visualización ────────────────────────────────────────
    st.divider()
    st.header("Filtros de visualizacion")
    search_filter = st.text_input("Buscar en resultados:", placeholder="titulo, autor, DOI...")
    year_range = st.slider("Rango de anios", 1990, 2026, (2015, 2026))
    filter_by_source = st.multiselect("Filtrar por fuente:", SOURCE_NAMES, default=SOURCE_NAMES)
    available_levels = ["L1", "L2", "L3", "L4"] if search_mode == "Presets (L1-L4)" else ["custom"]
    filter_by_level = st.multiselect(
        "Filtrar por nivel:",
        available_levels,
        default=available_levels,
    )

# ── Main content ───────────────────────────────────────────────────────
st.title("SciSearch")
st.caption("Dashboard de articulos cientificos consolidados y deduplicados")

# ── Ejecutar pipeline ──────────────────────────────────────────────────
if run_clicked:
    # Barra de progreso y spinner
    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(current: int, total: int, source: str) -> None:
        progress_bar.progress(current / total, text=f"[{current}/{total}] Consultando {source}...")

    # Determinar qué ejecutar según el modo
    custom_queries = None
    custom_filter_rules = None

    logging.info(f"[DEBUG] search_mode={search_mode}")
    logging.info(f"[DEBUG] raw_query={raw_query}")
    logging.info(f"[DEBUG] builder_groups={builder_groups}")

    if search_mode == "Busqueda libre" and raw_query:
        custom_queries = {"custom": [raw_query]}
        if custom_filter_groups:
            custom_filter_rules = {"custom": custom_filter_groups}
        else:
            custom_filter_rules = {"custom": []}
        logging.info(f"[DEBUG] Modo busqueda libre: custom_queries={custom_queries}")

    elif search_mode == "Constructor visual":
        if builder_groups and all(g.get("terms") for g in builder_groups):
            generated_query = build_boolean_query(builder_groups, bool_operator)
            custom_queries = {"custom": [generated_query]}
            if use_filter:
                custom_filter_rules = {"custom": [g["terms"] for g in builder_groups]}
            else:
                custom_filter_rules = {"custom": []}
            logging.info(f"[DEBUG] Modo builder: query={generated_query}")
        else:
            logging.warning("[DEBUG] Builder: no groups with terms")

    else:
        logging.info(f"[DEBUG] Modo presets: levels={selected_levels}")

    logging.info(f"[DEBUG] custom_queries={custom_queries}")
    logging.info(f"[DEBUG] custom_filter_rules={custom_filter_rules}")

    # Ejecutar con spinner
    with st.spinner("Consultando APIs cientificas... Esto puede tomar 30-60 segundos."):
        try:
            articles = _run_async(run_pipeline(
                levels=None if custom_queries else (selected_levels or [l["key"] for l in LEVELS]),
                sources=selected_sources,
                max_results=max_results,
                progress_callback=update_progress,
                custom_queries=custom_queries,
                custom_filter_rules=custom_filter_rules,
            ))
            logging.info(f"[DEBUG] Pipeline returned {len(articles)} articles")
        except Exception as e:
            logging.error(f"[DEBUG] Pipeline error: {e}")
            error_msg = str(e)
            if "429" in error_msg or "rate" in error_msg.lower():
                st.error("Error: Limite de velocidad alcanzado. Intenta con menos fuentes o reduce maximo de resultados.")
            elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                st.error("Error: Tiempo de espera agotado. La API no respondio a tiempo. Intenta de nuevo.")
            elif "connection" in error_msg.lower() or "connect" in error_msg.lower():
                st.error("Error: No se pudo conectar a la API. Verifica tu conexion a internet.")
            else:
                st.error(f"Error en el pipeline: {error_msg[:200]}")
            articles = []

    progress_bar.empty()
    status_text.empty()

    st.session_state["articles"] = articles
    st.session_state["ran"] = True
    st.success(f"Pipeline completado: {len(articles)} articulos obtenidos")

# ── Cargar artículos ───────────────────────────────────────────────────
articles = st.session_state.get("articles", [])
has_data = len(articles) > 0

if not has_data:
    st.info("Configura los parametros y haz clic en **Ejecutar Pipeline** para comenzar.")
    st.stop()

# ── Aplicar filtros de visualización ───────────────────────────────────
# Si es query custom, no filtrar por level (los artículos tienen level="custom")
effective_levels = None
if search_mode == "Presets (L1-L4)":
    effective_levels = filter_by_level

filtered = filter_articles(
    articles,
    query=search_filter,
    year_range=year_range,
    sources=filter_by_source,
    levels=effective_levels,
)

# ── Métricas ───────────────────────────────────────────────────────────
st.subheader("Resumen")

metrics = compute_quality_metrics(filtered)
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total", metrics["total"])
c2.metric("Con DOI", f"{metrics['with_doi']}", f"{metrics['with_doi']/max(metrics['total'],1)*100:.0f}%")
c3.metric("Con Abstract", f"{metrics['with_abstract']}", f"{metrics['with_abstract']/max(metrics['total'],1)*100:.0f}%")
c4.metric("Con PDF", f"{metrics['with_pdf']}", f"{metrics['with_pdf']/max(metrics['total'],1)*100:.0f}%")
c5.metric("Autor Desc.", f"{metrics['unknown_author']}", f"{metrics['unknown_author']/max(metrics['total'],1)*100:.0f}%")



# ── Tabla de resultados ────────────────────────────────────────────────
st.subheader(f"Resultados ({len(filtered)} artículos)")

display_df = pd.DataFrame(filtered)
if not display_df.empty:
    display_cols = ["level", "title", "author", "journal", "year", "source", "doi"]
    display_df = display_df[[c for c in display_cols if c in display_df.columns]]

    event = st.dataframe(
        display_df,
        width="stretch",
        column_config={
            "level": st.column_config.TextColumn("Nivel", width="small"),
            "title": st.column_config.TextColumn("Título", width="large"),
            "doi": st.column_config.LinkColumn("DOI", display_text="link"),
        },
        height=400,
        selection_mode="multi-row",
        on_select="rerun",
        key="results_table",
    )

    # ── Artículos seleccionados ──────────────────────────────────────────
    selected_rows = event.selection.rows if event.selection else []
    if selected_rows:
        selected_articles = [filtered[i] for i in selected_rows]
        st.info(f"{len(selected_articles)} artículos seleccionados")

        # Exportar seleccionados
        col_sel1, col_sel2, col_sel3 = st.columns(3)
        with col_sel1:
            sel_csv = pd.DataFrame(selected_articles).to_csv(index=False)
            st.download_button(
                "Exportar seleccionados (CSV)",
                data=sel_csv,
                file_name="selected_articles.csv",
                mime="text/csv",
                key="export_selected_csv",
            )
        with col_sel2:
            from polymer_pipeline.export import export_bibtex as _export_bib
            import tempfile
            from pathlib import Path
            with tempfile.NamedTemporaryFile(suffix=".bib", delete=False) as tmp:
                _export_bib(selected_articles, filepath=tmp.name)
                bib_content = Path(tmp.name).read_text()
            st.download_button(
                "Exportar seleccionados (BibTeX)",
                data=bib_content,
                file_name="selected_articles.bib",
                mime="application/x-bibtex",
                key="export_selected_bib",
            )
        with col_sel3:
            sel_json = json.dumps(selected_articles, indent=2, ensure_ascii=False)
            st.download_button(
                "Exportar seleccionados (JSON)",
                data=sel_json,
                file_name="selected_articles.json",
                mime="application/json",
                key="export_selected_json",
            )

        # Detalle del primer artículo seleccionado (si hay 1 o más)
        if len(selected_articles) == 1:
            article = selected_articles[0]
        elif len(selected_articles) > 1:
            st.markdown("**Detalle del primer artículo seleccionado:**")
            article = selected_articles[0]
        else:
            article = None

        if article:
            st.divider()
            st.subheader("Detalle del artículo")

            col_main, col_side = st.columns([3, 1])

            with col_main:
                st.markdown(f"### {article.get('title', 'Sin título')}")

                info_cols = st.columns(3)
                with info_cols[0]:
                    st.markdown(f"**Autor:** {article.get('author', 'Desconocido')}")
                    st.markdown(f"**Año:** {article.get('year', 'N/A')}")
                with info_cols[1]:
                    st.markdown(f"**Revista:** {article.get('journal', 'No disponible')}")
                    st.markdown(f"**Fuente:** {article.get('source', 'N/A')}")
                with info_cols[2]:
                    st.markdown(f"**Nivel:** {article.get('level', 'N/A')}")

                abstract = article.get("abstract", "")
                if abstract:
                    with st.expander("Abstract", expanded=True):
                        st.markdown(abstract)
                else:
                    st.info("No hay abstract disponible para este artículo.")

            with col_side:
                st.markdown("### Enlaces")

                doi = article.get("doi", "")
                if doi:
                    st.link_button(
                        "Abrir DOI",
                        url=f"https://doi.org/{doi}",
                        width="stretch",
                    )

                pdf_url = article.get("pdf_url", "")
                if pdf_url:
                    st.link_button(
                        "Descargar PDF",
                        url=pdf_url,
                        width="stretch",
                    )
                else:
                    st.button("Sin PDF disponible", disabled=True, width="stretch")

            # Scholar
            if doi:
                st.link_button(
                    "Google Scholar",
                    url=f"https://scholar.google.com/scholar?q={doi}",
                    width="stretch",
                )

            # Semantic Scholar
            if article.get("title"):
                from urllib.parse import quote
                st.link_button(
                    "Semantic Scholar",
                    url=f"https://www.semanticscholar.org/search?q={quote(article['title'])}",
                    width="stretch",
                )



# ── Gráficas ───────────────────────────────────────────────────────────
st.subheader("Analisis Visual")

with st.spinner("Generando graficas..."):
    plots = generate_interactive_plots(filtered)

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Por Anio", "Revistas", "Keywords", "Fuentes", "Niveles"])

with tab1:
    st.plotly_chart(plots["year"], width="stretch")
with tab2:
    st.plotly_chart(plots["journals"], width="stretch")
with tab3:
    st.plotly_chart(plots["keywords"], width="stretch")
with tab4:
    st.plotly_chart(plots["sources"], width="stretch")
with tab5:
    st.plotly_chart(plots["levels"], width="stretch")

    

# Exportar todos los resultados
st.divider()
st.subheader("Exportar todos los resultados")
col_exp1, col_exp2, col_exp3 = st.columns(3)
with col_exp1:
    if st.button("Exportar CSV"):
        export_csv(filtered, filepath="/tmp/export.csv")
        st.success("CSV exportado")
with col_exp2:
    if st.button("Exportar BibTeX"):
        export_bibtex(filtered, filepath="/tmp/export.bib")
        st.success("BibTeX exportado")
with col_exp3:
    json_str = json.dumps(filtered, indent=2, ensure_ascii=False)
    st.download_button(
        "Descargar JSON",
        data=json_str,
        file_name="polymer_results.json",
        mime="application/json",
    )
