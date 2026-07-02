import time
import requests
from polymer_pipeline.settings import (
    BATCH_SIZE, TOTAL_RESULTS_PER_QUERY,
    SLEEP_BETWEEN_BATCHES, ELSEVIER_API_KEY,
)


def fetch_elsevier(query):
    if not ELSEVIER_API_KEY:
        print("[Elsevier] Saltando: No se configuró ELSEVIER_API_KEY en API_KEY.env")
        return []

    url = "https://api.elsevier.com/content/search/scopus"
    headers = {
        "X-ELS-APIKey": ELSEVIER_API_KEY,
        "Accept": "application/json",
    }

    normalized = []
    start_index = 0

    while start_index < TOTAL_RESULTS_PER_QUERY:
        params = {
            "query": query,
            "count": BATCH_SIZE,
            "start": start_index,
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)

            if response.status_code == 429:
                print(f"[Elsevier] 429 en start={start_index}. Pausando 5s y saltando este lote.")
                time.sleep(5)
                start_index += BATCH_SIZE
                continue

            if response.status_code != 200:
                print(f"[Elsevier] Error {response.status_code} en start={start_index}. Se omite este lote.")
                start_index += BATCH_SIZE
                continue

            data = response.json()
            search_results = data.get("search-results", {})
            entries = search_results.get("entry", [])

            if not entries or "error" in entries[0]:
                break

            for entry in entries:
                title = entry.get("dc:title", "Sin título")
                author = entry.get("dc:creator", "Desconocido")
                journal = entry.get("prism:publicationName", "No disponible")

                cover_date = entry.get("prism:coverDate", "")
                year = cover_date[:4] if cover_date else ""

                doi = entry.get("prism:doi", "").lower().strip()

                normalized.append({
                    "title": title,
                    "author": author,
                    "journal": journal,
                    "year": year,
                    "doi": doi,
                    "source": "Elsevier",
                })

            total_results = int(search_results.get("opensearch:totalResults", 0))
            if len(normalized) >= total_results:
                break

            start_index += BATCH_SIZE
            time.sleep(SLEEP_BETWEEN_BATCHES)

        except Exception as e:
            print(f"[Elsevier] Falló la petición en start={start_index}: {e}")
            start_index += BATCH_SIZE
            continue

    return normalized
