# ================================
# Semantic Search Dictionary
# Polymer + Packaging Literature
# ================================

# -------------------------------
# Raw term lists
# -------------------------------
# IMPORTANTE: estas listas ahora cumplen DOBLE función:
#   1. Documentación legible de qué significa cada bloque lógico.
#   2. Input directo del filtro de validación posterior (ver filters.py).
#
# Por eso deben coincidir exactamente con los términos usados en los
# bloques A-E más abajo. Si agregas un sinónimo a un bloque lógico,
# agrégalo también aquí, o el filtro será más estricto que tu búsqueda.
#
# Los términos terminados en "*" se interpretan como prefijo:
# "blend*" coincide con "blend", "blends", "blending", etc.

POLYESTER_TERMS = [
    "polyester*",
    "PET",
    "polyethylene terephthalate",
    "poly(ethylene terephthalate)",  # nomenclatura IUPAC con paréntesis
    "copolyester*",
    "co-polyester*"
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
    "water vapor barrier"
]

PACKAGING_TERMS = [
    "packaging",
    "film*",
    "package*",
    "pack"
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
    "polyhydroxybutyrate"
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
    "nanocrystal*"
]

BLEND_TERMS = [
    "blend*",
    "copolymer*",
    "co-polyester*",
    "copolyester*"
]


# -------------------------------
# Logical query blocks (MAIN SYSTEM)
# -------------------------------
# A: Polyesters (Poliesteres comunes y nombres específicos)
A = '(polyester OR polyesters OR PET OR "polyethylene terephthalate")'

# B: High Barrier (Propiedades de barrera y tasas de transmisión)
B = '("high barrier" OR "oxygen barrier" OR "gas barrier" OR "water vapor barrier" OR WVTR OR OTR)'

# C: Packaging and films (Aplicación de empaque)
C = '(packaging OR films OR "food packaging" OR "flexible packaging")'

# D: Biopolymers (Polímeros biodegradables específicos)
D = '(PBAT OR PLA OR PHB OR biopolymer* OR biopolyester*)'

# E1: Blends (Exclusivo Level 1)
E_blends = '(blend* OR copolymer* OR co-polyester* OR "polymer blend*")'

# E2: Additives & Fillers (Exclusivo Level 2)
E_additives = '(additive* OR filler* OR nanoparticle* OR composite* OR nanocomposite* OR clay*)'


# -------------------------------
# Deterministic query levels
# -------------------------------
L1_QUERIES = [
    f"{A} AND {E_blends} AND {B}"
]

L2_QUERIES = [
    f"{A} AND {E_additives} AND {B}"
]

L3_QUERIES = [
    f"{C} AND {B} AND {A}"
]

L4_QUERIES = [
    f"{D} AND {B} AND {C}"
]


# -------------------------------
# Reglas del filtro de validación posterior
# -------------------------------
# Cada nivel exige que el título contenga AL MENOS UN término de CADA
# lista (lógica AND entre listas, OR dentro de cada lista) — el mismo
# razonamiento de los bloques A-E, pero verificado sobre el texto real
# del resultado, no sobre la query enviada a la API.
LEVEL_FILTER_RULES = {
    "L1": [POLYESTER_TERMS, BLEND_TERMS, BARRIER_TERMS],
    "L2": [POLYESTER_TERMS, ADDITIVE_TERMS, BARRIER_TERMS],
    "L3": [PACKAGING_TERMS, BARRIER_TERMS, POLYESTER_TERMS],
    "L4": [BIOPOLYMER_TERMS, BARRIER_TERMS, PACKAGING_TERMS],
}


# -------------------------------
# Export structure
# -------------------------------

SEARCH_QUERIES = {
    "L1": L1_QUERIES,
    "L2": L2_QUERIES,
    "L3": L3_QUERIES,
    "L4": L4_QUERIES
}