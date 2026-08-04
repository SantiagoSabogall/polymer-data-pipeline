"""Fuente de verdad de los términos de búsqueda y de los niveles del pipeline.

Las listas de términos (POLYESTER_TERMS, BARRIER_TERMS, ...) viven únicamente
aquí y se almacenan "limpias", es decir, sin wildcards: el sufijo ``*`` se
elimina y la responsabilidad de expresarlo (o no) según la sintaxis de cada
API recae en ``polymer_pipeline.query_builder``.

Los fragmentos booleanos genéricos (A, B, C, D, E_blends, E_additives) se
derivan automáticamente de las listas para evitar duplicación: cualquier
cambio en una lista se propaga a las consultas, a los filtros y al dashboard
sin editar nada más.
"""

from __future__ import annotations

POLYESTER_TERMS = [
    "polyester",
    "PET",
    "polyethylene terephthalate",
    "poly(ethylene terephthalate)",
    "copolyester",
    "co-polyester",
]

BARRIER_TERMS = [
    "barrier",
    "permeability",
    "permeation",
    "transmission",
    "transmission rate",
    "permeable",
    "WVTR",
    "OTR",
    "high barrier",
    "oxygen barrier",
    "gas barrier",
    "water vapor barrier",
]

PACKAGING_TERMS = [
    "packaging",
    "film",
    "package",
    "pack",
]

BIOPOLYMER_TERMS = [
    "PBAT",
    "PLA",
    "PHB",
    "biopolymer",
    "biopolyester",
    "poly(lactic acid)",
    "polylactic acid",
    "poly(butylene adipate-co-terephthalate)",
    "polyhydroxybutyrate",
]

ADDITIVE_TERMS = [
    "additive",
    "filler",
    "nanofiller",
    "nanoparticle",
    "composite",
    "nanocomposite",
    "clay",
    "nanoclay",
    "silica",
    "graphene",
    "cellulose",
    "nanocrystal",
]

BLEND_TERMS = [
    "blend",
    "copolymer",
    "co-polyester",
    "copolyester",
]


def _term_for_query(term: str) -> str:
    """Expresa un término limpio dentro de un fragmento booleano genérico.

    Las frases (más de una palabra) se entrecomillan para que el parser de
    ``query_builder`` las distinga de los términos simples.
    """
    return f'"{term}"' if " " in term else term


def _or_group(terms: list[str]) -> str:
    """Construye un grupo ``OR`` a partir de una lista de términos limpios."""
    return "(" + " OR ".join(_term_for_query(term) for term in terms) + ")"


# Fragmentos booleanos genéricos derivados de las listas (única fuente).
# Sirven de entrada a query_builder.py, que los traduce a la sintaxis de cada API.
A = _or_group(POLYESTER_TERMS)
B = _or_group(BARRIER_TERMS)
C = _or_group(PACKAGING_TERMS)
D = _or_group(BIOPOLYMER_TERMS)
E_blends = _or_group(BLEND_TERMS)
E_additives = _or_group(ADDITIVE_TERMS)

# Única fuente de verdad de los niveles de búsqueda.
# Agregar o quitar un nivel aquí (key, label, color, queries y filter_rules opcionales)
# propaga los cambios a pipeline, filtros, dashboard y exports automáticamente.
LEVELS = [
    {
        "key": "L1",
        "label": "Blends",
        "color": "#10b981",
        "queries": [f"{A} AND {E_blends} AND {B}"],
        "filter_rules": [POLYESTER_TERMS, BLEND_TERMS, BARRIER_TERMS],
    },
    {
        "key": "L2",
        "label": "Aditivos",
        "color": "#f59e0b",
        "queries": [f"{A} AND {E_additives} AND {B}"],
        "filter_rules": [POLYESTER_TERMS, ADDITIVE_TERMS, BARRIER_TERMS],
    },
    {
        "key": "L3",
        "label": "Empaques",
        "color": "#3b82f6",
        "queries": [f"{C} AND {B} AND {A}"],
        "filter_rules": [PACKAGING_TERMS, BARRIER_TERMS, POLYESTER_TERMS],
    },
    {
        "key": "L4",
        "label": "Biodegradables",
        "color": "#ec4899",
        "queries": [f"{D} AND {B} AND {C}"],
        "filter_rules": [BIOPOLYMER_TERMS, BARRIER_TERMS, PACKAGING_TERMS],
    },
]

# Derivados (se mantienen por compatibilidad; no editarlos a mano)
SEARCH_QUERIES = {level["key"]: level["queries"] for level in LEVELS}
LEVEL_FILTER_RULES = {
    level["key"]: level["filter_rules"]
    for level in LEVELS
    if level.get("filter_rules")
}
