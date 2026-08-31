from __future__ import annotations

import logging

from polymer_pipeline.cache import get_cached, set_cache
from polymer_pipeline.http import PageFetcher, make_session
from polymer_pipeline.query_builder import build_crossref_query
from polymer_pipeline.rate_limiter import get_rate_limiter
from polymer_pipeline.settings import (
    CROSSREF_EMAIL,
    TOTAL_RESULTS_PER_QUERY,
)

logger = logging.getLogger(__name__)

URL = "https://api.crossref.org/works"

CROSSREF_BATCH_SIZE = 100
CROSSREF_SLEEP = 0.1


def _strip_jats_tags(text: str) -> str:
    """Elimina tags JATS/XML del abstract."""
    import re
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


async def fetch_crossref(
    query: str, title_abs_only: bool = False,
) -> list[dict]:
    cache_key = f"Crossref:{query}"
    cached = get_cached(cache_key)
    if cached is not None:
        logger.info("[Crossref] Usando cache para: %s...", query[:60])
        return cached

    translated = build_crossref_query(query)

    headers = {
        "User-Agent": f"PolymerDataPipeline/1.0 (mailto:{CROSSREF_EMAIL})"
    }

    def build_params(start: int) -> dict:
        if title_abs_only:
            return {
                "query.bibliographic": translated,
                "rows": CROSSREF_BATCH_SIZE,
                "offset": start,
            }
        return {
            "query": translated,
            "rows": CROSSREF_BATCH_SIZE,
            "offset": start,
        }

    def extract_items(data: dict) -> list[dict]:
        items = data.get("message", {}).get("items", [])
        normalized = []
        for item in items:
            title = item.get("title", [""])[0] if item.get("title") else "Sin título"
            doi = item.get("DOI", "").lower().strip()
            container = item.get("container-title", [""])
            journal = container[0] if item.get("container-title") else "No disponible"

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

            abstract = _strip_jats_tags(item.get("abstract", ""))

            pdf_url = ""
            for link in item.get("link", []):
                ct = link.get("content-type", "")
                if "pdf" in ct.lower():
                    pdf_url = link.get("URL", "")
                    break

            normalized.append({
                "title": title,
                "author": author,
                "journal": journal,
                "year": year,
                "doi": doi,
                "source": "Crossref",
                "abstract": abstract,
                "pdf_url": pdf_url,
            })
        return normalized

    def extract_total(data: dict) -> int:
        return data.get("message", {}).get("total-results", 0)

    fetcher = PageFetcher(
        url=URL,
        batch_size=CROSSREF_BATCH_SIZE,
        sleep_between=CROSSREF_SLEEP,
        total_limit=TOTAL_RESULTS_PER_QUERY,
        build_params=build_params,
        extract_items=extract_items,
        extract_total=extract_total,
        name="Crossref",
    )

    limiter = get_rate_limiter("Crossref")
    async with limiter:
        async with await make_session() as session:
            session.headers.update(headers)
            normalized = await fetcher.run(session)

    set_cache(cache_key, normalized)
    return normalized
