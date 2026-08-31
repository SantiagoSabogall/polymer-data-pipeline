import json
import re
from collections import Counter

from polymer_pipeline._dashboard_assets import DASHBOARD_CSS, DASHBOARD_JS
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


def _build_css_vars(levels, results):
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

    for name, cfg in SOURCES.items():
        cls = name.lower()
        color = cfg["color"]
        var_lines.append(f"--source-{cls}: {color};")
        badge_rules.append(
            f".badge.src-{cls} {{ background: {_hex_to_rgba(color, 0.15)}; "
            f"color: var(--source-{cls}); border: 1px solid {_hex_to_rgba(color, 0.3)}; }}"
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


def generate_dashboard(results, plots=None):
    if plots is None:
        plots = {}
    total_articles = len(results)
    level_counts = Counter(r.get("level") for r in results)

    css_vars, stat_rules, badge_rules = _build_css_vars(LEVELS, results)

    css = DASHBOARD_CSS.format(
        css_vars=css_vars,
        stat_rules=stat_rules,
        badge_rules=badge_rules,
    )

    stats_cards = _stat_cards_html(level_counts, total_articles, LEVELS)
    source_stats = _source_stat_cards_html(results)
    level_buttons = _level_buttons_html(LEVELS)
    source_buttons = _source_buttons_html()
    level_keys_json = json.dumps([level["key"].lower() for level in LEVELS])
    results_json = json.dumps(results, ensure_ascii=False)

    chart_titles = {
        "year":     "Evolución de Publicaciones por Año",
        "journals": "Top 10 Revistas",
        "keywords": "Palabras Clave en Títulos",
        "sources":  "Distribución por Fuente",
    }

    charts_html = ""
    if plots:
        cards_html = ""
        for key, b64 in plots.items():
            title = chart_titles.get(key, key)
            cards_html += f'''
        <div class="chart-card">
            <div class="chart-title">{title}</div>
            <img src="data:image/png;base64,{b64}" alt="{title}" class="chart-img">
        </div>'''
        charts_html = f'''
    <div class="charts-section">
        <div class="section-title">Analisis Visual</div>
        <div class="charts-grid">{cards_html}
        </div>
    </div>'''

    js = DASHBOARD_JS.format(
        results_json=results_json,
        level_keys_json=level_keys_json,
    )

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Polymer Data Pipeline Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap"
          rel="stylesheet">
    <style>{css}</style>
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
        {stats_cards}
        {source_stats}
    </div>

    {charts_html}

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
                {level_buttons}
            </div>

            <div class="filter-group">
                {source_buttons}
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

<script>{js}</script>

</body>
</html>
"""
