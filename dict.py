# ================================
# Semantic Search Dictionary
# Polymer + Packaging Literature
# ================================

# -------------------------------
# Raw term lists (opcional uso futuro)
# -------------------------------

POLYESTER_TERMS = [
    "polyester",
    "polyesters",
    "PET",
    "polyethylene terephthalate"
]

BARRIER_TERMS = [
    "high barrier",
    "oxygen barrier",
    "gas barrier",
    "water vapor barrier"
]

PACKAGING_TERMS = [
    "packaging",
    "films",
    "food packaging"
]

BIOPOLYMER_TERMS = [
    "PLA",
    "PBAT",
    "PHB"
]

ADDITIVE_TERMS = [
    "additives",
    "fillers",
    "nanoparticles"
]

BLEND_TERMS = [
    "blend",
    "blends"
]


# -------------------------------
# Logical query blocks (MAIN SYSTEM)
# -------------------------------

A = '(polyester OR polyesters OR PET OR "polyethylene terephthalate")'

B = '("high barrier" OR "oxygen barrier" OR "gas barrier" OR "water vapor barrier" OR WVTR OR OTR)'

C = '(packaging OR films OR "food packaging" OR "flexible packaging")'

D = '(PBAT OR PLA OR PHB OR biopolymer* OR biopolyester*)'

# Separamos blends (L1) de additives/fillers/nanoparticles (L2)
E_blends = '(blend* OR copolymer* OR co-polyester* OR "polymer blend*")'
E_additives = '(additive* OR filler* OR nanoparticle* OR composite* OR nanocomposite* OR clay*)'


# -------------------------------
# Deterministic query levels
# -------------------------------

# Level 1: Polyesters AND blends AND High Barrier
L1_QUERIES = [
    f"{A} AND {E_blends} AND {B}"
]

# Level 2: Polyesters AND Additives AND High Barrier
L2_QUERIES = [
    f"{A} AND {E_additives} AND {B}"
]

# Level 3: Packaging or films AND High Barrier AND Polyesters
L3_QUERIES = [
    f"{C} AND {B} AND {A}"
]

# Level 4: PBAT/PLA/PHB AND High Barrier AND Packaging
L4_QUERIES = [
    f"{D} AND {B} AND {C}"
]


# -------------------------------
# Export structure
# -------------------------------

SEARCH_QUERIES = {
    "L1": L1_QUERIES,
    "L2": L2_QUERIES,
    "L3": L3_QUERIES,
    "L4": L4_QUERIES
}