import time
import requests

from polymer_pipeline.cache import get_cached, set_cache


CHEMRXIV_MEMBER_ID = "4917"


def fetch_chemrxiv(query: str, max_results: int = 100,
                   email: str = "ssabogal@unal.edu.co",
                   sleep: float = 0.5) -> list:
    cache_key = f"ChemRxiv:{query}"
    cached = get_cached(cache_key)
    if cached is not None:
        print(f"[ChemRxiv] Usando cache para: {query[:60]}...")
        return cached

    url = "https://api.crossref.org/works"
    headers = {
        "User-Agent": f"PolymerDataPipeline/1.0 (mailto:{email})"
    }

    normalized = []
    batch = 25
    offset = 0

    while offset < max_results:
        rows = min(batch, max_results - offset)
        params = {
            "query": query,
            "filter": f"member:{CHEMRXIV_MEMBER_ID}",
            "rows": rows,
            "offset": offset,
            "select": "DOI,title,author,published-print,published-online,container-title",
        }

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=20)

            if resp.status_code == 429:
                print(f"[ChemRxiv] 429 en offset={offset}. Pausando 10s.")
                time.sleep(10)
                continue

            if resp.status_code != 200:
                print(f"[ChemRxiv] Error {resp.status_code} en offset={offset}. Omitiendo lote.")
                offset += rows
                continue

            data = resp.json()
            message = data.get("message", {})
            items = message.get("items", [])

            if not items:
                break

            for item in items:
                title = item.get("title", ["Sin titulo"])[0] if item.get("title") else "Sin titulo"
                doi = item.get("DOI", "").lower().strip()

                authors = item.get("author", [])
                author = "Desconocido"
                if authors:
                    given = authors[0].get("given", "")
                    family = authors[0].get("family", "")
                    author = f"{given} {family}".strip() or "Desconocido"

                container = item.get("container-title", [])
                journal = container[0] if container else "ChemRxiv"

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
                    "source": "ChemRxiv",
                })

            total = message.get("total-results", 0)
            if len(normalized) >= total:
                break

            offset += rows
            time.sleep(sleep)

        except Exception as e:
            print(f"[ChemRxiv] Excepcion en offset={offset}: {e}")
            offset += rows
            continue

    set_cache(cache_key, normalized)
    return normalized
