import json


def generate_dashboard(results, plots=None):
    if plots is None:
        plots = {}
    total_articles = len(results)
    l1_count = sum(1 for r in results if r["level"] == "L1")
    l2_count = sum(1 for r in results if r["level"] == "L2")
    l3_count = sum(1 for r in results if r["level"] == "L3")
    l4_count = sum(1 for r in results if r["level"] == "L4")

    pubmed_count   = sum(1 for r in results if r["source"] == "PubMed")
    chemrxiv_count = sum(1 for r in results if r["source"] == "ChemRxiv")

    results_json = json.dumps(results, ensure_ascii=False)

    chart_titles = {
        "year":     "Evolución de Publicaciones por Año",
        "journals": "Top 10 Revistas",
        "keywords": "Palabras Clave en Títulos",
        "sources":  "Distribución por Fuente",
    }
    charts_section_html = ""
    if plots:
        cards_html = ""
        for key, b64 in plots.items():
            title = chart_titles.get(key, key)
            cards_html += f'''
        <div class="chart-card">
            <div class="chart-title">{title}</div>
            <img src="data:image/png;base64,{b64}" alt="{title}" class="chart-img">
        </div>'''
        charts_section_html = f'''
    <div class="charts-section">
        <div class="section-title">Analisis Visual</div>
        <div class="charts-grid">{cards_html}
        </div>
    </div>'''

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
            --source-pubmed: #22c55e;
            --source-chemrxiv: #fb923c;
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

        .badge.src-crossref  {{ background: rgba(139, 92, 246, 0.15); color: var(--source-crossref);  border: 1px solid rgba(139, 92, 246, 0.3); }}
        .badge.src-springer  {{ background: rgba(244, 63, 94, 0.15);  color: var(--source-springer);  border: 1px solid rgba(244, 63, 94, 0.3);  }}
        .badge.src-elsevier  {{ background: rgba(14, 165, 233, 0.15); color: var(--source-elsevier);  border: 1px solid rgba(14, 165, 233, 0.3); }}
        .badge.src-pubmed    {{ background: rgba(34, 197, 94, 0.15);  color: var(--source-pubmed);    border: 1px solid rgba(34, 197, 94, 0.3);  }}
        .badge.src-chemrxiv  {{ background: rgba(251, 146, 60, 0.15); color: var(--source-chemrxiv);  border: 1px solid rgba(251, 146, 60, 0.3); }}

        .empty-state {{
            padding: 4rem 2rem;
            text-align: center;
            color: var(--text-muted);
        }}

        .empty-state h3 {{
            color: var(--text-main);
            margin-bottom: 0.5rem;
        }}

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

        .charts-section {{
            margin-bottom: 2rem;
        }}

        .section-title {{
            font-size: 1.4rem;
            font-weight: 700;
            color: var(--text-main);
            margin-bottom: 1.2rem;
            padding-bottom: 0.6rem;
            border-bottom: 1px solid var(--border-color);
            letter-spacing: -0.3px;
        }}

        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
            gap: 1.5rem;
        }}

        .chart-card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.5rem;
            backdrop-filter: blur(12px);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}

        .chart-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 8px 30px var(--accent-glow);
        }}

        .chart-title {{
            font-size: 0.9rem;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 1rem;
        }}

        .chart-img {{
            width: 100%;
            height: auto;
            border-radius: 8px;
            display: block;
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
        <div class="stat-card" style="--accent-primary:var(--source-pubmed)">
            <div class="label">PubMed</div>
            <div class="value" style="color:var(--source-pubmed)">{pubmed_count}</div>
        </div>
        <div class="stat-card" style="--accent-primary:var(--source-chemrxiv)">
            <div class="label">ChemRxiv</div>
            <div class="value" style="color:var(--source-chemrxiv)">{chemrxiv_count}</div>
        </div>
    </div>

    {charts_section_html}

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
                <button class="filter-btn" onclick="filterSource('PubMed', this)">PubMed</button>
                <button class="filter-btn" onclick="filterSource('ChemRxiv', this)">ChemRxiv</button>
            </div>
        </div>
    </div>

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

            const levelClass = item.level.toLowerCase();
            const levelBadge = `<span class="badge ${{levelClass}}">${{item.level}}</span>`;

            const sourceClass = `src-${{item.source.toLowerCase()}}`;
            const sourceBadge = `<span class="badge ${{sourceClass}}">${{item.source}}</span>`;

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
        const buttons = btn.parentElement.querySelectorAll(".filter-btn");
        buttons.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");

        activeLevel = level;
        filterData();
    }}

    function filterSource(source, btn) {{
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

        document.getElementById("stat-total").innerText = filtered.length;
        document.getElementById("stat-l1").innerText = filtered.filter(i => i.level === 'L1').length;
        document.getElementById("stat-l2").innerText = filtered.filter(i => i.level === 'L2').length;
        document.getElementById("stat-l3").innerText = filtered.filter(i => i.level === 'L3').length;
        document.getElementById("stat-l4").innerText = filtered.filter(i => i.level === 'L4').length;

        renderTable(filtered);
    }}

    window.onload = initTable;
</script>

</body>
</html>
"""
    return html_content
