"""
filters.py
==========

"""

import re
from dict import (
    LEVEL_FILTER_RULES,
    POLYESTER_TERMS,
    BIOPOLYMER_TERMS,
    PACKAGING_TERMS,
    BARRIER_TERMS,
    BLEND_TERMS,
    ADDITIVE_TERMS
)


def _term_to_pattern(term):
    """Convierte un término (con o sin '*' de prefijo) en un patrón
    regex con límites de palabra, para evitar falsos positivos como
    'PET' coincidiendo dentro de 'carPET' o 'PETroleum'.

    \\b solo es válido en la frontera entre un carácter de palabra y uno
    que no lo es. Si el término empieza o termina en puntuación (ej.
    "poly(ethylene terephthalate)"), exigir \\b ahí rompe el match
    cuando ese paréntesis está pegado a OTRO carácter no-alfanumérico
    en el texto real (ej. "...)/Clay..."). Por eso el límite se agrega
    condicionalmente, solo en los extremos alfanuméricos del término.
    """
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
    """True si 'text' contiene al menos uno de los términos de la lista.
    Es la implementación del 'OR' dentro de cada bloque lógico (A, B, C...)."""
    if not text:
        return False
    for term in terms:
        pattern = _term_to_pattern(term)
        if re.search(pattern, text, flags=re.IGNORECASE):
            return True
    return False


def passes_filter(article, level):
    """Evalúa si un artículo pasa el filtro de relevancia.
    
    1. Si la fuente es Springer o Elsevier, confiamos en su motor de búsqueda
       booleano y los aceptamos directamente para no perder artículos válidos.
    2. Para Crossref, validamos que el título contenga al menos un término
       de material/empaque Y al menos un término de propiedad/aditivo/mezcla,
       lo cual elimina el ruido de medicina o geología de forma efectiva.
    """
    title = article.get("title", "")
    if not title or title == "Sin título":
        return False

    source = article.get("source", "")
    if source in ["Springer", "Elsevier"]:
        return True

    # Agrupamos dimensiones para una validación flexible en Crossref
    material_terms = POLYESTER_TERMS + BIOPOLYMER_TERMS + PACKAGING_TERMS
    property_terms = BARRIER_TERMS + BLEND_TERMS + ADDITIVE_TERMS

    has_material = contains_any_term(title, material_terms)
    has_property = contains_any_term(title, property_terms)

    return has_material and has_property


if __name__ == "__main__":
    # Demostración rápida usando ejemplos reales que se colaron en L2
    # durante la corrida anterior, para confirmar que el filtro los rechaza.
    ruido_l2 = [
        "Evolution of Nanoparticle Protein Corona across the Blood-Brain Barrier",
        "Comparison of Clay Mineralogy of Late Quaternary Back-Barrier and Barrier Sediments",
        "Effect of Heating and Drying on Clay-Barrier Gas-Permeability",
    ]
    valido_l2 = [
        "Effects of Nanofiller-Induced Crystallization on Gas Barrier Properties "
        "in Poly(ethylene terephthalate)/Clay Composite Films"
    ]

    print("--- Casos que DEBERÍAN rechazarse ---")
    for titulo in ruido_l2:
        print(f"  [{passes_filter({'title': titulo}, 'L2')}] {titulo[:70]}...")

    print("\n--- Caso que DEBERÍA aceptarse ---")
    for titulo in valido_l2:
        print(f"  [{passes_filter({'title': titulo}, 'L2')}] {titulo[:70]}...")