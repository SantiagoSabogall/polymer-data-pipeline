import json
import re
from collections import Counter

from polymer_pipeline.dict import LEVELS
from polymer_pipeline.sources import SOURCES

_LEVEL_NUM_RE = re.compile(r"^L(\d+)$")


def _hex_to_rgba(hex_color, alpha):
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha})"


def _level_display_name(level):
    match = _LEVEL_NUM_RE.match(level["key"])
    base = f"Level {match.group(1)}" if match else level["key"]
    return f"{base} ({level['label']})"


def _level_css(levels):
    var_lines = []
    stat_rules = []
    badge_rules = []
    for level in levels:
        cls = f"lvl-{level['key'].lower()}"
        color = level["color"]
        var_lines.append(f"--badge-{cls}: {color};")
        stat_rules.append(f".stat-card.{cls}::before {{ background: {color}; }}")
        badge_rules.append(
            f".badge.{cls} {{ background: {_hex_to_rgba(color, 0.15)}; "
            f"color: var(--badge-{cls}); border: 1px solid {_hex_to_rgba(color, 0.3)}; }}"
        )
    return (
        "\n            ".join(var_lines),
        "\n        ".join(stat_rules),
        "\n        ".join(badge_rules),
    )


def _stat_cards_html(level_counts, total_articles, levels):
    cards = [
        '<div class="stat-card">',
        '    <div class="label">Total Artículos</div>',
        f'    <div class="value" id="stat-total">{total_articles}</div>',
        "</div>",
    ]
    for level in levels:
        key = level["key"]
        cards.append(f'<div class="stat-card lvl-{key.lower()}">')
        cards.append(f'    <div class="label">{_level_display_name(level)}</div>')
        cards.append(
            f'    <div class="value" id="stat-{key.lower()}">'
            f'{level_counts.get(key, 0)}</div>'
        )
        cards.append("</div>")
    return "\n        ".join(cards)


def _level_buttons_html(levels):
    buttons = [
        '<button class="filter-btn active" id="btn-all-lvl" '
        'onclick="filterLevel(\'ALL\', this)">Todos los Niveles</button>'
    ]
    for level in levels:
        buttons.append(
            f"<button class=\"filter-btn\" "
            f"onclick=\"filterLevel('{level['key']}', this)\">"
            f"{_level_display_name(level)}</button>"
        )
    return "\n                ".join(buttons)


def _source_css():
    var_lines = []
    badge_rules = []
    for name, cfg in SOURCES.items():
        cls = name.lower()
        color = cfg["color"]
        var_lines.append(f"--source-{cls}: {color};")
        badge_rules.append(
            f".badge.src-{cls} {{ background: {_hex_to_rgba(color, 0.15)}; "
            f"color: var(--source-{cls}); border: 1px solid {_hex_to_rgba(color, 0.3)}; }}"
        )
    return "\n            ".join(var_lines), "\n        ".join(badge_rules)


def _source_buttons_html():
    buttons = [
        '<button class="filter-btn active" id="btn-all-src" '
        'onclick="filterSource(\'ALL\', this)">Todas las APIs</button>'
    ]
    for name in SOURCES:
        buttons.append(
            f'<button class="filter-btn" onclick="filterSource(\'{name}\', this)">{name}</button>'
        )
    return "\n                ".join(buttons)


def _source_stat_cards_html(results):
    counts = Counter(r.get("source") for r in results)
    cards = []
    for name in SOURCES:
        cls = name.lower()
        cards.append(f'<div class="stat-card" style="--accent-primary:var(--source-{cls})">')
        cards.append(f'    <div class="label">{name}</div>')
        cards.append(
            f'    <div class="value"'
            f' style="color:var(--source-{cls})">'
            f'{counts.get(name, 0)}</div>'
        )
        cards.append("</div>")
    return "\n        ".join(cards)


def generate_dashboard(results, plots=None):
    if plots is None:
        plots = {}
    total_articles = len(results)
    level_counts = Counter(r.get("level") for r in results)
    level_css_vars, level_stat_rules, level_badge_rules = _level_css(LEVELS)
    source_css_vars, source_badge_rules = _source_css()
    stats_cards_html = _stat_cards_html(level_counts, total_articles, LEVELS)
    source_stat_cards_html = _source_stat_cards_html(results)
    level_buttons_html = _level_buttons_html(LEVELS)
    source_buttons_html = _source_buttons_html()
    level_keys_json = json.dumps([level["key"].lower() for level in LEVELS])

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
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap"
          rel="stylesheet">
    <style>
        :root {{
            --bg-dark: #0f172a;
            --card-bg: rgba(30, 41, 59, 0.7);
            --border-color: rgba(255, 255, 255, 0.08);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent-primary: #38bdf8;
            --accent-glow: rgba(56, 189, 248, 0.15);

            {level_css_vars}

            {source_css_vars}
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
            background-image:
              radial-gradient(circle at 10% 20%, rgba(14, 165, 233, 0.05) 0%, transparent 40%),
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

        {level_stat_rules}

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
            background: rgba(148, 163, 184, 0.15);
            color: var(--text-muted);
            border: 1px solid rgba(148, 163, 184, 0.3);
        }}

        {level_badge_rules}

        {source_badge_rules}

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

        .title-cell {{
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
        }}

        .abstract-toggle {{
            background: rgba(56, 189, 248, 0.1);
            border: 1px solid rgba(56, 189, 248, 0.3);
            color: var(--accent-primary);
            padding: 0.25rem 0.6rem;
            border-radius: 6px;
            font-size: 0.7rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            display: inline-flex;
            align-items: center;
            gap: 0.3rem;
            width: fit-content;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .abstract-toggle:hover {{
            background: rgba(56, 189, 248, 0.2);
            border-color: rgba(56, 189, 248, 0.5);
        }}

        .abstract-toggle .arrow {{
            transition: transform 0.2s ease;
            font-size: 0.6rem;
        }}

        .abstract-toggle.open .arrow {{
            transform: rotate(90deg);
        }}

        .abstract-content {{
            display: none;
            background: rgba(15, 23, 42, 0.5);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 0.8rem;
            font-size: 0.85rem;
            color: var(--text-muted);
            line-height: 1.5;
            max-height: 200px;
            overflow-y: auto;
            margin-top: 0.3rem;
        }}

        .abstract-content.show {{
            display: block;
        }}

        .no-abstract {{
            font-style: italic;
            color: rgba(148, 163, 184, 0.5);
        }}

        .pdf-btn {{
            background: rgba(34, 197, 94, 0.1);
            border: 1px solid rgba(34, 197, 94, 0.3);
            color: #22c55e;
            padding: 0.25rem 0.6rem;
            border-radius: 6px;
            font-size: 0.7rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            display: inline-flex;
            align-items: center;
            gap: 0.3rem;
            text-decoration: none;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .pdf-btn:hover {{
            background: rgba(34, 197, 94, 0.2);
            border-color: rgba(34, 197, 94, 0.5);
        }}

        .pdf-btn.no-pdf {{
            opacity: 0.3;
            cursor: default;
            pointer-events: none;
        }}

        .title-actions {{
            display: flex;
            gap: 0.4rem;
            flex-wrap: wrap;
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
        {stats_cards_html}
        {source_stat_cards_html}
    </div>

    {charts_section_html}

    <div class="controls-card">
        <div class="search-row">
            <div class="search-box">
                <input type="text" id="search-input"
                       placeholder="Buscar por título, autor, revista, DOI..."
                       oninput="filterData()">
            </div>

            <div class="search-box" style="max-width: 400px;">
                <input type="text" id="title-search-input"
                       placeholder="Buscar palabra en títulos..."
                       oninput="filterData()">
            </div>

            <div class="filter-group">
                {level_buttons_html}
            </div>

            <div class="filter-group">
                {source_buttons_html}
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

    const levelKeys = {level_keys_json};

    let activeLevel = 'ALL';
    let activeSource = 'ALL';
    let activeTitleSearch = '';

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

            const levelClass = "lvl-" + item.level.toLowerCase();
            const levelBadge = `<span class="badge ${{levelClass}}">${{item.level}}</span>`;

            const sourceClass = `src-${{item.source.toLowerCase()}}`;
            const sourceBadge = `<span class="badge ${{sourceClass}}">${{item.source}}</span>`;

            const doiHtml = item.doi
                ? `<a class="doi-link"
                      href="https://doi.org/${{item.doi}}"
                      target="_blank">🔗 ${{item.doi}}</a>`
                : '<span style="color:var(--text-muted); font-style:italic;">No disponible</span>';

            const abstractId = "abstract-" + Math.random().toString(36).substr(2, 9);
            const hasAbstract = item.abstract && item.abstract.trim().length > 0;
            const abstractButtonHtml = hasAbstract
                ? `<button class="abstract-toggle"
                      onclick="toggleAbstract('${{abstractId}}', this)">
                     <span class="arrow">▶</span> Abstract
                   </button>`
                : `<span class="abstract-toggle" style="opacity:0.4; cursor:default;">
                     <span class="arrow">▶</span> Sin abstract
                   </span>`;
            const abstractContentHtml = hasAbstract
                ? `<div class="abstract-content" id="${{abstractId}}">${{item.abstract}}</div>`
                : '';

            const hasPdf = item.pdf_url && item.pdf_url.trim().length > 0;
            const pdfButtonHtml = hasPdf
                ? `<a class="pdf-btn" href="${{item.pdf_url}}" target="_blank">📄 PDF</a>`
                : `<span class="pdf-btn no-pdf">📄 Sin PDF</span>`;

            tr.innerHTML = `
                <td>${{levelBadge}}</td>
                <td class="title-cell">
                    <div>${{item.title}}</div>
                    <div class="title-actions">
                        ${{abstractButtonHtml}}
                        ${{pdfButtonHtml}}
                    </div>
                    ${{abstractContentHtml}}
                </td>
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
        const titleSearchQuery = document
            .getElementById("title-search-input")
            .value.toLowerCase().trim();

        const filtered = dataset.filter(item => {{
            const matchesLevel = activeLevel === 'ALL' || item.level === activeLevel;
            const matchesSource = activeSource === 'ALL' || item.source === activeSource;

            const matchesSearch = !searchQuery ||
                item.title.toLowerCase().includes(searchQuery) ||
                item.author.toLowerCase().includes(searchQuery) ||
                item.journal.toLowerCase().includes(searchQuery) ||
                item.doi.toLowerCase().includes(searchQuery);

            const matchesTitleSearch = !titleSearchQuery ||
                item.title.toLowerCase().includes(titleSearchQuery);

            return matchesLevel && matchesSource && matchesSearch && matchesTitleSearch;
        }});

        document.getElementById("stat-total").innerText = filtered.length;
        levelKeys.forEach(lk => {{
            const el = document.getElementById("stat-" + lk);
            if (el) el.innerText = filtered
                .filter(i => (i.level || "").toLowerCase() === lk)
                .length;
        }});

        renderTable(filtered);
    }}

    function toggleAbstract(id, btn) {{
        const content = document.getElementById(id);
        if (content) {{
            content.classList.toggle("show");
            btn.classList.toggle("open");
        }}
    }}

    window.onload = initTable;
</script>

</body>
</html>
"""
    return html_content
