import re
from polymer_pipeline.dict import (
    LEVEL_FILTER_RULES,
    POLYESTER_TERMS,
    BIOPOLYMER_TERMS,
    PACKAGING_TERMS,
    BARRIER_TERMS,
    BLEND_TERMS,
    ADDITIVE_TERMS,
)


def _term_to_pattern(term):
    if term.endswith("*"):
        base = term[:-1]
        pattern = re.escape(base) + r"\w*"
    else:
        base = term
        pattern = re.escape(base)

    leading = r"\b" if base[:1].isalnum() else ""
    trailing = r"\b" if base[-1:].isalnum() else ""
    return leading + pattern + trailing


def contains_any_term(text, terms):
    if not text:
        return False
    for term in terms:
        pattern = _term_to_pattern(term)
        if re.search(pattern, text, flags=re.IGNORECASE):
            return True
    return False


def passes_filter(article, level):
    title = article.get("title", "")
    if not title or title == "Sin título":
        return False

    source = article.get("source", "")
    if source in ["Springer", "Elsevier"]:
        return True

    material_terms = POLYESTER_TERMS + BIOPOLYMER_TERMS + PACKAGING_TERMS
    property_terms = BARRIER_TERMS + BLEND_TERMS + ADDITIVE_TERMS

    has_material = contains_any_term(title, material_terms)
    has_property = contains_any_term(title, property_terms)

    return has_material and has_property
