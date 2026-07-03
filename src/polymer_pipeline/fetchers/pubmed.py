import requests
import xml.etree.ElementTree as ET

from polymer_pipeline.settings import NCBI_EMAIL
from polymer_pipeline.cache import get_cached, set_cache


def fetch_pubmed(query: str, max_results: int = 100):
    cache_key = f"PubMed:{query}"
    cached = get_cached(cache_key)
    if cached is not None:
        print(f"[PubMed] Usando cache para: {query[:60]}...")
        return cached

    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    search_params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json",
        "email": NCBI_EMAIL,
    }
    try:
        resp = requests.get(base_url + "esearch.fcgi", params=search_params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        idlist = data.get("esearchresult", {}).get("idlist", [])
    except Exception as e:
        print(f"[PubMed] Error during esearch: {e}")
        return []

    if not idlist:
        return []

    fetch_params = {
        "db": "pubmed",
        "id": ",".join(idlist),
        "rettype": "xml",
        "retmode": "xml",
    }
    try:
        resp = requests.get(base_url + "efetch.fcgi", params=fetch_params, timeout=15)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except Exception as e:
        print(f"[PubMed] Error during efetch: {e}")
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
        results.append({
            "title": title,
            "author": author,
            "journal": journal,
            "year": year,
            "doi": doi,
            "source": "PubMed",
        })
    set_cache(cache_key, results)
    return results
