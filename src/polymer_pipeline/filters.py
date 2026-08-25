from __future__ import annotations

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
from polymer_pipeline.sources import SOURCES_WITH_BUILTIN_FILTER

_FALLBACK_MATERIAL = POLYESTER_TERMS + BIOPOLYMER_TERMS + PACKAGING_TERMS
_FALLBACK_PROPERTY = BARRIER_TERMS + BLEND_TERMS + ADDITIVE_TERMS

_CASE_SENSITIVE_TERMS = {"PET"}


def _compile_term(term: str) -> re.Pattern[str]:
    is_wildcard = term.endswith("*")
    if is_wildcard:
        base = term[:-1]
        pattern = re.escape(base) + r"\w*"
    else:
        base = term
        pattern = re.escape(base)

    leading = r"\b" if base[:1].isalnum() else ""
    trailing = r"\b" if not is_wildcard and base[-1:].isalnum() else ""
    flags = 0 if term in _CASE_SENSITIVE_TERMS else re.IGNORECASE
    return re.compile(leading + pattern + trailing, flags=flags)


# Patrones precompilados una sola vez (los términos no cambian en runtime).
_TERM_PATTERNS: dict[str, re.Pattern[str]] = {
    term: _compile_term(term) for term in {
        *_FALLBACK_MATERIAL,
        *_FALLBACK_PROPERTY,
        *POLYESTER_TERMS,
        *BIOPOLYMER_TERMS,
        *PACKAGING_TERMS,
        *BARRIER_TERMS,
        *BLEND_TERMS,
        *ADDITIVE_TERMS,
    }
}


def _term_pattern(term: str) -> re.Pattern[str]:
    return _TERM_PATTERNS.get(term) or _compile_term(term)


def contains_any_term(text: str | None, terms: list[str]) -> bool:
    if not text:
        return False
    for term in terms:
        if _term_pattern(term).search(text):
            return True
    return False


def passes_filter(
    article: dict,
    level: str,
    custom_rules: dict[str, list[list[str]]] | None = None,
) -> bool:
    """Verifica si un artículo pasa el filtro de relevancia para un nivel.

    Args:
        article: Dict con campos del artículo.
        level: Identificador del nivel (L1-L4 o "custom").
        custom_rules: Reglas de filtro personalizadas {level: [groups]}.
                      Si se provee, tiene prioridad sobre LEVEL_FILTER_RULES.
    """
    title = article.get("title", "")
    if not title or title == "Sin título":
        return False

    # Fuentes con relevancia built-in saltan el filtro
    source = article.get("source", "")
    if source in SOURCES_WITH_BUILTIN_FILTER:
        return True

    # Buscar reglas: primero en custom_rules, luego en LEVEL_FILTER_RULES
    rules = None
    if custom_rules:
        rules = custom_rules.get(level)
    if rules is None:
        rules = LEVEL_FILTER_RULES.get(level)

    if rules:
        matches = sum(1 for term_group in rules if contains_any_term(title, term_group))
        return matches >= 2

    # Fallback genérico para niveles sin reglas definidas
    return contains_any_term(title, _FALLBACK_MATERIAL) and contains_any_term(title, _FALLBACK_PROPERTY)
