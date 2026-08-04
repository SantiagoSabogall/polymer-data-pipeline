POLYESTER_TERMS = [
    "polyester*",
    "PET",
    "polyethylene terephthalate",
    "poly(ethylene terephthalate)",
    "copolyester*",
    "co-polyester*",
]

BARRIER_TERMS = [
    "barrier*",
    "permeability",
    "permeation",
    "transmission",
    "transmission rate*",
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
    "film*",
    "package*",
    "pack",
]

BIOPOLYMER_TERMS = [
    "PBAT",
    "PLA",
    "PHB",
    "biopolymer*",
    "biopolyester*",
    "poly(lactic acid)",
    "polylactic acid",
    "poly(butylene adipate-co-terephthalate)",
    "polyhydroxybutyrate",
]

ADDITIVE_TERMS = [
    "additive*",
    "filler*",
    "nanofiller*",
    "nanoparticle*",
    "composite*",
    "nanocomposite*",
    "clay*",
    "nanoclay*",
    "silica",
    "graphene",
    "cellulose",
    "nanocrystal*",
]

BLEND_TERMS = [
    "blend*",
    "copolymer*",
    "co-polyester*",
    "copolyester*",
]

A = '(polyester OR polyesters OR PET OR "polyethylene terephthalate")'
B = '("high barrier" OR "oxygen barrier" OR "gas barrier" OR "water vapor barrier" OR WVTR OR OTR)'
C = '(packaging OR films OR "food packaging" OR "flexible packaging")'
D = '(PBAT OR PLA OR PHB OR biopolymer* OR biopolyester*)'
E_blends = '(blend* OR copolymer* OR co-polyester* OR "polymer blend*")'
E_additives = '(additive* OR filler* OR nanoparticle* OR composite* OR nanocomposite* OR clay*)'

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
