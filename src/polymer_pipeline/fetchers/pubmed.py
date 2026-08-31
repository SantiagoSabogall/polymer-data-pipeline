from __future__ import annotations

import logging
import xml.etree.ElementTree as ET

from polymer_pipeline.cache import get_cached, set_cache
from polymer_pipeline.http import make_session, request_with_retry
from polymer_pipeline.query_builder import build_pubmed_query
from polymer_pipeline.rate_limiter import get_rate_limiter
from polymer_pipeline.settings import NCBI_API_KEY, NCBI_EMAIL

logger = logging.getLogger(__name__)


async def fetch_pubmed(query: str, max_results: int = 100) -> list[dict]:
    cache_key = f"PubMed:{query}"
    cached = get_cached(cache_key)
    if cached is not None:
        logger.info("[PubMed] Usando cache para: %s...", query[:60])
        return cached

    query = build_pubmed_query(query)
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    search_params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json",
        "email": NCBI_EMAIL,
    }
    if NCBI_API_KEY:
        search_params["api_key"] = NCBI_API_KEY

    limiter = get_rate_limiter("PubMed")
    async with limiter:
        async with await make_session() as session:
            try:
                resp = await request_with_retry(
                    session, "GET", base_url + "esearch.fcgi",
                    params=search_params,
                )
                if resp is None or resp.status != 200:
                    logger.error(
                        "[PubMed] Error during esearch: status=%s",
                        resp.status if resp else "None",
                    )
                    return []
                data = await resp.json()
                idlist = data.get("esearchresult", {}).get("idlist", [])
            except Exception as e:
                logger.error("[PubMed] Error during esearch: %s", e)
                return []

            if not idlist:
                return []

            fetch_params = {
                "db": "pubmed",
                "id": ",".join(idlist),
                "rettype": "xml",
                "retmode": "xml",
            }
            if NCBI_API_KEY:
                fetch_params["api_key"] = NCBI_API_KEY
            try:
                resp = await request_with_retry(
                    session, "GET", base_url + "efetch.fcgi",
                    params=fetch_params,
                )
                if resp is None or resp.status != 200:
                    logger.error(
                        "[PubMed] Error during efetch: status=%s",
                        resp.status if resp else "None",
                    )
                    return []
                xml_content = await resp.text()
                root = ET.fromstring(xml_content)
            except Exception as e:
                logger.error("[PubMed] Error during efetch: %s", e)
                return []

            results = []
            for article in root.findall('.//PubmedArticle'):
                medline = article.find('MedlineCitation')
                article_info = medline.find('Article') if medline is not None else None
                if article_info is None:
                    continue
                title_el = article_info.find('ArticleTitle')
                title = title_el.text if title_el is not None else "Sin título"
                author = "Desconocido"
                author_list = article_info.find('AuthorList')
                if author_list is not None and len(author_list) > 0:
                    first_author = author_list[0]
                    lastname = first_author.findtext('LastName') or ''
                    fore_name = first_author.findtext('ForeName') or ''
                    author = f"{fore_name} {lastname}".strip() or "Desconocido"
                journal_el = article_info.find('Journal/Title')
                journal = journal_el.text if journal_el is not None else "No disponible"
                year = ""
                pub_date = article_info.find('Journal/JournalIssue/PubDate')
                if pub_date is not None:
                    year_el = pub_date.find('Year')
                    if year_el is not None and year_el.text:
                        year = year_el.text
                    else:
                        medline_date = pub_date.find('MedlineDate')
                        if medline_date is not None and medline_date.text:
                            year = medline_date.text[:4]
                doi = ""
                for eid in article.findall('.//ELocationID'):
                    if eid.get('EIdType') == 'doi' and eid.text:
                        doi = eid.text.lower().strip()
                        break

                abstract = ""
                abstract_el = article_info.find('Abstract')
                if abstract_el is not None:
                    abstract_parts = []
                    for text_el in abstract_el.findall('AbstractText'):
                        if text_el.text:
                            abstract_parts.append(text_el.text)
                    abstract = " ".join(abstract_parts)

                pdf_url = ""

                results.append({
                    "title": title,
                    "author": author,
                    "journal": journal,
                    "year": year,
                    "doi": doi,
                    "source": "PubMed",
                    "abstract": abstract,
                    "pdf_url": pdf_url,
                })

    set_cache(cache_key, results)
    return results
