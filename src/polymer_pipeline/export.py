import csv


def export_csv(articles, filepath="consolidated_results.csv"):
    if not articles:
        print("[Export] No articles to export.")
        return
    fieldnames = ["level", "title", "author", "journal", "year", "doi", "source"]
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for art in articles:
            writer.writerow({k: art.get(k, "") for k in fieldnames})
    print(f"[Export] CSV guardado en {filepath}")


def export_bibtex(articles, filepath="consolidated_results.bib"):
    if not articles:
        print("[Export] No articles to export.")
        return
    with open(filepath, "w", encoding="utf-8") as f:
        for i, art in enumerate(articles):
            source = art.get("source", "Unknown")[:3]
            year = art.get("year", "nodate")
            key = f"{source}_{year}_{i+1}"
            title = _sanitize_bibtex(art.get("title", ""))
            author = _sanitize_bibtex(art.get("author", ""))
            journal = _sanitize_bibtex(art.get("journal", ""))
            doi = art.get("doi", "")
            f.write(f"@article{{{key},\n")
            f.write(f"  title = {{{title}}},\n")
            f.write(f"  author = {{{author}}},\n")
            f.write(f"  journal = {{{journal}}},\n")
            f.write(f"  year = {{{year}}},\n")
            f.write(f"  doi = {{{doi}}},\n")
            f.write(f"  source = {{{art.get('source', '')}}}\n")
            f.write("}\n\n")
    print(f"[Export] BibTeX guardado en {filepath}")


def _sanitize_bibtex(text):
    text = text.replace("{", "\\{").replace("}", "\\}")
    text = text.replace("&", "\\&")
    return text
