import os
import json
import time
import requests
import webbrowser
from xml.etree import ElementTree as ET
from dotenv import load_dotenv
from dict import SEARCH_QUERIES
from filters import passes_filter

# Cargar variables de entorno
load_dotenv(dotenv_path="API_KEY.env")


TOTAL_RESULTS_PER_QUERY = 100
BATCH_SIZE = 25


SLEEP_BETWEEN_BATCHES = 0.5

# API Keys
ELSEVIER_API_KEY = os.getenv("ELSEVIER_API_KEY")
SPRINGER_API_KEY = os.getenv("SPRINGER_META_API_KEY")
CROSSREF_EMAIL = os.getenv("CROSSREF_POLITE_EMAIL", "ssabogal@unal.edu.co")


def fetch_crossref(query):
    """Obtiene artículos de Crossref, paginando con 'offset' hasta
    TOTAL_RESULTS_PER_QUERY o hasta agotar los resultados disponibles."""
    url = "https://api.crossref.org/works"
    headers = {
        "User-Agent": f"PolymerDataPipeline/1.0 (mailto:{CROSSREF_EMAIL})"
    }

    normalized = []
    offset = 0

    while offset < TOTAL_RESULTS_PER_QUERY:
        params = {
            "query": query,
            "rows": BATCH_SIZE,
            "offset": offset
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)

            if response.status_code == 429:
                print(f"[Crossref] 429 en offset={offset}. Pausando 5s y saltando este lote.")
                time.sleep(5)
                offset += BATCH_SIZE  # avanzamos igual, para no quedar atascados en el mismo lote
                continue

            if response.status_code != 200:
                print(f"[Crossref] Error {response.status_code} en offset={offset}. Se omite este lote.")
                offset += BATCH_SIZE
                continue

            data = response.json()
            message = data.get("message", {})
            items = message.get("items", [])

            # Si la API ya no devuelve items, no hay más que paginar.
            if not items:
                break

            for item in items:
                title = item.get("title", [""])[0] if item.get("title") else "Sin título"
                doi = item.get("DOI", "").lower().strip()
                journal = item.get("container-title", [""])[0] if item.get("container-title") else "No disponible"

                authors = item.get("author", [])
                author = "Desconocido"
                if authors:
                    given = authors[0].get("given", "")
                    family = authors[0].get("family", "")
                    author = f"{given} {family}".strip() or "Desconocido"

                year = ""
                if "published-print" in item:
                    year = str(item["published-print"]["date-parts"][0][0])
                elif "published-online" in item:
                    year = str(item["published-online"]["date-parts"][0][0])

                normalized.append({
                    "title": title,
                    "author": author,
                    "journal": journal,
                    "year": year,
                    "doi": doi,
                    "source": "Crossref"
                })

            # Si Crossref reporta menos resultados totales de los que ya
            # acumulamos, no tiene sentido seguir pidiendo más lotes.
            total_results = message.get("total-results", 0)
            if len(normalized) >= total_results:
                break

            offset += BATCH_SIZE
            time.sleep(SLEEP_BETWEEN_BATCHES)

        except Exception as e:
            print(f"[Crossref] Falló la petición en offset={offset}: {e}")
            offset += BATCH_SIZE
            continue

    return normalized


def fetch_springer(query):
    """Obtiene artículos de Springer, paginando con 's' (¡1-indexado!)
    hasta TOTAL_RESULTS_PER_QUERY o hasta agotar los resultados."""
    if not SPRINGER_API_KEY:
        print("[Springer] Saltando: No se configuró SPRINGER_META_API_KEY en API_KEY.env")
        return []

    url = "https://api.springernature.com/meta/v2/json"

    normalized = []
    start = 1  # Springer empieza a contar en 1, no en 0

    while (start - 1) < TOTAL_RESULTS_PER_QUERY:
        params = {
            "q": query,
            "p": BATCH_SIZE,
            "s": start,
            "api_key": SPRINGER_API_KEY
        }

        try:
            response = requests.get(url, params=params, timeout=15)

            if response.status_code == 429:
                print(f"[Springer] 429 en s={start}. Pausando 5s y saltando este lote.")
                time.sleep(5)
                start += BATCH_SIZE
                continue

            if response.status_code != 200:
                print(f"[Springer] Error {response.status_code} en s={start}. Se omite este lote.")
                start += BATCH_SIZE
                continue

            data = response.json()
            records = data.get("records", [])

            if not records:
                break

            for record in records:
                title = record.get("title", "Sin título")
                doi = record.get("doi", "").lower().strip()
                journal = record.get("publicationName", "No disponible")

                creators = record.get("creators", [])
                author = creators[0].get("creator", "Desconocido") if creators else "Desconocido"

                pub_date = record.get("publicationDate", "")
                year = pub_date[:4] if pub_date else ""

                normalized.append({
                    "title": title,
                    "author": author,
                    "journal": journal,
                    "year": year,
                    "doi": doi,
                    "source": "Springer"
                })

            # El total real disponible viene en result[0]["total"] (string)
            result_info = data.get("result", [{}])
            total_results = int(result_info[0].get("total", 0)) if result_info else 0
            if len(normalized) >= total_results:
                break

            start += BATCH_SIZE
            time.sleep(SLEEP_BETWEEN_BATCHES)

        except Exception as e:
            print(f"[Springer] Falló la petición en s={start}: {e}")
            start += BATCH_SIZE
            continue

    return normalized


def fetch_elsevier(query):
    """Obtiene artículos de Scopus (Elsevier), paginando con 'start'
    hasta TOTAL_RESULTS_PER_QUERY o hasta agotar los resultados."""
    if not ELSEVIER_API_KEY:
        print("[Elsevier] Saltando: No se configuró ELSEVIER_API_KEY en API_KEY.env")
        return []

    url = "https://api.elsevier.com/content/search/scopus"
    headers = {
        "X-ELS-APIKey": ELSEVIER_API_KEY,
        "Accept": "application/json"
    }

    normalized = []
    start_index = 0

    while start_index < TOTAL_RESULTS_PER_QUERY:
        params = {
            "query": query,
            "count": BATCH_SIZE,
            "start": start_index
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)

            if response.status_code == 429:
                print(f"[Elsevier] 429 en start={start_index}. Pausando 5s y saltando este lote.")
                time.sleep(5)
                start_index += BATCH_SIZE
                continue

            if response.status_code != 200:
                print(f"[Elsevier] Error {response.status_code} en start={start_index}. Se omite este lote.")
                start_index += BATCH_SIZE
                continue

            data = response.json()
            search_results = data.get("search-results", {})
            entries = search_results.get("entry", [])

            if not entries or "error" in entries[0]:
                break

            for entry in entries:
                title = entry.get("dc:title", "Sin título")
                author = entry.get("dc:creator", "Desconocido")
                journal = entry.get("prism:publicationName", "No disponible")

                cover_date = entry.get("prism:coverDate", "")
                year = cover_date[:4] if cover_date else ""

                doi = entry.get("prism:doi", "").lower().strip()

                normalized.append({
                    "title": title,
                    "author": author,
                    "journal": journal,
                    "year": year,
                    "doi": doi,
                    "source": "Elsevier"
                })

            total_results = int(search_results.get("opensearch:totalResults", 0))
            if len(normalized) >= total_results:
                break

            start_index += BATCH_SIZE
            time.sleep(SLEEP_BETWEEN_BATCHES)

        except Exception as e:
            print(f"[Elsevier] Falló la petición en start={start_index}: {e}")
            start_index += BATCH_SIZE
            continue

    return normalized

# =====================================================================
# Generación de HTML Dashboard
# =====================================================================

def generate_dashboard(results):
    """Genera una página HTML moderna, elegante e interactiva con los resultados consolidado."""
    
 
    total_articles = len(results)
    l1_count = sum(1 for r in results if r["level"] == "L1")
    l2_count = sum(1 for r in results if r["level"] == "L2")
    l3_count = sum(1 for r in results if r["level"] == "L3")
    l4_count = sum(1 for r in results if r["level"] == "L4")
    
    crossref_count = sum(1 for r in results if r["source"] == "Crossref")
    springer_count = sum(1 for r in results if r["source"] == "Springer")
    elsevier_count = sum(1 for r in results if r["source"] == "Elsevier")

    # Serializar resultados a JSON de forma segura para usar en Javascript
    results_json = json.dumps(results, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Polymer Data Pipeline Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-dark: #0f172a;
            --card-bg: rgba(30, 41, 59, 0.7);
            --border-color: rgba(255, 255, 255, 0.08);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent-primary: #38bdf8;
            --accent-glow: rgba(56, 189, 248, 0.15);
            
            --badge-l1: #10b981;
            --badge-l2: #f59e0b;
            --badge-l3: #3b82f6;
            --badge-l4: #ec4899;
            
            --source-crossref: #8b5cf6;
            --source-springer: #f43f5e;
            --source-elsevier: #0ea5e9;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg-dark);
            color: var(--text-main);
            min-height: 100vh;
            overflow-x: hidden;
            background-image: radial-gradient(circle at 10% 20%, rgba(14, 165, 233, 0.05) 0%, transparent 40%),
                              radial-gradient(circle at 90% 80%, rgba(139, 92, 246, 0.05) 0%, transparent 40%);
            background-attachment: fixed;
            padding: 2rem;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}

        header {{
            margin-bottom: 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 1.5rem;
        }}

        .logo-section h1 {{
            font-size: 2.2rem;
            font-weight: 700;
            background: linear-gradient(135deg, #38bdf8 0%, #8b5cf6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.5px;
        }}

        .logo-section p {{
            color: var(--text-muted);
            font-size: 0.95rem;
            margin-top: 0.2rem;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}

        .stat-card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.25rem;
            backdrop-filter: blur(12px);
            transition: transform 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease;
            position: relative;
            overflow: hidden;
        }}

        .stat-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 4px;
            height: 100%;
            background: var(--accent-primary);
            opacity: 0.7;
        }}

        .stat-card.l1::before {{ background: var(--badge-l1); }}
        .stat-card.l2::before {{ background: var(--badge-l2); }}
        .stat-card.l3::before {{ background: var(--badge-l3); }}
        .stat-card.l4::before {{ background: var(--badge-l4); }}

        .stat-card:hover {{
            transform: translateY(-4px);
            border-color: rgba(56, 189, 248, 0.3);
            box-shadow: 0 8px 30px var(--accent-glow);
        }}

        .stat-card .label {{
            font-size: 0.85rem;
            color: var(--text-muted);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .stat-card .value {{
            font-size: 2rem;
            font-weight: 700;
            margin-top: 0.5rem;
        }}

        /* Seccion de Control y Busqueda */
        .controls-card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.5rem;
            backdrop-filter: blur(12px);
            margin-bottom: 2rem;
        }}

        .search-row {{
            display: flex;
            gap: 1rem;
            align-items: center;
            flex-wrap: wrap;
        }}

        .search-box {{
            flex: 1;
            min-width: 300px;
            position: relative;
        }}

        .search-box input {{
            width: 100%;
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 0.8rem 1rem 0.8rem 2.8rem;
            color: var(--text-main);
            font-family: inherit;
            font-size: 1rem;
            transition: all 0.3s ease;
        }}

        .search-box input:focus {{
            outline: none;
            border-color: var(--accent-primary);
            box-shadow: 0 0 15px rgba(56, 189, 248, 0.15);
        }}

        .search-box::before {{
            content: '🔍';
            position: absolute;
            left: 1rem;
            top: 50%;
            transform: translateY(-50%);
            font-size: 1rem;
            opacity: 0.5;
        }}

        .filter-group {{
            display: flex;
            gap: 0.5rem;
            align-items: center;
            flex-wrap: wrap;
        }}

        .filter-btn {{
            background: rgba(51, 65, 85, 0.4);
            border: 1px solid var(--border-color);
            color: var(--text-main);
            padding: 0.6rem 1.2rem;
            border-radius: 10px;
            font-family: inherit;
            font-size: 0.9rem;
            cursor: pointer;
            transition: all 0.2s ease;
        }}

        .filter-btn:hover {{
            background: rgba(51, 65, 85, 0.8);
            border-color: rgba(255,255,255,0.2);
        }}

        .filter-btn.active {{
            background: var(--accent-primary);
            border-color: var(--accent-primary);
            color: #0f172a;
            font-weight: 600;
        }}

        /* Tabla de Resultados */
        .results-container {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            overflow: hidden;
            backdrop-filter: blur(12px);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        }}

        .table-scroll {{
            overflow-x: auto;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }}

        th {{
            background: rgba(15, 23, 42, 0.5);
            padding: 1.2rem 1.5rem;
            font-weight: 600;
            font-size: 0.9rem;
            color: var(--text-muted);
            border-bottom: 1px solid var(--border-color);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        td {{
            padding: 1.2rem 1.5rem;
            border-bottom: 1px solid var(--border-color);
            font-size: 0.95rem;
            vertical-align: middle;
        }}

        tr:last-child td {{
            border-bottom: none;
        }}

        tr:hover td {{
            background: rgba(255, 255, 255, 0.02);
        }}

        .title-col {{
            font-weight: 600;
            color: var(--text-main);
            max-width: 500px;
            word-wrap: break-word;
        }}

        .doi-link {{
            color: var(--accent-primary);
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 0.3rem;
            transition: color 0.2s ease;
        }}

        .doi-link:hover {{
            color: #7dd3fc;
            text-decoration: underline;
        }}

        /* Badges de Lógica */
        .badge {{
            display: inline-block;
            padding: 0.35rem 0.7rem;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            text-align: center;
        }}

        .badge.l1 {{ background: rgba(16, 185, 129, 0.15); color: var(--badge-l1); border: 1px solid rgba(16, 185, 129, 0.3); }}
        .badge.l2 {{ background: rgba(245, 158, 11, 0.15); color: var(--badge-l2); border: 1px solid rgba(245, 158, 11, 0.3); }}
        .badge.l3 {{ background: rgba(59, 130, 246, 0.15); color: var(--badge-l3); border: 1px solid rgba(59, 130, 246, 0.3); }}
        .badge.l4 {{ background: rgba(236, 72, 153, 0.15); color: var(--badge-l4); border: 1px solid rgba(236, 72, 153, 0.3); }}

        .badge.src-crossref {{ background: rgba(139, 92, 246, 0.15); color: var(--source-crossref); border: 1px solid rgba(139, 92, 246, 0.3); }}
        .badge.src-springer {{ background: rgba(244, 63, 94, 0.15); color: var(--source-springer); border: 1px solid rgba(244, 63, 94, 0.3); }}
        .badge.src-elsevier {{ background: rgba(14, 165, 233, 0.15); color: var(--source-elsevier); border: 1px solid rgba(14, 165, 233, 0.3); }}

        .empty-state {{
            padding: 4rem 2rem;
            text-align: center;
            color: var(--text-muted);
        }}

        .empty-state h3 {{
            color: var(--text-main);
            margin-bottom: 0.5rem;
        }}

        /* Responsive Layout */
        @media (max-width: 768px) {{
            body {{
                padding: 1rem;
            }}
            .search-row {{
                flex-direction: column;
                align-items: stretch;
            }}
            .filter-group {{
                justify-content: flex-start;
            }}
        }}
    </style>
</head>
<body>

<div class="container">
    <header>
        <div class="logo-section">
            <h1>Polymer Data Pipeline</h1>
            <p>Dashboard de Artículos Consolidados y Deduplicados</p>
        </div>
    </header>

    <!-- Indicadores de métricas -->
    <div class="stats-grid">
        <div class="stat-card">
            <div class="label">Total Artículos</div>
            <div class="value" id="stat-total">{total_articles}</div>
        </div>
        <div class="stat-card l1">
            <div class="label">Level 1 (Blends)</div>
            <div class="value" id="stat-l1">{l1_count}</div>
        </div>
        <div class="stat-card l2">
            <div class="label">Level 2 (Aditivos)</div>
            <div class="value" id="stat-l2">{l2_count}</div>
        </div>
        <div class="stat-card l3">
            <div class="label">Level 3 (Empaques)</div>
            <div class="value" id="stat-l3">{l3_count}</div>
        </div>
        <div class="stat-card l4">
            <div class="label">Level 4 (Biodegradables)</div>
            <div class="value" id="stat-l4">{l4_count}</div>
        </div>
    </div>

    <!-- Controles interactivos -->
    <div class="controls-card">
        <div class="search-row">
            <div class="search-box">
                <input type="text" id="search-input" placeholder="Buscar por título, autor, revista, DOI..." oninput="filterData()">
            </div>
            
            <div class="filter-group">
                <button class="filter-btn active" id="btn-all-lvl" onclick="filterLevel('ALL', this)">Todos los Niveles</button>
                <button class="filter-btn" onclick="filterLevel('L1', this)">Level 1</button>
                <button class="filter-btn" onclick="filterLevel('L2', this)">Level 2</button>
                <button class="filter-btn" onclick="filterLevel('L3', this)">Level 3</button>
                <button class="filter-btn" onclick="filterLevel('L4', this)">Level 4</button>
            </div>

            <div class="filter-group">
                <button class="filter-btn active" id="btn-all-src" onclick="filterSource('ALL', this)">Todas las APIs</button>
                <button class="filter-btn" onclick="filterSource('Crossref', this)">Crossref</button>
                <button class="filter-btn" onclick="filterSource('Springer', this)">Springer</button>
                <button class="filter-btn" onclick="filterSource('Elsevier', this)">Elsevier</button>
            </div>
        </div>
    </div>

    <!-- Tabla principal -->
    <div class="results-container">
        <div class="table-scroll">
            <table id="articles-table">
                <thead>
                    <tr>
                        <th style="width: 80px;">Nivel</th>
                        <th>Título</th>
                        <th>Autor Principal</th>
                        <th>Revista</th>
                        <th style="width: 80px;">Año</th>
                        <th style="width: 120px;">Fuente</th>
                        <th>DOI / Enlace</th>
                    </tr>
                </thead>
                <tbody id="table-body">
                    <!-- Los datos se inyectarán de forma dinámica mediante JavaScript -->
                </tbody>
            </table>
        </div>
        <div id="empty-message" class="empty-state" style="display: none;">
            <h3>No se encontraron resultados</h3>
            <p>Intenta ajustar la búsqueda o los filtros seleccionados.</p>
        </div>
    </div>
</div>

<script>
    // Inyección de los resultados unificados
    const dataset = {results_json};

    let activeLevel = 'ALL';
    let activeSource = 'ALL';

    function initTable() {{
        renderTable(dataset);
    }}

    function renderTable(data) {{
        const tbody = document.getElementById("table-body");
        const emptyMsg = document.getElementById("empty-message");
        tbody.innerHTML = "";

        if (data.length === 0) {{
            emptyMsg.style.display = "block";
            return;
        }} else {{
            emptyMsg.style.display = "none";
        }}

        data.forEach(item => {{
            const tr = document.createElement("tr");

            // Nivel badge
            const levelClass = item.level.toLowerCase();
            const levelBadge = `<span class="badge ${{levelClass}}">${{item.level}}</span>`;

            // Fuente badge
            const sourceClass = `src-${{item.source.toLowerCase()}}`;
            const sourceBadge = `<span class="badge ${{sourceClass}}">${{item.source}}</span>`;

            // DOI link
            const doiHtml = item.doi 
                ? `<a class="doi-link" href="https://doi.org/${{item.doi}}" target="_blank">🔗 ${{item.doi}}</a>` 
                : '<span style="color:var(--text-muted); font-style:italic;">No disponible</span>';

            tr.innerHTML = `
                <td>${{levelBadge}}</td>
                <td class="title-col">${{item.title}}</td>
                <td>${{item.author}}</td>
                <td>${{item.journal}}</td>
                <td>${{item.year || 'N/A'}}</td>
                <td>${{sourceBadge}}</td>
                <td>${{doiHtml}}</td>
            `;
            tbody.appendChild(tr);
        }});
    }}

    function filterLevel(level, btn) {{
        // Limpiar estilos de botones de nivel
        const buttons = btn.parentElement.querySelectorAll(".filter-btn");
        buttons.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");

        activeLevel = level;
        filterData();
    }}

    function filterSource(source, btn) {{
        // Limpiar estilos de botones de fuente
        const buttons = btn.parentElement.querySelectorAll(".filter-btn");
        buttons.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");

        activeSource = source;
        filterData();
    }}

    function filterData() {{
        const searchQuery = document.getElementById("search-input").value.toLowerCase().trim();

        const filtered = dataset.filter(item => {{
            const matchesLevel = activeLevel === 'ALL' || item.level === activeLevel;
            const matchesSource = activeSource === 'ALL' || item.source === activeSource;
            
            const matchesSearch = !searchQuery || 
                item.title.toLowerCase().includes(searchQuery) ||
                item.author.toLowerCase().includes(searchQuery) ||
                item.journal.toLowerCase().includes(searchQuery) ||
                item.doi.toLowerCase().includes(searchQuery);

            return matchesLevel && matchesSource && matchesSearch;
        }});

        // Actualizar contadores
        document.getElementById("stat-total").innerText = filtered.length;
        document.getElementById("stat-l1").innerText = filtered.filter(i => i.level === 'L1').length;
        document.getElementById("stat-l2").innerText = filtered.filter(i => i.level === 'L2').length;
        document.getElementById("stat-l3").innerText = filtered.filter(i => i.level === 'L3').length;
        document.getElementById("stat-l4").innerText = filtered.filter(i => i.level === 'L4').length;

        renderTable(filtered);
    }}

    // Iniciar
    window.onload = initTable;
</script>

</body>
</html>
"""
    return html_content

# =====================================================================
# Pipeline de Ejecución Principal
# =====================================================================

def main():
    print("=" * 60)
    print(" INICIANDO PIPELINE DE BÚSQUEDA CIENTÍFICA CONSOLIDADA ")
    print("=" * 60)
    
    seen_dois = set()
    all_normalized_articles = []
    
    for level, queries in SEARCH_QUERIES.items():
        print(f"\n>>> Procesando nivel: {level}")
        
        for q in queries:
            print(f"  Consulta: {q[:80]}...")
            
            # 1. Búsqueda en Crossref
            print("    [1/3] Descargando de Crossref...")
            crossref_articles = fetch_crossref(q)
            
            # 2. Búsqueda en Springer
            print("    [2/3] Descargando de Springer...")
            springer_articles = fetch_springer(q)
            
            # 3. Búsqueda en Elsevier
            print("    [3/3] Descargando de Elsevier...")
            elsevier_articles = fetch_elsevier(q)
            
            # Mezclar todos los artículos de esta consulta
            combined_raw = crossref_articles + springer_articles + elsevier_articles

            # --- Filtro de validación posterior ---
            # No confiamos en que la query haya filtrado correctamente
            # (confirmado empíricamente: Crossref ignora AND/OR y trae
            # ruido de dominios no relacionados). Verificamos el título
            # de cada artículo contra la lógica real del nivel.
            combined = [art for art in combined_raw if passes_filter(art, level)]
            rejected_items = [art for art in combined_raw if not passes_filter(art, level)]

            if rejected_items:
                rejected_by_source = {}
                for art in rejected_items:
                    rejected_by_source[art["source"]] = rejected_by_source.get(art["source"], 0) + 1
                print(f"    [Filtro] Rechazados: {len(rejected_items)}/{len(combined_raw)} -> {rejected_by_source}")
            
            new_additions_count = 0
            duplicates_count = 0
            
            for art in combined:
                doi = art["doi"]
                
                # Regla de deduplicación: si tiene DOI, se filtra por DOI.
                # Si no tiene DOI (raro pero posible), se filtra por título.
                identifier = doi if doi else art["title"].lower().strip()
                
                if identifier not in seen_dois:
                    seen_dois.add(identifier)
                    art["level"] = level
                    all_normalized_articles.append(art)
                    new_additions_count += 1
                else:
                    duplicates_count += 1
                    
            print(f"  --> Agregados: {new_additions_count} nuevos | Duplicados omitidos: {duplicates_count}")

    # Guardar a JSON consolidado
    json_output_path = "consolidated_results.json"
    with open(json_output_path, "w", encoding="utf-8") as f:
        json.dump(all_normalized_articles, f, indent=4, ensure_ascii=False)
    print(f"\n[Éxito] Se guardaron {len(all_normalized_articles)} artículos unificados en {json_output_path}")

    # Generar Dashboard HTML
    html_content = generate_dashboard(all_normalized_articles)
    html_output_path = "dashboard.html"
    with open(html_output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[Éxito] Dashboard interactivo generado en {html_output_path}")
    
    # Abrir en navegador
    webbrowser.open(html_output_path)
    print("\n¡Proceso finalizado con éxito!")

if __name__ == "__main__":
    main()