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


def passes_filter(article: dict, level: str) -> bool:
    title = article.get("title", "")
    if not title or title == "Sin título":
        return False

    # Springer y Elsevier ya filtran por relevancia en su propia API
    source = article.get("source", "")
    if source in SOURCES_WITH_BUILTIN_FILTER:
        return True

    rules = LEVEL_FILTER_RULES.get(level)
    if rules:
        # Al menos 2 de 3 grupos de términos deben tener coincidencia (filtro balanceado)
        matches = sum(1 for term_group in rules if contains_any_term(title, term_group))
        return matches >= 2

    # Fallback genérico para niveles sin reglas definidas
    return contains_any_term(title, _FALLBACK_MATERIAL) and contains_any_term(title, _FALLBACK_PROPERTY)
