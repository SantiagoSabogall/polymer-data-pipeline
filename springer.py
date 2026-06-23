import os
import requests
import webbrowser
from dotenv import load_dotenv

# =====================================================
# Cargar API Key
# =====================================================

load_dotenv("API_KEY.env")

API_KEY = os.getenv("SPRINGER_META_API_KEY")

if not API_KEY:
    raise ValueError(
        "No se encontró SPRINGER_META_API_KEY en API_KEY.env"
    )

# =====================================================
# Configuración de búsqueda
# =====================================================

QUERY = "andromeda"

TOTAL_RESULTS = 100
CHUNK_SIZE = 25

URL = "https://api.springernature.com/meta/v2/json"

all_records = []

# =====================================================
# Descarga de resultados
# =====================================================

for start in range(1, TOTAL_RESULTS + 1, CHUNK_SIZE):

    params = {
        "q": QUERY,
        "p": CHUNK_SIZE,
        "s": start,
        "api_key": API_KEY
    }

    print(
        f"Descargando registros {start} - "
        f"{min(start + CHUNK_SIZE - 1, TOTAL_RESULTS)}..."
    )

    response = requests.get(URL, params=params)

    if response.status_code != 200:
        raise Exception(
            f"Error {response.status_code}\n{response.text}"
        )

    data = response.json()

    records = data.get("records", [])

    if not records:
        print("No se encontraron más registros.")
        break

    all_records.extend(records)

print(f"\nTotal de artículos recolectados: {len(all_records)}")

# =====================================================
# Construcción de tabla HTML
# =====================================================

rows = ""

for article in all_records:

    title = article.get("title", "Sin título")

    journal = article.get(
        "publicationName",
        "No disponible"
    )

    doi = article.get("doi", "")

    publication_date = article.get(
        "publicationDate",
        ""
    )

    year = publication_date[:4] if publication_date else ""

    creators = article.get("creators", [])

    if creators:
        author = creators[0].get(
            "creator",
            "Desconocido"
        )
    else:
        author = "Desconocido"

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
# HTML final
# =====================================================

html = f"""
<!DOCTYPE html>
<html lang="es">

<head>
<meta charset="utf-8">

<title>Resultados Springer</title>

<style>

body {{
    font-family: Arial, sans-serif;
    color: #323232;
    margin: 20px;
}}

h2 {{
    color: #005b96;
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
    background-color: #005b96;
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

<h2>Resultados Springer para "{QUERY}"</h2>

<p>
<b>Total de artículos mostrados:</b>
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

output_file = "springer_results.html"

with open(output_file, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\nArchivo generado: {output_file}")

# =====================================================
# Abrir en navegador
# =====================================================

webbrowser.open(output_file)

print("Proceso terminado.")