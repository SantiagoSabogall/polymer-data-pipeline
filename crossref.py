import requests
import webbrowser

# =====================================================
# Configuración
# =====================================================

QUERY = "andromeda"

TOTAL_RESULTS = 100
CHUNK_SIZE = 25

URL = "https://api.crossref.org/works"

all_records = []

headers = {
    "User-Agent":
    "PolymerDataPipeline/1.0 (mailto:sabogal@unal.edu.co)"
}

for offset in range(0, TOTAL_RESULTS, CHUNK_SIZE):

    params = {
        "query": QUERY,
        "rows": CHUNK_SIZE,
        "offset": offset
    }

    print(
        f"Descargando registros "
        f"{offset+1}-{offset+CHUNK_SIZE}"
    )

    
    response = requests.get(
    URL,
    params=params,
    headers=headers
            )

    if response.status_code != 200:
        raise Exception(
            f"Error {response.status_code}\n"
            f"{response.text}"
        )

    data = response.json()

    items = data["message"]["items"]

    if not items:
        break

    all_records.extend(items)

print(f"\nTotal recolectados: {len(all_records)}")

# =====================================================
# Construcción HTML
# =====================================================

rows = ""

for article in all_records:

    title = ""

    if article.get("title"):
        title = article["title"][0]

    journal = ""

    if article.get("container-title"):
        journal = article["container-title"][0]

    doi = article.get("DOI", "")

    year = ""

    if "published-print" in article:
        year = str(
            article["published-print"]
            ["date-parts"][0][0]
        )

    elif "published-online" in article:
        year = str(
            article["published-online"]
            ["date-parts"][0][0]
        )

    author = "Desconocido"

    authors = article.get("author", [])

    if authors:

        given = authors[0].get("given", "")

        family = authors[0].get("family", "")

        author = f"{given} {family}"

    doi_html = ""

    if doi:
        doi_html = (
            f'<a href="https://doi.org/{doi}" '
            f'target="_blank">{doi}</a>'
        )

    rows += f"""
    <tr>
        <td>{title}</td>
        <td>{author}</td>
        <td>{journal}</td>
        <td>{year}</td>
        <td>{doi_html}</td>
    </tr>
    """

# =====================================================
# HTML
# =====================================================

html = f"""
<!DOCTYPE html>
<html>

<head>

<meta charset="utf-8">

<title>Resultados Crossref</title>

<style>

body {{
    font-family: Arial;
    margin: 20px;
}}

table {{
    border-collapse: collapse;
    width: 100%;
}}

th, td {{
    border: 1px solid #ddd;
    padding: 8px;
}}

th {{
    background-color: #2f5d8c;
    color: white;
}}

tr:nth-child(even) {{
    background-color: #f4f4f4;
}}

a {{
    text-decoration: none;
}}

</style>

</head>

<body>

<h2>Resultados Crossref para "{QUERY}"</h2>

<p>
<b>Total mostrados:</b>
{len(all_records)}
</p>

<table>

<tr>
    <th>Título</th>
    <th>Autor principal</th>
    <th>Revista</th>
    <th>Año</th>
    <th>DOI</th>
</tr>

{rows}

</table>

</body>
</html>
"""

# =====================================================
# Guardar HTML
# =====================================================

output_file = "crossref_results.html"

with open(
    output_file,
    "w",
    encoding="utf-8"
) as f:
    f.write(html)

print(f"\nArchivo generado: {output_file}")

webbrowser.open(output_file)