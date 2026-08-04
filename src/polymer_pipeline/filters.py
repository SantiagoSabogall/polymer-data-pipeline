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

_FALLBACK_MATERIAL = POLYESTER_TERMS + BIOPOLYMER_TERMS + PACKAGING_TERMS
_FALLBACK_PROPERTY = BARRIER_TERMS + BLEND_TERMS + ADDITIVE_TERMS

# Estas fuentes ya filtran por relevancia dentro de su propia API,
# por lo que no se les aplican las reglas de nivel.
SOURCES_WITH_BUILTIN_FILTER = {"Springer", "Elsevier"}


def _term_to_pattern(term):
    is_wildcard = term.endswith("*")
    if is_wildcard:
        base = term[:-1]
        pattern = re.escape(base) + r"\w*"
    else:
        base = term
        pattern = re.escape(base)

    leading = r"\b" if base[:1].isalnum() else ""
    trailing = r"\b" if not is_wildcard and base[-1:].isalnum() else ""
    return leading + pattern + trailing

_CASE_SENSITIVE_TERMS = {"PET"}
def contains_any_term(text, terms):
    if not text:
        return False
    for term in terms:
        pattern = _term_to_pattern(term)
        flags = 0 if term in _CASE_SENSITIVE_TERMS else re.IGNORECASE
        if re.search(pattern, text, flags=flags):
            return True
    return False


def passes_filter(article, level):
    title = article.get("title", "")
    if not title or title == "Sin título":
        return False

    # Springer y Elsevier ya filtran por relevancia en su propia API
    source = article.get("source", "")
    if source in SOURCES_WITH_BUILTIN_FILTER:
        return True

    rules = LEVEL_FILTER_RULES.get(level)
    if rules:
        # Todos los grupos de términos del nivel deben tener al menos una coincidencia
        return all(contains_any_term(title, term_group) for term_group in rules)

    # Fallback genérico para niveles sin reglas definidas
    return contains_any_term(title, _FALLBACK_MATERIAL) and contains_any_term(title, _FALLBACK_PROPERTY)

