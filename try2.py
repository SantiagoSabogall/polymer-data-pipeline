import os
import re
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path="API_KEY.env")

ELSEVIER_API_KEY = os.getenv("ELSEVIER_API_KEY")
SPRINGER_API_KEY = os.getenv("SPRINGER_META_API_KEY")
CROSSREF_EMAIL = os.getenv("CROSSREF_POLITE_EMAIL", "ssabogal@unal.edu.co")

TEST_QUERY = "polyester water vapor barrier"
SAMPLE_SIZE = 3


def test_elsevier():
    print("\n=== ELSEVIER (Scopus Search API) ===")

    if not ELSEVIER_API_KEY:
        print("Saltando: ELSEVIER_API_KEY no configurada.")
        return

    url = "https://api.elsevier.com/content/search/scopus"
    headers = {"X-ELS-APIKey": ELSEVIER_API_KEY, "Accept": "application/json"}
    params = {
        "query": TEST_QUERY,
        "count": SAMPLE_SIZE,
        "view": "COMPLETE"  # sin esto, dc:description nunca viene en la respuesta
    }

    response = requests.get(url, headers=headers, params=params, timeout=15)
    print("Status:", response.status_code)

    if response.status_code != 200:
        print("Respuesta:", response.text[:300])
        return

    entries = response.json().get("search-results", {}).get("entry", [])
    if not entries:
        print("No se obtuvieron resultados para la query de prueba.")
        return

    for i, entry in enumerate(entries, 1):
        title = entry.get("dc:title", "Sin título")
        abstract = entry.get("dc:description")
        print(f"\n[{i}] {title}")
        if abstract:
            print(f"   Abstract presente ({len(abstract)} caracteres):")
            print(f"   {abstract[:200]}...")
        else:
            print("   Abstract: NO presente en esta respuesta (revisar entitlement de la cuenta)")


    print("\n=== SPRINGER (Meta API) ===")

    if not SPRINGER_API_KEY:
        print("Saltando: SPRINGER_META_API_KEY no configurada.")
        return

    url = "https://api.springernature.com/meta/v2/json"
    params = {
        "q": TEST_QUERY,
        "p": SAMPLE_SIZE,
        "api_key": SPRINGER_API_KEY
    }

    response = requests.get(url, params=params, timeout=15)
    print("Status:", response.status_code)

    if response.status_code != 200:
        print("Respuesta:", response.text[:300])
        return

    records = response.json().get("records", [])
    if not records:
        print("No se obtuvieron resultados para la query de prueba.")
        return

    for i, record in enumerate(records, 1):
        title = record.get("title", "Sin título")
        abstract = record.get("abstract")
        print(f"\n[{i}] {title}")
        if abstract:
            print(f"   Abstract presente ({len(abstract)} caracteres):")
            print(f"   {abstract[:200]}...")
        else:
            print("   Abstract: NO presente en esta respuesta")


def test_crossref():
    print("\n=== CROSSREF (REST API /works) ===")

    url = "https://api.crossref.org/works"
    headers = {
        "User-Agent": f"PolymerDataPipeline/1.0 (mailto:{CROSSREF_EMAIL})"
    }
    params = {
        "query": TEST_QUERY,
        "rows": SAMPLE_SIZE
    }

    response = requests.get(url, headers=headers, params=params, timeout=15)
    print("Status:", response.status_code)

    if response.status_code != 200:
        print("Respuesta:", response.text[:300])
        return

    items = response.json().get("message", {}).get("items", [])
    if not items:
        print("No se obtuvieron resultados para la query de prueba.")
        return

    con_abstract = 0
    for i, item in enumerate(items, 1):
        title = item.get("title", [""])[0] if item.get("title") else "Sin título"
        abstract_raw = item.get("abstract")

        print(f"\n[{i}] {title}")
        if abstract_raw:
            con_abstract += 1
            # El abstract de Crossref normalmente viene envuelto en JATS XML
            # (ej. <jats:p>...</jats:p>). Mostramos ambas versiones para
            # confirmar si hace falta un paso de limpieza antes de usarlo.
            print(f"   Abstract RAW (con marcado JATS, primeros 200 car.):")
            print(f"   {abstract_raw[:200]}")

            cleaned = re.sub(r"<[^>]+>", "", abstract_raw).strip()
            print(f"   Abstract LIMPIO (tags removidos, primeros 200 car.):")
            print(f"   {cleaned[:200]}...")
        else:
            print("   Abstract: NO presente (esta editorial no lo depositó en Crossref)")

    print(f"\n--- Cobertura: {con_abstract}/{len(items)} resultados con abstract en esta muestra ---")


if __name__ == "__main__":
    test_elsevier()

    test_crossref()