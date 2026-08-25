# Plan de Escalabilidad: Polymer Data Pipeline

## Visión

Convertir el pipeline CLI one-shot en una plataforma de investigación interactiva,
manteniendo la rigurosidad científica pero con una experiencia de usuario moderna
y amigable para investigadores.

---

## Estado Actual (Baseline)

- **CLI one-shot:** `python main.py` ejecuta todo de golpe
- **Dashboard estático:** `dashboard.html` auto-generado, sin live updates
- **8 APIs:** Crossref, Springer, Elsevier, PubMed, OpenAlex, MDPI, SemanticScholar, Lens
- **2,268 artículos** deduplicados en 4 niveles (L1-L4)
- **4 gráficas matplotlib** estáticas (embeddadas como base64 PNG)
- **Export:** JSON, CSV, BibTeX (siempre completo, sin filtros)
- **Data quality:** Sin métricas visibles (autores "Desconocido", journals "No disponible")
- **PDF download:** Implementado pero deshabilitado

---

## FASE 1 — Streamlit App Interactiva (MVP)

### Objetivo

Crear una app Streamlit que reemplace el CLI como interfaz principal, ofreciendo
control granular sobre el pipeline y visualización interactiva de resultados.

### 1.1 Estructura de archivos

```
polymer-data-pipeline/
├── app.py                          # Entry point de Streamlit
├── main.py                         # CLI legacy (se mantiene como fallback)
├── src/
│   └── polymer_pipeline/
│       ├── pipeline.py             # Refactor: funciones reutilizables
│       ├── core.py                 # NUEVO: lógica de negocio extraída
│       ├── settings.py
│       ├── cache.py
│       ├── filters.py
│       ├── export.py
│       ├── models.py
│       ├── plots.py                # Refactor: Plotly en vez de matplotlib
│       ├── plots_interactive.py    # NUEVO: gráficas Plotly interactivas
│       ├── dashboard.py            # Se mantiene como fallback estático
│       ├── dict.py
│       ├── sources.py
│       ├── http.py
│       ├── query_builder.py
│       ├── downloader.py
│       └── fetchers/
│           ├── __init__.py
│           ├── crossref.py
│           ├── springer.py
│           ├── elsevier.py
│           ├── pubmed.py
│           ├── openalex.py
│           ├── openalex_base.py
│           ├── mdpi.py
│           ├── semantic_scholar.py
│           └── lens.py
├── pyproject.toml
├── .streamlit/
│   └── config.toml                 # NUEVO: config de Streamlit
└── requirements.txt                # NUEVO: para deployment
```

### 1.2 Módulo `core.py` — Lógica de negocio extraída

Extraer la lógica de `pipeline.py` en funciones puras que Streamlit pueda
llamar sin side effects:

```python
# Funciones principales:
def run_pipeline(
    levels: list[str],           # ["L1", "L2", "L3", "L4"]
    sources: list[str],          # ["Crossref", "PubMed", ...]
    max_results: int = 250,
    progress_callback: Callable | None = None,
) -> list[dict]:
    """Ejecuta el pipeline completo y devuelve artículos normalizados."""

def filter_articles(
    articles: list[dict],
    query: str = "",
    year_range: tuple[int, int] | None = None,
    sources: list[str] | None = None,
    levels: list[str] | None = None,
) -> list[dict]:
    """Filtra artículos según criterios del usuario."""

def compute_quality_metrics(articles: list[dict]) -> dict:
    """Calcula métricas de calidad de datos."""

def export_filtered(
    articles: list[dict],
    format: str = "csv",  # "csv" | "bibtex" | "json"
    filepath: str | None = None,
) -> str:
    """Exporta artículos filtrados y devuelve la ruta del archivo."""
```

### 1.3 `app.py` — Interfaz principal de Streamlit

#### Layout de la app

```
┌─────────────────────────────────────────────────────────┐
│  🧪 Polymer Data Pipeline                    [Ejecutar] │
├──────────────┬──────────────────────────────────────────┤
│  SIDEBAR     │  MAIN CONTENT                            │
│              │                                          │
│  ☑ L1 Blend │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐   │
│  ☑ L2 Adit. │  │Total │ │  L1  │ │  L2  │ │  L3  │   │
│  ☑ L3 Empaq.│  │2,268 │ │ 668  │ │ 605  │ │ 351  │   │
│  ☑ L4 Biode.│  └──────┘ └──────┘ └──────┘ └──────┘   │
│              │                                          │
│  ☑ Crossref  │  ┌─────────────────────────────────────┐ │
│  ☑ PubMed    │  │  GRÁFICA: Publicaciones por Año     │ │
│  ☑ Springer  │  │  (Plotly interactiva, zoom, hover)  │ │
│  ☐ MDPI      │  └─────────────────────────────────────┘ │
│              │                                          │
│  Max results │  ┌──────────────┐ ┌──────────────┐      │
│  [250    ]   │  │ Top Revistas │ │ Top Keywords │      │
│              │  │ (Plotly)     │ │ (Plotly)     │      │
│  Año desde   │  └──────────────┘ └──────────────┘      │
│  [2015  ]    │                                          │
│  Año hasta   │  ┌─────────────────────────────────────┐ │
│  [2026  ]    │  │  DATA QUALITY                       │ │
│              │  │  ✅ Con DOI: 94%  ⚠️ Sin abstract: 12%│ │
│  [📥 Export] │  └─────────────────────────────────────┘ │
│              │                                          │
│              │  ┌─────────────────────────────────────┐ │
│              │  │  TABLA (paginada, 50 por página)    │ │
│              │  │  🔍 [Buscar por título, autor...]   │ │
│              │  │  │ Nivel │ Título │ Autor │ Año │...│ │
│              │  └─────────────────────────────────────┘ │
└──────────────┴──────────────────────────────────────────┘
```

#### Componentes de la sidebar

```python
import streamlit as st

st.sidebar.header("⚙️ Configuración del Pipeline")

# Selectores de nivel
st.sidebar.subheader("Niveles de búsqueda")
levels = []
for level in LEVELS:
    if st.sidebar.checkbox(f"{level['label']} ({level['key']})", value=True):
        levels.append(level['key'])

# Selectores de fuente
st.sidebar.subheader("Fuentes (APIs)")
sources = []
for source_name, cfg in SOURCES.items():
    if st.sidebar.checkbox(source_name, value=True):
        sources.append(source_name)

# Parámetros
max_results = st.sidebar.slider(
    "Resultados por query", min_value=50, max_value=1000, value=250, step=50
)

# Botón de ejecución
run_pipeline = st.sidebar.button("🚀 Ejecutar Pipeline", type="primary")
```

#### Filtros de visualización (post-pipeline)

```python
st.sidebar.divider()
st.sidebar.header("🔍 Filtros de visualización")

# Búsqueda por texto
search_query = st.sidebar.text_input("Buscar por título, autor, DOI...")

# Filtro por año
year_min, year_max = st.sidebar.slider(
    "Rango de años", min_value=1990, max_value=2026, value=(2015, 2026)
)

# Filtro por fuente (post-filtrado)
selected_sources = st.sidebar.multiselect(
    "Filtrar por fuente", options=SOURCE_NAMES, default=SOURCE_NAMES
)
```

### 1.4 Gráficas interactivas con Plotly

```python
# plots_interactive.py

import plotly.express as px
import plotly.graph_objects as go

def plot_publications_by_year(df: pd.DataFrame) -> go.Figure:
    year_counts = df.groupby("year").size().reset_index(name="count")
    fig = px.line(year_counts, x="year", y="count",
                  title="Evolución de Publicaciones por Año",
                  markers=True)
    fig.update_traces(fill="tozeroy", line_color="#38bdf8")
    fig.update_layout(template="plotly_dark", paper_bgcolor="#0f172a")
    return fig

def plot_top_journals(df: pd.DataFrame, top_n: int = 10) -> go.Figure:
    journals = df["journal"].value_counts().head(top_n)
    fig = px.bar(x=journals.values, y=journals.index,
                 orientation="h",
                 title=f"Top {top_n} Revistas",
                 color_discrete_sequence=["#14b8a6"])
    fig.update_layout(template="plotly_dark", paper_bgcolor="#0f172a")
    return fig

def plot_source_distribution(df: pd.DataFrame) -> go.Figure:
    counts = df["source"].value_counts()
    fig = px.pie(values=counts.values, names=counts.index,
                 title="Distribución por Fuente",
                 color_discrete_sequence=[SOURCE_COLORS.get(s, "#fbbf24")
                                          for s in counts.index])
    fig.update_layout(template="plotly_dark", paper_bgcolor="#0f172a")
    return fig
```

### 1.5 Barra de progreso durante ejecución

```python
# En core.py:
def run_pipeline(levels, sources, max_results, progress_callback=None):
    tasks = _build_tasks(levels, sources, max_results)
    total = len(tasks)

    results_by_query = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(_fetch_task, *t): t for t in tasks}
        for i, future in enumerate(as_completed(futures)):
            result = future.result()
            key = (result["level"], result["query"])
            results_by_query.setdefault(key, []).append(result)
            if progress_callback:
                progress_callback(i + 1, total, result["source"])

    return _filter_and_dedupe(results_by_query)

# En app.py:
progress_bar = st.progress(0)
status_text = st.empty()

def update_progress(current, total, source):
    progress_bar.progress(current / total)
    status_text.text(f"[{current}/{total}] Consultando {source}...")

articles = run_pipeline(levels, sources, progress_callback=update_progress)
progress_bar.empty()
```

### 1.6 Tabla paginada con st.dataframe

```python
import streamlit as st

# DataFrame con columnas seleccionables
display_df = filtered_df[["level", "title", "author", "journal", "year", "source", "doi"]]

st.dataframe(
    display_df,
    use_container_width=True,
    column_config={
        "level": st.column_config.TextColumn("Nivel", width="small"),
        "title": st.column_config.TextColumn("Título", width="large"),
        "doi": st.column_config.LinkColumn("DOI", display_text="🔗"),
    },
    selection_mode="multi-row",  # Para export selectivo
    height=500,
)

# Botón de export basado en selección
if st.button("📥 Exportar seleccionados"):
    selected = st.session_state.selection
    export_filtered(selected_articles, format="csv")
```

### 1.7 Data Quality Panel

```python
def compute_quality_metrics(articles: list[dict]) -> dict:
    total = len(articles)
    return {
        "total": total,
        "with_doi": sum(1 for a in articles if a.get("doi")),
        "with_abstract": sum(1 for a in articles if a.get("abstract")),
        "with_pdf": sum(1 for a in articles if a.get("pdf_url")),
        "unknown_author": sum(1 for a in articles if a.get("author") == "Desconocido"),
        "unknown_journal": sum(1 for a in articles if a.get("journal") in ("No disponible", "Desconocido")),
    }

# En app.py:
metrics = compute_quality_metrics(filtered_articles)

col1, col2, col3, col4 = st.columns(4)
col1.metric("📄 Con DOI", f"{metrics['with_doi']}/{metrics['total']}",
            f"{metrics['with_doi']/metrics['total']*100:.0f}%")
col2.metric("📝 Con Abstract", f"{metrics['with_abstract']}/{metrics['total']}",
            f"{metrics['with_abstract']/metrics['total']*100:.0f}%")
col3.metric("🔗 Con PDF", f"{metrics['with_pdf']}/{metrics['total']}",
            f"{metrics['with_pdf']/metrics['total']*100:.0f}%")
col4.metric("👤 Autor Desconocido", f"{metrics['unknown_author']}",
            f"{metrics['unknown_author']/metrics['total']*100:.0f}%")
```

### 1.8 Configuración de Streamlit

```toml
# .streamlit/config.toml
[theme]
primaryColor = "#38bdf8"
backgroundColor = "#0f172a"
secondaryBackgroundColor = "#1e293b"
textColor = "#f8fafc"
font = "sans serif"

[server]
maxUploadSize = 10
enableCORS = false

[browser]
gatherUsageStats = false
```

### 1.9 Dependencias nuevas

```toml
# En pyproject.toml [project.dependencies]:
dependencies = [
    # ... existentes ...
    "streamlit>=1.30",
    "plotly>=5.18",
]
```

### 1.10 Comportamiento dual (CLI + App)

```python
# app.py - Entry point de Streamlit
import streamlit as st

st.set_page_config(
    page_title="Polymer Data Pipeline",
    page_icon="🧪",
    layout="wide",
)

# ... lógica de la app ...

# main.py - Se mantiene como CLI fallback
# Ahora importa de core.py en vez de tener toda la lógica
from polymer_pipeline.core import run_pipeline

if __name__ == "__main__":
    articles = run_pipeline(levels=["L1", "L2", "L3", "L4"], sources=SOURCE_NAMES)
    # ... export y plots ...
```

### 1.11 Sistema de búsquedas (3 modos)

El sistema actual tiene las búsquedas hardcodeadas en `dict.py`. El nuevo plan
ofrece 3 modos para que el usuario defina qué buscar.

#### Flujo general

```
                    ┌─────────────────┐
                    │  USUARIO ELIGE  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
         ┌────────┐    ┌──────────┐    ┌──────────┐
         │ PRESET │    │ RAW QUERY│    │ BUILDER  │
         │ L1-L4  │    │(textarea)│    │  (GUI)   │
         └───┬────┘    └────┬─────┘    └────┬─────┘
             │              │               │
             ▼              ▼               ▼
        dict.py        query_string    groups → query_string
             │              │               │
             └──────────────┼───────────────┘
                            ▼
                   ┌────────────────┐
                   │ query_builder  │  ← SIN CAMBIOS (ya es genérico)
                   │ .py traduce a  │
                   │ cada API       │
                   └───────┬────────┘
                           ▼
                   ┌────────────────┐
                   │ fetchers.exe-  │
                   │ cutan en       │
                   │ paralelo       │
                   └───────┬────────┘
                           ▼
                   ┌────────────────┐
                   │ filters.filtra │  ← Acepta rules como parámetro
                   │ por título     │
                   └───────┬────────┘
                           ▼
                   ┌────────────────┐
                   │ Resultados en  │
                   │ Streamlit      │
                   └────────────────┘
```

#### Modo 1 — Presets (como ahora, pero con UI)

Mantiene los 4 niveles predefinidos como "atajos". Un click y listo.

```python
# En la sidebar de Streamlit:
st.sidebar.subheader("📋 Presets de búsqueda")
for level in LEVELS:
    if st.sidebar.checkbox(f"{level['label']} ({level['key']})", value=True):
        selected_levels.append(level['key'])
```

#### Modo 2 — Búsqueda libre (raw query)

Un textarea donde el usuario escribe cualquier query booleana.
`query_builder.py` ya funciona con cualquier query — sin cambios.

```
Sidebar:
  📝 Búsqueda personalizada:
  ┌─────────────────────────────────────────────┐
  │ (lithium OR "lithium ion" OR LiFePO4) AND   │
  │ ("solid electrolyte" OR garnet OR sulfide)   │
  └─────────────────────────────────────────────┘

  Reglas de filtro (título debe contener):
  ☑ Grupo 1: lithium, "lithium ion", LiFePO4
  ☑ Grupo 2: "solid electrolyte", garnet, sulfide
```

#### Modo 3 — Constructor visual de queries (GUI)

Para usuarios que no quieren escribir boolean. Construye la query
y las filter rules automáticamente desde grupos de términos.

```
Sidebar:
  🔧 Constructor de consulta:

  Grupo 1 - Nombre: [Material    ]
  Términos: [lithium] [+] [lithium ion] [+] [LiFePO4] [+]

  Grupo 2 - Nombre: [Propiedad   ]
  Términos: [electrolyte] [+] [ionic conductivity] [+]

  Grupo 3 - Nombre: [Aplicación  ]
  Términos: [battery] [+] [储能] [+]

  Combinar con AND:  (●) AND  (○) OR

  Reglas de filtro (post-búsqueda):
  ☑ Requiere al menos 2 de 3 grupos en título
```

#### Cambios necesarios en el código

| Archivo | Cambio |
|---------|--------|
| `dict.py` | Se mantiene como presets, pero se agrega `build_query_from_groups()` para queries dinámicas |
| `query_builder.py` | **Sin cambios** — ya acepta cualquier query booleana |
| `filters.py` | Se refactoriza para aceptar `filter_rules` como parámetro en vez de importar de `dict.py` |
| `pipeline.py` | Se refactoriza para aceptar queries y rules como parámetros |
| `core.py` (nuevo) | Orquesta los 3 modos y pasa todo como parámetros |

#### Orquestación en `core.py`

```python
def run_search(mode: str, **kwargs) -> list[dict]:
    """
    mode="preset"   → usa LEVELS de dict.py
    mode="raw"      → usa la query del usuario
    mode="builder"  → construye query desde grupos
    """
    if mode == "preset":
        levels = kwargs["levels"]
        queries = {k: v for k, v in SEARCH_QUERIES.items() if k in levels}
        filter_rules = {k: v for k, v in LEVEL_FILTER_RULES.items() if k in levels}

    elif mode == "raw":
        raw_query = kwargs["query"]
        user_rules = kwargs.get("filter_groups", [])
        queries = {"custom": [raw_query]}
        filter_rules = {"custom": user_rules} if user_rules else {}

    elif mode == "builder":
        groups = kwargs["groups"]
        # groups = [{"name": "Material", "terms": ["lithium", ...]}, ...]
        bool_op = kwargs.get("bool_operator", "AND")
        raw_query = build_boolean_query(groups, bool_op)
        user_rules = [g["terms"] for g in groups]
        queries = {"custom": [raw_query]}
        filter_rules = {"custom": user_rules}

    return _execute_pipeline(queries, filter_rules)
```

#### Función auxiliar `build_boolean_query()`

```python
# En dict.py o core.py
def build_boolean_query(groups: list[dict], operator: str = "AND") -> str:
    """Construye una query booleana desde grupos de términos definidos por el usuario.

    groups = [
        {"name": "Material", "terms": ["lithium", "LiFePO4"]},
        {"name": "Propiedad", "terms": ["electrolyte", "conductivity"]},
    ]
    operator = "AND"

    Resultado: '(lithium OR "LiFePO4") AND (electrolyte OR conductivity)'
    """
    rendered_groups = []
    for group in groups:
        terms = group["terms"]
        or_parts = []
        for term in terms:
            if " " in term:
                or_parts.append(f'"{term}"')
            else:
                or_parts.append(term)
        rendered_groups.append("(" + " OR ".join(or_parts) + ")")
    return f" {operator} ".join(rendered_groups)
```

#### Guardado/carga de búsquedas

```python
# Presets guardados por el usuario
search_presets = {
    "polyester_barrier": {
        "mode": "preset",
        "levels": ["L1", "L2"],
    },
    "solid_electrolytes": {
        "mode": "builder",
        "groups": [
            {"name": "Material", "terms": ["lithium", "LiFePO4"]},
            {"name": "Propiedad", "terms": ["electrolyte", "conductivity"]},
        ],
        "bool_operator": "AND",
    },
    "bioplastics_china": {
        "mode": "raw",
        "query": '(PLA OR PHA OR "bioplastic") AND China',
        "filter_groups": [["PLA", "PHA", "bioplastic"]],
    },
}

# Se guardan en JSON local:
# ~/.polymer-pipeline/searches.json
```

#### UI de Streamlit para gestión de presets

```python
# Sidebar - Gestión de búsquedas guardadas
st.sidebar.subheader("💾 Búsquedas guardadas")
saved_searches = load_saved_searches()
selected_preset = st.sidebar.selectbox(
    "Cargar búsqueda:",
    options=["(nueva)"] + list(saved_searches.keys()),
)

if selected_preset != "(nueva)":
    preset = saved_searches[selected_preset]
    # Cargar configuración del preset en los widgets

# Botón para guardar la búsqueda actual
if st.sidebar.button("💾 Guardar búsqueda actual"):
    name = st.sidebar.text_input("Nombre de la búsqueda")
    if name:
        save_search(name, current_config)
```

---

## FASE 2 — FastAPI como API Programática

### Objetivo

Exponer el pipeline como REST API para que otros sistemas (notebooks, R scripts,
dashboards externos) puedan consumir los datos programáticamente.

### 2.1 Estructura de archivos

```
src/polymer_pipeline/
├── api.py              # NUEVO: FastAPI app
├── api_models.py       # NUEVO: Pydantic models para API
├── core.py             # Compartido con Streamlit
└── ...
```

### 2.2 Endpoints

```python
# api.py
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse

app = FastAPI(title="Polymer Data Pipeline API", version="2.0")

@app.get("/health")
async def health_check():
    return {"status": "ok", "articles_count": len(get_cached_articles())}

@app.get("/articles")
async def list_articles(
    level: str | None = Query(None, description="Filter by level (L1-L4)"),
    source: str | None = Query(None, description="Filter by source"),
    year_from: int | None = Query(None, description="Min publication year"),
    year_to: int | None = Query(None, description="Max publication year"),
    query: str | None = Query(None, description="Search in title/author/DOI"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
):
    """Lista artículos con filtros y paginación."""
    ...

@app.get("/articles/{doi:path}")
async def get_article(doi: str):
    """Obtiene un artículo específico por DOI."""
    ...

@app.get("/stats")
async def get_stats():
    """Estadísticas del dataset (conteos por nivel, fuente, año)."""
    ...

@app.get("/export/csv")
async def export_csv(
    level: str | None = None,
    source: str | None = None,
):
    """Exporta artículos filtrados como CSV."""
    ...

@app.get("/export/bib")
async def export_bibtex(
    level: str | None = None,
    source: str | None = None,
):
    """Exporta artículos filtrados como BibTeX."""
    ...

@app.post("/pipeline/run")
async def run_pipeline_endpoint(
    levels: list[str] = ["L1", "L2", "L3", "L4"],
    sources: list[str] = ["Crossref", "PubMed", "Springer"],
    max_results: int = 250,
):
    """Ejecuta el pipeline (solo admin)."""
    ...
```

### 2.3 Pydantic Models

```python
# api_models.py
from pydantic import BaseModel

class ArticleResponse(BaseModel):
    title: str
    author: str
    journal: str
    year: str
    doi: str
    source: str
    abstract: str
    pdf_url: str
    level: str

class PaginatedResponse(BaseModel):
    items: list[ArticleResponse]
    total: int
    page: int
    page_size: int
    pages: int

class StatsResponse(BaseModel):
    total: int
    by_level: dict[str, int]
    by_source: dict[str, int]
    by_year: dict[str, int]
    quality: dict[str, float]
```

### 2.4 Ejecución

```bash
# Desarrollo
uvicorn polymer_pipeline.api:app --reload --port 8000

# Producción
uvicorn polymer_pipeline.api:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## FASE 3 — Deployment y Collaboración

### 3.1 Docker

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY . .

EXPOSE 8501 8000

# Default: Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8501"]
```

```yaml
# docker-compose.yml
services:
  app:
    build: .
    ports:
      - "8501:8501"   # Streamlit
      - "8000:8000"   # FastAPI
    env_file:
      - .env
    volumes:
      - .cache:/app/.cache
      - ./downloads:/app/downloads
```

### 3.2 Deploy en Streamlit Cloud

```toml
# requirements.txt (generado desde pyproject.toml)
# Streamlit Cloud lee este archivo
streamlit>=1.30
plotly>=5.18
requests>=2.28
python-dotenv>=1.0
numpy>=1.24
pandas>=1.5
matplotlib>=3.7
```

Configuración en [share.streamlit.io](https://share.streamlit.io):
- Repository: `tu-usuario/polymer-data-pipeline`
- Main file: `app.py`
- Python version: 3.12

### 3.3 Deploy en HuggingFace Spaces

```yaml
# README.md (en la raíz, para HuggingFace)
---
title: Polymer Data Pipeline
emoji: 🧪
colorFrom: blue
colorTo: purple
sdk: streamlit
sdk_version: "1.30"
app_file: app.py
pinned: false
---
```

### 3.4 Cache con Redis (producción)

```python
# cache.py - Versión Redis
import redis
from polymer_pipeline.settings import CACHE_TTL

_redis = redis.Redis(host="localhost", port=6379, db=0)

def get_cached(key: str) -> list | None:
    data = _redis.get(f"pipeline:{key}")
    if data:
        return json.loads(data)
    return None

def set_cache(key: str, data: list) -> None:
    _redis.setex(f"pipeline:{key}", CACHE_TTL, json.dumps(data))
```

### 3.5 Autenticación básica

```python
# api.py
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_user = os.getenv("API_USER", "admin")
    correct_pass = os.getenv("API_PASS", "changeme")
    if credentials.username != correct_user or credentials.password != correct_pass:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    return credentials.username

@app.post("/pipeline/run")
async def run_pipeline_endpoint(..., user: str = Depends(verify_credentials)):
    ...
```

---

## Resumen de dependencias por fase

| Dependencia | Fase 1 | Fase 2 | Fase 3 |
|------------|--------|--------|--------|
| `streamlit>=1.30` | ✅ | ✅ | ✅ |
| `plotly>=5.18` | ✅ | ✅ | ✅ |
| `fastapi>=0.108` | — | ✅ | ✅ |
| `uvicorn[standard]>=0.25` | — | ✅ | ✅ |
| `pydantic>=2.5` | — | ✅ | ✅ |
| `redis>=5.0` | — | — | ✅ |
| `docker` | — | — | ✅ |

---

## Prioridad de implementación

1. **FASE 1** → Empezar inmediatamente (mayor valor inmediato)
2. **FASE 2** → Cuando necesites que otros consuman los datos
3. **FASE 3** → Cuando quieras compartir con otros investigadores

---

## Preguntas abiertas (para decidir antes de implementar)

- [ ] ¿Streamlit reemplaza `main.py` completamente o coexisten?
- [ ] ¿Plotly reemplaza matplotlib o mantenemos ambos?
- [ ] ¿El dashboard.html estático se mantiene como fallback?
- [ ] ¿Necesitamos deploy en la nube o solo local?
- [ ] ¿Autenticación en la app o es solo para uso local?
- [ ] ¿Los 3 modos de búsqueda (preset, raw, builder) se implementan todos en la Fase 1 o se agregan incrementalmente?
- [ ] ¿Las búsquedas guardadas se almacenan en JSON local o en una base de datos?
