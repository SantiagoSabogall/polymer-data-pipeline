import os
import requests
import webbrowser
from dotenv import load_dotenv

# =====================================================
# Cargar credenciales
# =====================================================

load_dotenv("API_KEY.env")

CLIENT_ID = os.getenv("ORCID_CLIENT_ID")
CLIENT_SECRET = os.getenv("ORCID_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    raise ValueError("No se encontraron las credenciales ORCID")

# =====================================================
# Obtener token OAuth2
# =====================================================


token_url = "https://sandbox.orcid.org/oauth/token"

token_data = {
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "grant_type": "client_credentials",
    "scope": "/read-public"
}

token_response = requests.post(token_url, data=token_data)
print(token_response.status_code)
print(repr(token_response.text))

if token_response.status_code != 200:
    raise Exception(
        f"Error obteniendo token:\n{token_response.text}"
    )

access_token = token_response.json()["access_token"]

print("Token obtenido correctamente")

# =====================================================
# Consulta
# =====================================================

QUERY = "andromeda"

headers = {
    "Authorization": f"Bearer {access_token}",
    "Accept": "application/json"
}

search_url = "https://pub.orcid.org/v3.0/search/"

params = {
    "q": QUERY
}

response = requests.get(
    search_url,
    headers=headers,
    params=params
)

if response.status_code != 200:
    raise Exception(
        f"Error en búsqueda:\n{response.text}"
    )

data = response.json()

results = data.get("result", [])

print(f"Resultados encontrados: {len(results)}")

# =====================================================
# Obtener detalles de cada ORCID
# =====================================================

rows = ""

for item in results[:50]:

    orcid = item["orcid-identifier"]["path"]

    person_url = f"https://pub.orcid.org/v3.0/{orcid}/person"

    person_response = requests.get(
        person_url,
        headers=headers
    )

    if person_response.status_code != 200:
        continue

    person = person_response.json()

    given = (
        person.get("name", {})
        .get("given-names", {})
        .get("value", "")
    )

    family = (
        person.get("name", {})
        .get("family-name", {})
        .get("value", "")
    )

    full_name = f"{given} {family}".strip()

    rows += f"""
    <tr>
        <td>{full_name}</td>
        <td>{orcid}</td>
        <td>
            <a href="https://orcid.org/{orcid}" target="_blank">
                Ver perfil
            </a>
        </td>
    </tr>
    """

# =====================================================
# Generar HTML
# =====================================================

html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">

<title>Resultados ORCID</title>

<style>

body {{
    font-family: Arial;
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
    background-color: #4CAF50;
    color: white;
}}

tr:nth-child(even) {{
    background-color: #f2f2f2;
}}

</style>

</head>

<body>

<h2>Resultados ORCID para "{QUERY}"</h2>

<table>

<tr>
    <th>Nombre</th>
    <th>ORCID</th>
    <th>Perfil</th>
</tr>

{rows}

</table>

</body>
</html>
"""

output_file = "orcid_results.html"

with open(output_file, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Archivo generado: {output_file}")

webbrowser.open(output_file)