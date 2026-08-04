import time
import requests
from polymer_pipeline.settings import (
    BATCH_SIZE, TOTAL_RESULTS_PER_QUERY,
    SLEEP_BETWEEN_BATCHES, SPRINGER_API_KEY,
)
from polymer_pipeline.cache import get_cached, set_cache
from polymer_pipeline.query_builder import build_springer_query


def fetch_springer(query):
    cache_key = f"Springer:{query}"
    cached = get_cached(cache_key)
    if cached is not None:
        print(f"[Springer] Usando cache para: {query[:60]}...")
        return cached

    query = build_springer_query(query)
    if not SPRINGER_API_KEY:
        print("[Springer] Saltando: No se configuró SPRINGER_META_API_KEY en API_KEY.env")
        return []

    url = "https://api.springernature.com/meta/v2/json"

    normalized = []
    start = 1

    while (start - 1) < TOTAL_RESULTS_PER_QUERY:
        params = {
            "q": query,
            "p": BATCH_SIZE,
            "s": start,
            "api_key": SPRINGER_API_KEY,
        }

        try:
            response = requests.get(url, params=params, timeout=15)

            if response.status_code == 429:
                print(f"[Springer] 429 en s={start}. Pausando 5s y saltando este lote.")
                time.sleep(5)
                start += BATCH_SIZE
                continue

            if response.status_code != 200:
                print(f"[Springer] Error {response.status_code} en s={start}. Se omite este lote.")
                start += BATCH_SIZE
                continue

            data = response.json()
            records = data.get("records", [])

            if not records:
                break

            for record in records:
                title = record.get("title", "Sin título")
                doi = record.get("doi", "").lower().strip()
                journal = record.get("publicationName", "No disponible")

                creators = record.get("creators", [])
                author = creators[0].get("creator", "Desconocido") if creators else "Desconocido"

                pub_date = record.get("publicationDate", "")
                year = pub_date[:4] if pub_date else ""

                normalized.append({
                    "title": title,
                    "author": author,
                    "journal": journal,
                    "year": year,
                    "doi": doi,
                    "source": "Springer",
                })

            result_info = data.get("result", [{}])
            total_results = int(result_info[0].get("total", 0)) if result_info else 0
            if len(normalized) >= total_results:
                break

            start += BATCH_SIZE
            time.sleep(SLEEP_BETWEEN_BATCHES)

        except Exception as e:
            print(f"[Springer] Falló la petición en s={start}: {e}")
            start += BATCH_SIZE
            continue

    set_cache(cache_key, normalized)
    return normalized
