import requests
from lxml import etree
import webbrowser

# ========= CONFIGURACIÓN CORREGIDA =========
API_KEY = "9f5a1f06efed14d3649dfb4e23ab072d"  # Corregido: Ahora es un string entre comillas
QUERY   = "julia"     


TOTAL_RESULTS = 100                           # Corregido: Definido como un número entero exacto
CHUNK_SIZE = 25

url = "https://api.elsevier.com/content/search/scopus"
headers = {"X-ELS-APIKey": API_KEY, "Accept": "application/xml"}

entries = []

for start in range(0, TOTAL_RESULTS, CHUNK_SIZE):
    params = {
        "query": QUERY,
        "count": CHUNK_SIZE,
        "start": start
    }
    print(f" Descargando resultados {start+1} a {start+CHUNK_SIZE}...")
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        raise Exception(f"Error en la petición: {response.status_code}, {response.text}")
    
    xml_chunk = etree.fromstring(response.content)
    chunk_entries = xml_chunk.findall("{http://www.w3.org/2005/Atom}entry")
    entries.extend(chunk_entries)

print(f" Total de entradas recolectadas: {len(entries)}")

root = etree.Element("results")
for entry in entries:
    root.append(entry)

xsl_str = """<?xml version="1.0"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:a="http://www.w3.org/2005/Atom"
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:prism="http://prismstandard.org/namespaces/basic/2.0/"
    exclude-result-prefixes="a dc prism">

  <xsl:output method="html" encoding="utf-8" indent="yes"/>

  <xsl:template match="/results">
    <html>
      <head>
        <meta charset="utf-8"/>
        <title>Resultados Scopus API</title>
        <style>
          body { font-family: Arial; color:#323232; }
          table { border-collapse: collapse; width: 100%; }
          th, td { border: 1px solid #ddd; padding: 8px; }
          th { background-color: #007398; color:#fff; }
          tr:nth-child(even) { background-color: #f9f9f9; }
        </style>
      </head>
      <body>
        <h2>Resultados Scopus para la consulta</h2>
        <p><b>Total de resultados mostrados:</b> <xsl:value-of select="count(a:entry)"/></p>
        <table>
          <tr>
            <th>Título</th>
            <th>Autor principal</th>
            <th>Revista</th>
            <th>Año</th>
            <th>DOI</th>
          </tr>
          <xsl:for-each select="a:entry">
            <tr>
              <td><xsl:value-of select="dc:title"/></td>
              <td><xsl:value-of select="dc:creator"/></td>
              <td><xsl:value-of select="prism:publicationName"/></td>
              <td><xsl:value-of select="substring(prism:coverDate,1,4)"/></td>
              <td>
                <xsl:if test="prism:doi">
                  <a href="https://doi.org/{prism:doi}" target="_blank">
                    <xsl:value-of select="prism:doi"/>
                  </a>
                </xsl:if>
              </td>
            </tr>
          </xsl:for-each>
        </table>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>
"""

xslt_doc = etree.XML(xsl_str.encode("utf-8"))
transform = etree.XSLT(xslt_doc)

html_doc = transform(root)

output_file = "elsevier_results.html"
with open(output_file, "wb") as f:
    f.write(etree.tostring(html_doc, pretty_print=True, method="html"))

print(f"¡Listo! Se guardó el archivo '{output_file}'")

webbrowser.open(output_file)
