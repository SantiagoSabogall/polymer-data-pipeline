import time
import requests

from polymer_pipeline.cache import get_cached, set_cache


CHEMRXIV_API_URL = "https://chemrxiv.org/engage/chemrxiv/public-api/v1/items"


def fetch_chemrxiv(query: str, max_results: int = 100, sleep: float = 0.5) -> list:
    cache_key = f"ChemRxiv:{query}"
    cached = get_cached(cache_key)
    if cached is not None:
        print(f"[ChemRxiv] Usando cache para: {query[:60]}...")
        return cached

    normalized = []
    skip = 0
    limit = min(25, max_results)

    while skip < max_results:
        params = {
            "term": query,
            "skip": skip,
            "limit": limit,
            "sort": "relevant",
        }

        try:
            resp = requests.get(CHEMRXIV_API_URL, params=params, timeout=20)

            if resp.status_code == 429:
                print(f"[ChemRxiv] 429 en skip={skip}. Pausando 10s.")
                time.sleep(10)
                continue

            if resp.status_code != 200:
                print(f"[ChemRxiv] Error {resp.status_code} en skip={skip}. Omitiendo lote.")
                break

            data = resp.json()
            items = data.get("itemHits", [])

            if not items:
                break

            for hit in items:
                item = hit.get("item", {})

                title = item.get("title", "Sin título")
                doi = item.get("doi", "").lower().strip()

                authors = item.get("authors", [])
                author = "Desconocido"
                if authors:
                    first = authors[0]
                    given = first.get("firstName", "")
                    family = first.get("lastName", "")
                    author = f"{given} {family}".strip() or "Desconocido"

                # Fecha de publicación
                pub_date = item.get("publishedDate", "") or item.get("submittedDate", "")
                year = pub_date[:4] if pub_date else ""

                normalized.append({
                    "title": title,
                    "author": author,
                    "journal": "ChemRxiv",
                    "year": year,
                    "doi": doi,
                    "source": "ChemRxiv",
                })

            total = data.get("totalCount", 0)
            skip += len(items)

            if skip >= total or skip >= max_results:
                break

            time.sleep(sleep)

        except Exception as e:
            print(f"[ChemRxiv] Excepción en skip={skip}: {e}")
            break

    print(f"[ChemRxiv] {len(normalized)} resultados para: {query[:60]}...")
    set_cache(cache_key, normalized)
    return normalized
