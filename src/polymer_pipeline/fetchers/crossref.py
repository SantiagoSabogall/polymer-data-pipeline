import time
import requests
from polymer_pipeline.settings import (
    BATCH_SIZE, TOTAL_RESULTS_PER_QUERY,
    SLEEP_BETWEEN_BATCHES, CROSSREF_EMAIL,
)
from polymer_pipeline.cache import get_cached, set_cache


def fetch_crossref(query):
    cache_key = f"Crossref:{query}"
    cached = get_cached(cache_key)
    if cached is not None:
        print(f"[Crossref] Usando cache para: {query[:60]}...")
        return cached

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
            "offset": offset,
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)

            if response.status_code == 429:
                print(f"[Crossref] 429 en offset={offset}. Pausando 5s y saltando este lote.")
                time.sleep(5)
                offset += BATCH_SIZE
                continue

            if response.status_code != 200:
                print(f"[Crossref] Error {response.status_code} en offset={offset}. Se omite este lote.")
                offset += BATCH_SIZE
                continue

            data = response.json()
            message = data.get("message", {})
            items = message.get("items", [])

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
                    "source": "Crossref",
                })

            total_results = message.get("total-results", 0)
            if len(normalized) >= total_results:
                break

            offset += BATCH_SIZE
            time.sleep(SLEEP_BETWEEN_BATCHES)

        except Exception as e:
            print(f"[Crossref] Falló la petición en offset={offset}: {e}")
            offset += BATCH_SIZE
            continue

    set_cache(cache_key, normalized)
    return normalized
