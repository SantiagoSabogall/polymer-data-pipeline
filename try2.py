import requests
from dict import SEARCH_QUERIES

# ================================
# Crossref configuration
# ================================

URL = "https://api.crossref.org/works"

HEADERS = {
    "User-Agent": "PolymerPipeline/1.0 (mailto:your_email@unal.edu.co)"
}

# ================================
# Fetch function
# ================================

def fetch_crossref(query, rows=25, offset=0):

    params = {
        "query": query,
        "rows": rows,
        "offset": offset
    }

    response = requests.get(
        URL,
        params=params,
        headers=HEADERS
    )

    if response.status_code != 200:
        raise Exception(
            f"Crossref error {response.status_code}\n{response.text}"
        )

    data = response.json()

    return data["message"]["items"]

# ================================
# Normalization function
# ================================

def normalize_article(item):

    title = item.get("title", [""])[0] if item.get("title") else ""

    doi = item.get("DOI", "")

    journal = item.get("container-title", [""])[0] if item.get("container-title") else ""

    authors = item.get("author", [])

    author = "Desconocido"

    if authors:
        given = authors[0].get("given", "")
        family = authors[0].get("family", "")
        author = f"{given} {family}".strip()

    year = ""

    if "published-print" in item:
        year = item["published-print"]["date-parts"][0][0]

    elif "published-online" in item:
        year = item["published-online"]["date-parts"][0][0]

    return {
        "title": title,
        "doi": doi,
        "journal": journal,
        "author": author,
        "year": year
    }

# ================================
# Main pipeline
# ================================

def run_pipeline():

    all_results = {
        "L1": [],
        "L2": [],
        "L3": [],
        "L4": []
    }

    for level, queries in SEARCH_QUERIES.items():

        print(f"\n================ {level} ================")

        for query in queries:

            print(f"Query: {query}")

            items = fetch_crossref(query)

            print(f"  → resultados: {len(items)}")

            for item in items:

                article = normalize_article(item)
                article["level"] = level

                all_results[level].append(article)

    return all_results

# ================================
# Execution
# ================================

if __name__ == "__main__":

    results = run_pipeline()

    # ============================
    # Summary
    # ============================

    total = sum(len(v) for v in results.values())

    print("\n\n================ SUMMARY ================")

    print(f"Total artículos recolectados: {total}")

    for level, items in results.items():
        print(f"{level}: {len(items)} artículos")

    # ============================
    # Show sample
    # ============================

    print("\n\n================ SAMPLE ================")

    for level, items in results.items():

        if items:

            print(f"\n{level} ejemplo:")
            print(items[0])