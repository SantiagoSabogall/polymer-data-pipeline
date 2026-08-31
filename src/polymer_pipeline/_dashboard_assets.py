"""CSS and JS constants for the static HTML dashboard."""

DASHBOARD_CSS = """
    :root {
        --bg-dark: #0f172a;
        --card-bg: rgba(30, 41, 59, 0.7);
        --border-color: rgba(255, 255, 255, 0.08);
        --text-main: #f8fafc;
        --text-muted: #94a3b8;
        --accent-primary: #38bdf8;
        --accent-glow: rgba(56, 189, 248, 0.15);
        {css_vars}
    }

    * { margin: 0; padding: 0; box-sizing: border-box; }

    body {
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
    }

    .container { max-width: 1400px; margin: 0 auto; }

    header {
        margin-bottom: 2rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid var(--border-color);
        padding-bottom: 1.5rem;
    }

    .logo-section h1 {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #38bdf8 0%, #8b5cf6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.5px;
    }

    .logo-section p { color: var(--text-muted); font-size: 0.95rem; margin-top: 0.2rem; }

    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 1rem;
        margin-bottom: 2rem;
    }

    .stat-card {
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 1.25rem;
        backdrop-filter: blur(12px);
        transition: transform 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease;
        position: relative;
        overflow: hidden;
    }

    .stat-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0;
        width: 4px; height: 100%;
        background: var(--accent-primary);
        opacity: 0.7;
    }

    {stat_rules}

    .stat-card:hover {
        transform: translateY(-4px);
        border-color: rgba(56, 189, 248, 0.3);
        box-shadow: 0 8px 30px var(--accent-glow);
    }

    .stat-card .label {
        font-size: 0.85rem; color: var(--text-muted);
        font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;
    }

    .stat-card .value { font-size: 2rem; font-weight: 700; margin-top: 0.5rem; }

    .controls-card {
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 1.5rem;
        backdrop-filter: blur(12px);
        margin-bottom: 2rem;
    }

    .search-row { display: flex; gap: 1rem; align-items: center; flex-wrap: wrap; }

    .search-box { flex: 1; min-width: 300px; position: relative; }

    .search-box input {
        width: 100%;
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 0.8rem 1rem 0.8rem 2.8rem;
        color: var(--text-main);
        font-family: inherit;
        font-size: 1rem;
        transition: all 0.3s ease;
    }

    .search-box input:focus {
        outline: none;
        border-color: var(--accent-primary);
        box-shadow: 0 0 15px rgba(56, 189, 248, 0.15);
    }

    .search-box::before {
        content: '\uD83D\uDD0D';
        position: absolute; left: 1rem; top: 50%;
        transform: translateY(-50%); font-size: 1rem; opacity: 0.5;
    }

    .filter-group { display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; }

    .filter-btn {
        background: rgba(51, 65, 85, 0.4);
        border: 1px solid var(--border-color);
        color: var(--text-main);
        padding: 0.6rem 1.2rem;
        border-radius: 10px;
        font-family: inherit; font-size: 0.9rem;
        cursor: pointer; transition: all 0.2s ease;
    }

    .filter-btn:hover { background: rgba(51, 65, 85, 0.8); border-color: rgba(255,255,255,0.2); }

    .filter-btn.active {
        background: var(--accent-primary);
        border-color: var(--accent-primary);
        color: #0f172a; font-weight: 600;
    }

    .results-container {
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        overflow: hidden;
        backdrop-filter: blur(12px);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
    }

    .table-scroll { overflow-x: auto; }

    table { width: 100%; border-collapse: collapse; text-align: left; }

    th {
        background: rgba(15, 23, 42, 0.5);
        padding: 1.2rem 1.5rem;
        font-weight: 600; font-size: 0.9rem;
        color: var(--text-muted);
        border-bottom: 1px solid var(--border-color);
        text-transform: uppercase; letter-spacing: 0.5px;
    }

    td {
        padding: 1.2rem 1.5rem;
        border-bottom: 1px solid var(--border-color);
        font-size: 0.95rem; vertical-align: middle;
    }

    tr:last-child td { border-bottom: none; }
    tr:hover td { background: rgba(255, 255, 255, 0.02); }

    .title-col {
        font-weight: 600; color: var(--text-main);
        max-width: 500px; word-wrap: break-word;
    }

    .doi-link {
        color: var(--accent-primary); text-decoration: none;
        display: inline-flex; align-items: center; gap: 0.3rem;
        transition: color 0.2s ease;
    }

    .doi-link:hover { color: #7dd3fc; text-decoration: underline; }

    .badge {
        display: inline-block;
        padding: 0.35rem 0.7rem;
        border-radius: 20px;
        font-size: 0.75rem; font-weight: 700;
        text-transform: uppercase; letter-spacing: 0.5px;
        text-align: center;
        background: rgba(148, 163, 184, 0.15);
        color: var(--text-muted);
        border: 1px solid rgba(148, 163, 184, 0.3);
    }

    {badge_rules}

    .empty-state { padding: 4rem 2rem; text-align: center; color: var(--text-muted); }
    .empty-state h3 { color: var(--text-main); margin-bottom: 0.5rem; }

    @media (max-width: 768px) {
        body { padding: 1rem; }
        .search-row { flex-direction: column; align-items: stretch; }
        .filter-group { justify-content: flex-start; }
    }

    .charts-section { margin-bottom: 2rem; }

    .section-title {
        font-size: 1.4rem; font-weight: 700;
        color: var(--text-main); margin-bottom: 1.2rem;
        padding-bottom: 0.6rem;
        border-bottom: 1px solid var(--border-color);
        letter-spacing: -0.3px;
    }

    .charts-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
        gap: 1.5rem;
    }

    .chart-card {
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 1.5rem;
        backdrop-filter: blur(12px);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }

    .chart-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 30px var(--accent-glow);
    }

    .chart-title {
        font-size: 0.9rem; font-weight: 600;
        color: var(--text-muted);
        text-transform: uppercase; letter-spacing: 0.5px;
        margin-bottom: 1rem;
    }

    .chart-img { width: 100%; height: auto; border-radius: 8px; display: block; }

    .title-cell { display: flex; flex-direction: column; gap: 0.4rem; }

    .abstract-toggle {
        background: rgba(56, 189, 248, 0.1);
        border: 1px solid rgba(56, 189, 248, 0.3);
        color: var(--accent-primary);
        padding: 0.25rem 0.6rem;
        border-radius: 6px;
        font-size: 0.7rem; font-weight: 600;
        cursor: pointer; transition: all 0.2s ease;
        display: inline-flex; align-items: center; gap: 0.3rem;
        width: fit-content;
        text-transform: uppercase; letter-spacing: 0.5px;
    }

    .abstract-toggle:hover {
        background: rgba(56, 189, 248, 0.2);
        border-color: rgba(56, 189, 248, 0.5);
    }

    .abstract-toggle .arrow { transition: transform 0.2s ease; font-size: 0.6rem; }
    .abstract-toggle.open .arrow { transform: rotate(90deg); }

    .abstract-content {
        display: none;
        background: rgba(15, 23, 42, 0.5);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 0.8rem;
        font-size: 0.85rem; color: var(--text-muted);
        line-height: 1.5; max-height: 200px;
        overflow-y: auto; margin-top: 0.3rem;
    }

    .abstract-content.show { display: block; }

    .no-abstract { font-style: italic; color: rgba(148, 163, 184, 0.5); }

    .pdf-btn {
        background: rgba(34, 197, 94, 0.1);
        border: 1px solid rgba(34, 197, 94, 0.3);
        color: #22c55e;
        padding: 0.25rem 0.6rem;
        border-radius: 6px;
        font-size: 0.7rem; font-weight: 600;
        cursor: pointer; transition: all 0.2s ease;
        display: inline-flex; align-items: center; gap: 0.3rem;
        text-decoration: none;
        text-transform: uppercase; letter-spacing: 0.5px;
    }

    .pdf-btn:hover {
        background: rgba(34, 197, 94, 0.2);
        border-color: rgba(34, 197, 94, 0.5);
    }

    .pdf-btn.no-pdf { opacity: 0.3; cursor: default; pointer-events: none; }

    .title-actions { display: flex; gap: 0.4rem; flex-wrap: wrap; }
"""

DASHBOARD_JS = """
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
                      target="_blank">\uD83D\uDD17 ${{item.doi}}</a>`
                : '<span style="color:var(--text-muted); font-style:italic;">No disponible</span>';

            const abstractId = "abstract-" + Math.random().toString(36).substr(2, 9);
            const hasAbstract = item.abstract && item.abstract.trim().length > 0;
            const abstractButtonHtml = hasAbstract
                ? `<button class="abstract-toggle"
                      onclick="toggleAbstract('${{abstractId}}', this)">
                     <span class="arrow">\u25B6</span> Abstract
                   </button>`
                : `<span class="abstract-toggle" style="opacity:0.4; cursor:default;">
                     <span class="arrow">\u25B6</span> Sin abstract
                   </span>`;
            const abstractContentHtml = hasAbstract
                ? `<div class="abstract-content" id="${{abstractId}}">${{item.abstract}}</div>`
                : '';

            const hasPdf = item.pdf_url && item.pdf_url.trim().length > 0;
            const pdfButtonHtml = hasPdf
                ? `<a class="pdf-btn" href="${{item.pdf_url}}" target="_blank">\uD83D\uDCC4 PDF</a>`
                : `<span class="pdf-btn no-pdf">\uD83D\uDCC4 Sin PDF</span>`;

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
"""
