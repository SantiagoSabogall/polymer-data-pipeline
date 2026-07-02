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

L1_QUERIES = [f"{A} AND {E_blends} AND {B}"]
L2_QUERIES = [f"{A} AND {E_additives} AND {B}"]
L3_QUERIES = [f"{C} AND {B} AND {A}"]
L4_QUERIES = [f"{D} AND {B} AND {C}"]

LEVEL_FILTER_RULES = {
    "L1": [POLYESTER_TERMS, BLEND_TERMS, BARRIER_TERMS],
    "L2": [POLYESTER_TERMS, ADDITIVE_TERMS, BARRIER_TERMS],
    "L3": [PACKAGING_TERMS, BARRIER_TERMS, POLYESTER_TERMS],
    "L4": [BIOPOLYMER_TERMS, BARRIER_TERMS, PACKAGING_TERMS],
}

SEARCH_QUERIES = {
    "L1": L1_QUERIES,
    "L2": L2_QUERIES,
    "L3": L3_QUERIES,
    "L4": L4_QUERIES,
}
