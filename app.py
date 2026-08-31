"""Polymer Data Pipeline — App Streamlit interactiva.

Ejecutar con: streamlit run app.py
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import streamlit as st


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
from dotenv import load_dotenv

load_dotenv(
    dotenv_path=Path(__file__).parent / "API_KEY.env",
    override=True,
)

from polymer_pipeline.core import (
    compute_quality_metrics,
    filter_articles,
    run_pipeline,
)
from polymer_pipeline.dict import LEVELS, build_boolean_query
from polymer_pipeline.export import export_bibtex, export_csv
from polymer_pipeline.plots_interactive import generate_interactive_plots
from polymer_pipeline.settings import load_settings
from polymer_pipeline.sources import SOURCE_NAMES, SOURCES

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
    PRESETS_FILE.write_text(
        json.dumps(presets, indent=2, ensure_ascii=False), encoding="utf-8"
    )


# ── Page config ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SciSearch",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    .block-container { padding-top: 1.65rem !important; }
    h1 { margin-top: 0 !important; padding-top: 0 !important; }
    header[data-testid="stHeader"] { display: none; }
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
    [data-testid="stMetric"] {
        background-color: #1e293b;
        padding: 10px;
        border-radius: 8px;
    }
    @media (max-width: 768px) {
        section[data-testid="stSidebar"] {
            width: 280px !important;
        }
    }
    .article-detail {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 16px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<script>
document.addEventListener('keydown', function(e) {
    if (e.ctrlKey && e.key === 'Enter') {
        var btn = document.querySelector('button[kind="primary"]');
        if (btn) btn.click();
    }
    if (e.key === 'Escape') {
        var newBtn = Array.from(document.querySelectorAll('button'))
            .find(function(b) { return b.innerText.indexOf('Nueva b') !== -1; });
        if (newBtn) newBtn.click();
    }
});
</script>
""", unsafe_allow_html=True)

# ── Estado de sesión ──────────────────────────────────────────────────
if "articles" not in st.session_state:
    st.session_state["articles"] = []
if "search_mode_used" not in st.session_state:
    st.session_state["search_mode_used"] = "Presets (L1-L4)"

has_data = len(st.session_state["articles"]) > 0

# ════════════════════════════════════════════════════════════════════════
#  ESTADO 1: Búsqueda (no hay resultados)
# ════════════════════════════════════════════════════════════════════════
if not has_data:
    st.title("SciSearch")

    # ── Presets guardados ───────────────────────────────────────────
    saved_presets = _load_presets()
    preset_data = {}
    if saved_presets:
        preset_names = list(saved_presets.keys())
        selected_preset = st.selectbox(
            "Cargar búsqueda guardada:", ["(nueva)"] + preset_names
        )
        if selected_preset != "(nueva)":
            preset_data = saved_presets[selected_preset]

    # ── Modo de búsqueda ────────────────────────────────────────────
    search_mode = st.radio(
        "Modo de búsqueda:",
        ["Presets (L1-L4)", "Busqueda libre", "Constructor visual"],
        horizontal=True,
        key="search_mode",
    )

    # Inicializar variables
    selected_levels = None
    raw_query = None
    builder_groups = None
    bool_operator = "AND"
    custom_filter_groups = None
    use_filter = True
    filter_input = ""
    groups = []

    # ── MODO 1: Presets ─────────────────────────────────────────────
    if search_mode == "Presets (L1-L4)":
        st.subheader("Niveles de búsqueda")
        default_levels = preset_data.get(
            "levels", [lvl["key"] for lvl in LEVELS]
        )
        selected_levels = []
        cols = st.columns(2)
        for i, level in enumerate(LEVELS):
            with cols[i % 2]:
                if st.checkbox(
                    f"{level['label']} ({level['key']})",
                    value=level["key"] in default_levels,
                    key=f"lvl_{level['key']}",
                ):
                    selected_levels.append(level["key"])

    # ── MODO 2: Búsqueda libre ──────────────────────────────────────
    elif search_mode == "Busqueda libre":
        default_query = preset_data.get(
            "query",
            '(polyester OR PET) AND (barrier OR permeability)',
        )
        raw_query = st.text_area(
            "Escribe tu consulta booleana:",
            value=default_query,
            height=100,
            help="Formato: (termino1 OR termino2) AND (termino3 OR termino4)",
        )
        filter_input = st.text_input(
            "Filtrar títulos que contengan (opcional, coma separada):",
            value=preset_data.get("filter_text", ""),
            placeholder="polyester, barrier, film",
        )
        if filter_input:
            terms = [t.strip() for t in filter_input.split(",") if t.strip()]
            if terms:
                custom_filter_groups = [terms]

    # ── MODO 3: Constructor visual ──────────────────────────────────
    else:
        default_groups = preset_data.get("groups", [
            {"name": "Grupo 1", "terms": ["polyester", "PET"]},
            {"name": "Grupo 2", "terms": ["barrier", "permeability"]},
        ])
        default_operator = preset_data.get("bool_operator", "AND")

        if "builder_groups" not in st.session_state:
            st.session_state["builder_groups"] = default_groups

        groups = st.session_state["builder_groups"]

        bool_operator = st.radio(
            "Combinar grupos con:",
            ["AND", "OR"],
            index=0 if default_operator == "AND" else 1,
            horizontal=True,
        )

        new_groups = []
        for i, group in enumerate(groups):
            with st.expander(f"Grupo {i+1}: {group['name']}", expanded=True):
                name = st.text_input(
                    "Nombre:", value=group["name"], key=f"gname_{i}"
                )
                terms_str = st.text_area(
                    "Terminos (uno por línea):",
                    value="\n".join(group["terms"]),
                    height=80,
                    key=f"gterms_{i}",
                )
                terms = [
                    t.strip() for t in terms_str.split("\n") if t.strip()
                ]
                col_del, _ = st.columns([1, 4])
                with col_del:
                    if st.button("Eliminar", key=f"del_{i}"):
                        pass
                    else:
                        new_groups.append({"name": name, "terms": terms})

        groups = [g for g in new_groups if g["terms"]]

        col_add, col_preview = st.columns([1, 2])
        with col_add:
            if st.button("Agregar grupo"):
                groups.append(
                    {"name": f"Grupo {len(groups)+1}", "terms": []}
                )

        if groups and all(g["terms"] for g in groups):
            generated_query = build_boolean_query(groups, bool_operator)
            with col_preview:
                st.caption("Query generada:")
                st.code(generated_query, language=None)

        use_filter = st.checkbox("Aplicar filtro de relevancia", value=True)
        st.session_state["builder_groups"] = groups
        builder_groups = (
            groups if all(g["terms"] for g in groups) else None
        )

    # ── Fuentes + Parámetros ────────────────────────────────────────
    st.divider()
    col_sources, col_params = st.columns([2, 1])

    with col_sources:
        st.subheader("Fuentes")
        default_sources = preset_data.get("sources", SOURCE_NAMES)
        src_cols = st.columns(2)
        selected_sources = []
        for i, source_name in enumerate(SOURCES):
            with src_cols[i % 2]:
                if st.checkbox(
                    source_name,
                    value=source_name in default_sources,
                    key=f"src_{source_name}",
                ):
                    selected_sources.append(source_name)

    with col_params:
        st.subheader("Parámetros")
        max_results = st.slider(
            "Resultados por query",
            min_value=50,
            max_value=1000,
            value=preset_data.get("max_results", 250),
            step=50,
        )

    # ── Guardar preset ──────────────────────────────────────────────
    with st.expander("Guardar búsqueda actual"):
        save_cols = st.columns([2, 1])
        with save_cols[0]:
            save_name = st.text_input(
                "Nombre:", placeholder="mi_busqueda", label_visibility="collapsed"
            )
        with save_cols[1]:
            if st.button("Guardar"):
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
                        preset_config["filter_text"] = filter_input
                    elif search_mode == "Constructor visual":
                        preset_config["groups"] = groups
                        preset_config["bool_operator"] = bool_operator

                    saved = _load_presets()
                    saved[save_name] = preset_config
                    _save_presets(saved)
                    st.success(f"Guardado: {save_name}")
                    st.rerun()
                else:
                    st.warning("Escribe un nombre")

    # ── Ejecutar Pipeline ───────────────────────────────────────────
    st.divider()
    run_clicked = st.button(
        "Ejecutar Pipeline", type="primary", use_container_width=True
    )

    if run_clicked:
        progress_bar = st.progress(0)
        status_text = st.empty()

        def update_progress(current: int, total: int, source: str) -> None:
            progress_bar.progress(
                current / total,
                text=f"[{current}/{total}] Consultando {source}...",
            )

        custom_queries = None
        custom_filter_rules = None

        if search_mode == "Busqueda libre" and raw_query:
            custom_queries = {"custom": [raw_query]}
            if custom_filter_groups:
                custom_filter_rules = {"custom": custom_filter_groups}
            else:
                custom_filter_rules = {"custom": []}

        elif search_mode == "Constructor visual":
            if builder_groups and all(
                g.get("terms") for g in builder_groups
            ):
                generated_query = build_boolean_query(
                    builder_groups, bool_operator
                )
                custom_queries = {"custom": [generated_query]}
                if use_filter:
                    custom_filter_rules = {
                        "custom": [g["terms"] for g in builder_groups]
                    }
                else:
                    custom_filter_rules = {"custom": []}

        with st.spinner(
            "Consultando APIs científicas... Esto puede tomar 30-60 segundos."
        ):
            try:
                articles = _run_async(run_pipeline(
                    levels=(
                        None
                        if custom_queries
                        else (
                            selected_levels
                            or [lvl["key"] for lvl in LEVELS]
                        )
                    ),
                    sources=selected_sources,
                    max_results=max_results,
                    progress_callback=update_progress,
                    custom_queries=custom_queries,
                    custom_filter_rules=custom_filter_rules,
                ))
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "rate" in error_msg.lower():
                    st.error(
                        "Error: Límite de velocidad alcanzado. "
                        "Reduce fuentes o resultados."
                    )
                elif (
                    "timeout" in error_msg.lower()
                    or "timed out" in error_msg.lower()
                ):
                    st.error(
                        "Error: Tiempo de espera agotado. Intenta de nuevo."
                    )
                elif (
                    "connection" in error_msg.lower()
                    or "connect" in error_msg.lower()
                ):
                    st.error(
                        "Error: No se pudo conectar a la API."
                    )
                else:
                    st.error(f"Error en el pipeline: {error_msg[:200]}")
                articles = []

        progress_bar.empty()
        status_text.empty()

        st.session_state["articles"] = articles
        st.session_state["search_mode_used"] = search_mode
        st.rerun()

    st.stop()

# ════════════════════════════════════════════════════════════════════════
#  ESTADO 2: Resultados (sidebar con filtros + contenido principal)
# ════════════════════════════════════════════════════════════════════════
articles = st.session_state["articles"]
search_mode = st.session_state.get("search_mode_used", "Presets (L1-L4)")

# ── Sidebar: filtros de visualización ──────────────────────────────────
with st.sidebar:
    st.header("Filtros de visualización")
    search_filter = st.text_input(
        "Buscar en resultados:", placeholder="título, autor, DOI..."
    )
    year_range = st.slider("Rango de años", 1990, 2026, (2015, 2026))
    filter_by_source = st.multiselect(
        "Filtrar por fuente:", SOURCE_NAMES, default=SOURCE_NAMES
    )
    available_levels = (
        ["L1", "L2", "L3", "L4"]
        if search_mode == "Presets (L1-L4)"
        else ["custom"]
    )
    filter_by_level = st.multiselect(
        "Filtrar por nivel:", available_levels, default=available_levels
    )

# ── Main content ───────────────────────────────────────────────────────
st.title("SciSearch")

if st.button("Nueva búsqueda", use_container_width=True):
    st.session_state["articles"] = []
    st.rerun()

# ── Aplicar filtros ────────────────────────────────────────────────────
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


def _pct(v: int) -> str:
    return f"{v / max(metrics['total'], 1) * 100:.0f}%"


c2.metric("Con DOI", metrics["with_doi"], _pct(metrics["with_doi"]))
c3.metric(
    "Con Abstract", metrics["with_abstract"], _pct(metrics["with_abstract"])
)
c4.metric("Con PDF", metrics["with_pdf"], _pct(metrics["with_pdf"]))
c5.metric(
    "Autor Desc.",
    metrics["unknown_author"],
    _pct(metrics["unknown_author"]),
)

# ── Tabla de resultados + Detalle ──────────────────────────────────────
st.subheader(f"Resultados ({len(filtered)} artículos)")

display_df = pd.DataFrame(filtered)
if not display_df.empty:
    display_cols = [
        "level", "title", "author", "journal", "year", "source", "doi",
    ]
    display_df = display_df[
        [c for c in display_cols if c in display_df.columns]
    ]

    # Detectar si ya hay una selección previa en session_state
    _prev = st.session_state.get("results_table")
    _has_sel = False
    if _prev is not None and hasattr(_prev, "selection"):
        _has_sel = bool(_prev.selection and _prev.selection.rows)

    if _has_sel:
        col_table, col_detail = st.columns([3, 1])
    else:
        col_table = st.container()
        col_detail = None

    with col_table:
        event = st.dataframe(
            display_df,
            width="stretch",
            column_config={
                "level": st.column_config.TextColumn(
                    "Nivel", width="small"
                ),
                "title": st.column_config.TextColumn(
                    "Título", width="large"
                ),
                "doi": st.column_config.LinkColumn(
                    "DOI", display_text="link"
                ),
            },
            height=400,
            selection_mode="multi-row",
            on_select="rerun",
            key="results_table",
        )

    # ── Detalle del artículo seleccionado (columna derecha) ──────────
    selected_rows = event.selection.rows if event.selection else []

    if col_detail is not None and selected_rows:
        with col_detail:
            selected_articles = [filtered[i] for i in selected_rows]
            article = selected_articles[0]

            st.markdown(
                '<div class="article-detail">',
                unsafe_allow_html=True,
            )

            st.markdown(
                f"**{article.get('title', 'Sin título')}**"
            )

            info_md = (
                f"- **Autor:** {article.get('author', 'Desconocido')}\n"
                f"- **Año:** {article.get('year', 'N/A')}\n"
                f"- **Revista:** "
                f"{article.get('journal', 'No disponible')}\n"
                f"- **Fuente:** {article.get('source', 'N/A')}\n"
                f"- **Nivel:** {article.get('level', 'N/A')}"
            )
            st.markdown(info_md)

            doi = article.get("doi", "")
            if doi:
                st.link_button(
                    "Abrir DOI",
                    url=f"https://doi.org/{doi}",
                    use_container_width=True,
                )

            pdf_url = article.get("pdf_url", "")
            if pdf_url:
                st.link_button(
                    "Descargar PDF",
                    url=pdf_url,
                    use_container_width=True,
                )

            if doi:
                st.link_button(
                    "Google Scholar",
                    url=(
                        "https://scholar.google.com/scholar?q={doi}"
                    ),
                    use_container_width=True,
                )
            if article.get("title"):
                st.link_button(
                    "Semantic Scholar",
                    url=(
                        "https://www.semanticscholar.org/search?q="
                        f"{quote(article['title'])}"
                    ),
                    use_container_width=True,
                )

            abstract = article.get("abstract", "")
            if abstract:
                with st.expander("Abstract", expanded=False):
                    st.markdown(abstract)

            if len(selected_articles) > 1:
                st.caption(
                    f"+{len(selected_articles) - 1} artículos más "
                    f"seleccionados"
                )

            st.markdown("</div>", unsafe_allow_html=True)

    elif col_detail is not None and not selected_rows:
        with col_detail:
            st.markdown(
                '<div class="article-detail" style="opacity:0.5;">'
                "<p>Selecciona un artículo para ver sus detalles.</p>"
                "</div>",
                unsafe_allow_html=True,
            )

    # ── Exportar seleccionados (debajo de la tabla) ──────────────────
    if selected_rows:
        sel_articles = [filtered[i] for i in selected_rows]
        exp_cols = st.columns(3)
        with exp_cols[0]:
            sel_csv = pd.DataFrame(sel_articles).to_csv(index=False)
            st.download_button(
                "CSV seleccionados",
                data=sel_csv,
                file_name="selected_articles.csv",
                mime="text/csv",
                key="export_selected_csv",
            )
        with exp_cols[1]:
            from polymer_pipeline.export import (
                export_bibtex as _export_bib,
            )

            with tempfile.NamedTemporaryFile(
                suffix=".bib", delete=False
            ) as tmp:
                _export_bib(sel_articles, filepath=tmp.name)
                bib_content = Path(tmp.name).read_text()
            st.download_button(
                "BibTeX seleccionados",
                data=bib_content,
                file_name="selected_articles.bib",
                mime="application/x-bibtex",
                key="export_selected_bib",
            )
        with exp_cols[2]:
            sel_json = json.dumps(
                sel_articles, indent=2, ensure_ascii=False
            )
            st.download_button(
                "JSON seleccionados",
                data=sel_json,
                file_name="selected_articles.json",
                mime="application/json",
                key="export_selected_json",
            )

# ── Gráficas ───────────────────────────────────────────────────────────
st.subheader("Análisis Visual")

with st.spinner("Generando gráficas..."):
    plots = generate_interactive_plots(filtered)

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Por Año", "Revistas", "Keywords", "Fuentes", "Niveles"]
)
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

# ── Exportar todos ─────────────────────────────────────────────────────
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
