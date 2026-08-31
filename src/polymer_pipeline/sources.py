"""Registro único de las fuentes del pipeline.

Cada fuente define su color (para plots/dashboard) y si su API ya filtra por
relevancia propia (``builtin_relevance``), lo que evita volver a aplicar las
reglas de nivel en ``filters.py``. Ningún módulo debería hardcodear nombres de
fuente ni colores: todo se deriva de aquí.
"""

SOURCES: dict[str, dict] = {
    "Crossref": {"color": "#8b5cf6", "builtin_relevance": False},
    "Springer": {"color": "#f43f5e", "builtin_relevance": True},
    "Elsevier": {"color": "#0ea5e9", "builtin_relevance": True},
    "PubMed": {"color": "#22c55e", "builtin_relevance": False},
    "OpenAlex": {"color": "#fb923c", "builtin_relevance": True},
    "MDPI": {"color": "#0284c7", "builtin_relevance": True},
    "SemanticScholar": {"color": "#a855f7", "builtin_relevance": False},
    "Lens": {"color": "#14b8a6", "builtin_relevance": False},
}

SOURCE_NAMES = list(SOURCES)

SOURCES_WITH_BUILTIN_FILTER = {
    name for name, cfg in SOURCES.items() if cfg["builtin_relevance"]
}

SOURCE_COLORS = {name: cfg["color"] for name, cfg in SOURCES.items()}
