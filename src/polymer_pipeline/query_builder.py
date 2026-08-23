"""Construcción de consultas específicas por motor científico.

Este módulo es el único responsable de traducir la consulta booleana genérica
(definida en ``dict.py``, la fuente de verdad) al lenguaje de consulta propio
de cada API.

Los fetchers reciben esa consulta genérica y la delegan aquí: no conocen ningún
detalle de sintaxis. El principio es:

    dict.py  ->  query_builder.py  ->  fetchers  ->  pipeline

Para soportar una nueva API solo es necesario implementar un nuevo builder
(su término + su ``build_*_query``), sin tocar el resto del proyecto.

Formato de entrada soportado (el generado por ``dict.py``)::

    (t1 OR t2 OR "frase l") AND (t3 OR t4) AND ...

Los términos se almacenan limpios (sin wildcards) en ``dict.py``; cada builder
decide cómo expresarlos según las reglas de su API.
"""

from __future__ import annotations

from collections.abc import Callable

# Expresiones por término ---------------------------------------------------
#: Función que, dado un término limpio, devuelve su representación para un API.
TermFn = Callable[[str], str]


def _crossref_term(term: str) -> str:
    """polyester -> polyester* ; las frases se mantienen entrecomilladas."""
    return f'"{term}"' if " " in term else f"{term}*"


def _openalex_term(term: str) -> str:
    """Sin wildcards: los términos simples quedan planos y las frases entrecomilladas."""
    if " " in term or "(" in term:
        return f'"{term}"'
    return term


def _pubmed_term(term: str) -> str:
    """polyester -> polyester[Title/Abstract] ; frases: "..."[Title/Abstract]."""
    if " " in term:
        return f'"{term}"[Title/Abstract]'
    return f"{term}[Title/Abstract]"


def _springer_term(term: str) -> str:
    """Sintaxis booleana compatible con Springer (sin wildcards)."""
    return f'"{term}"' if " " in term else term


def _elsevier_term(term: str) -> str:
    """Scopus/ScienceDirect: campo TITLE-ABS-KEY."""
    inner = f'"{term}"' if " " in term else term
    return f"TITLE-ABS-KEY({inner})"


def _semanticscholar_term(term: str) -> str:
    """Búsqueda por relevancia de Semantic Scholar; frases entrecomilladas."""
    return f'"{term}"' if " " in term else term


def _europepmc_term(term: str) -> str:
    """EuropePMC: campo TITLE_ABS con soporte de frases."""
    return f'TITLE_ABS:"{term}"' if " " in term else f"TITLE_ABS:{term}"


def parse_boolean_query(query: str) -> list[list[str]]:
    """Convierte una consulta booleana genérica en grupos de términos limpios.

    Formato soportado (el que genera ``dict.py``)::

        (a OR "b c" OR d) AND (e OR f) AND ...

    Devuelve algo como ``[["a", "b c", "d"], ["e", "f"]]``. Si la entrada no
    tiene el formato esperado devuelve una lista vacía y quien llame degrada
    elegantemente.
    """
    if not query or not isinstance(query, str):
        return []
    groups: list[list[str]] = []
    for part in query.split(" AND "):
        group = _clean_group(part)
        if group:
            groups.append(group)
    return groups


def _clean_group(part: str) -> list[str]:
    """Limpia un grupo "(t1 OR t2 OR ...)" a una lista de términos."""
    part = part.strip()
    if part.startswith("(") and part.endswith(")"):
        part = part[1:-1]
    terms = [term.strip().strip('"') for term in part.split(" OR ")]
    return [term for term in terms if term]


def _render_boolean(query: str, term_fn: TermFn) -> str:
    """Renderiza cada grupo con ``term_fn`` y une los grupos con ``AND``.

    Si la consulta no es parseable, devuelve la entrada intacta (degradación
    elegante, nunca una consulta vacía o inválida).
    """
    groups = parse_boolean_query(query)
    if not groups:
        return query
    rendered: list[str] = []
    for group in groups:
        rendered.append("(" + " OR ".join(term_fn(term) for term in group) + ")")
    return " AND ".join(rendered)


def build_crossref_query(query: str) -> str:
    """Traduce la consulta genérica a sintaxis Crossref (wildcards)."""
    return _render_boolean(query, _crossref_term)


def build_openalex_query(query: str) -> str:
    """Traduce la consulta genérica a sintaxis OpenAlex (sin wildcards).

    OpenAlex no soporta wildcards dentro de frases; se degradan eliminándolos.
    La salida nunca produce HTTP 400 (parentesís equilibrados, sin ``*``).
    """
    return _render_boolean(query, _openalex_term)


def build_pubmed_query(query: str) -> str:
    """Traduce la consulta genérica a sintaxis PubMed (Title/Abstract)."""
    return _render_boolean(query, _pubmed_term)


def build_springer_query(query: str) -> str:
    """Traduce la consulta genérica a sintaxis booleana compatible con Springer."""
    return _render_boolean(query, _springer_term)


def build_elsevier_query(query: str) -> str:
    """Traduce la consulta genérica a sintaxis Scopus/ScienceDirect."""
    return _render_boolean(query, _elsevier_term)


def build_semanticscholar_query(query: str) -> str:
    """Traduce la consulta genérica a sintaxis de Semantic Scholar.

    Preparado para un futuro fetcher; aún no se usa en el pipeline.
    """
    return _render_boolean(query, _semanticscholar_term)


def build_europepmc_query(query: str) -> str:
    """Traduce la consulta genérica a sintaxis de EuropePMC.

    Preparado para un futuro fetcher; aún no se usa en el pipeline.
    """
    return _render_boolean(query, _europepmc_term)


# Registro extensible: agregar una nueva API = registrar aquí su builder.
BUILDERS: dict[str, Callable[[str], str]] = {
    "Crossref": build_crossref_query,
    "OpenAlex": build_openalex_query,
    "PubMed": build_pubmed_query,
    "Springer": build_springer_query,
    "Elsevier": build_elsevier_query,
    "MDPI": build_openalex_query,  # MDPI usa OpenAlex API
    "SemanticScholar": build_semanticscholar_query,
    "EuropePMC": build_europepmc_query,
}


def build_query(source: str, query: str) -> str:
    """Traduce ``query`` usando el builder registrado para ``source``.

    Si ``source`` no está registrado, devuelve la consulta intacta, de modo que
    un API nuevo sin builder propio sigue funcionando con la sintaxis genérica.
    """
    builder = BUILDERS.get(source)
    return builder(query) if builder is not None else query