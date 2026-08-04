"""Tests de query_builder y de la fuente de verdad dict.py.

Se ejecutan con unittest (stdlib), sin dependencias externas::

    python -m unittest tests.test_query_builder -v
"""

from __future__ import annotations

import unittest

from polymer_pipeline.dict import (
    A,
    B,
    D,
    E_additives,
    E_blends,
    POLYESTER_TERMS,
    SEARCH_QUERIES,
)
from polymer_pipeline.query_builder import (
    build_crossref_query,
    build_elsevier_query,
    build_europepmc_query,
    build_openalex_query,
    build_pubmed_query,
    build_query,
    build_semanticscholar_query,
    build_springer_query,
    parse_boolean_query,
)


class TestDictCleanTerms(unittest.TestCase):
    """Los términos de dict.py deben estar limpios (sin wildcards)."""

    def test_no_wildcards_in_term_lists(self) -> None:
        for terms in (
            POLYESTER_TERMS,
        ):
            for term in terms:
                with self.subTest(term=term):
                    self.assertNotIn("*", term)

    def test_derived_fragments_consume_the_lists(self) -> None:
        self.assertIn("polyester", A)
        self.assertNotIn("polyester*", A)
        self.assertIn("barrier", B)
        self.assertIn("blend", E_blends)
        self.assertIn("additive", E_additives)
        self.assertIn("PBAT", D)

    def test_search_queries_are_generic_boolean(self) -> None:
        for queries in SEARCH_QUERIES.values():
            for query in queries:
                with self.subTest(query=query):
                    self.assertIn(" AND ", query)
                    self.assertTrue(query.startswith("("))


class TestParseBooleanQuery(unittest.TestCase):
    def test_parses_groups_and_terms(self) -> None:
        query = '(a OR "b c" OR d) AND (e OR f)'
        self.assertEqual(parse_boolean_query(query), [["a", "b c", "d"], ["e", "f"]])

    def test_empty_or_none_returns_empty(self) -> None:
        self.assertEqual(parse_boolean_query(""), [])
        self.assertEqual(parse_boolean_query(None), [])  # type: ignore[arg-type]


class TestCrossrefBuilder(unittest.TestCase):
    def test_adds_wildcards_to_single_words(self) -> None:
        query = "(polyester OR PET) AND (barrier)"
        expected = "(polyester* OR PET*) AND (barrier*)"
        self.assertEqual(build_crossref_query(query), expected)

    def test_keeps_phrases_quoted(self) -> None:
        query = '("high barrier")'
        self.assertEqual(build_crossref_query(query), '("high barrier")')


class TestOpenAlexBuilder(unittest.TestCase):
    def test_no_wildcards(self) -> None:
        query = "(polyester OR PET) AND (barrier)"
        expected = "(polyester OR PET) AND (barrier)"
        self.assertEqual(build_openalex_query(query), expected)
        self.assertNotIn("*", build_openalex_query(query))

    def test_quotes_phrases_and_parenthesized_terms(self) -> None:
        query = '("polyethylene terephthalate" OR "poly(ethylene terephthalate)")'
        result = build_openalex_query(query)
        self.assertIn('"polyethylene terephthalate"', result)
        self.assertIn('"poly(ethylene terephthalate)"', result)


class TestPubMedBuilder(unittest.TestCase):
    def test_adds_title_abstract_field(self) -> None:
        query = "(polyester OR PET) AND (blend)"
        expected = (
            "(polyester[Title/Abstract] OR PET[Title/Abstract]) "
            "AND (blend[Title/Abstract])"
        )
        self.assertEqual(build_pubmed_query(query), expected)

    def test_phrases_with_field(self) -> None:
        query = '("high barrier")'
        self.assertEqual(build_pubmed_query(query), '("high barrier"[Title/Abstract])')


class TestSpringerAndElsevierBuilders(unittest.TestCase):
    def test_springer_keeps_boolean_syntax(self) -> None:
        query = "(polyester OR PET) AND (blend)"
        self.assertEqual(build_springer_query(query), query)

    def test_elsevier_uses_title_abs_key(self) -> None:
        query = "(polyester OR PET) AND (blend)"
        expected = (
            "(TITLE-ABS-KEY(polyester) OR TITLE-ABS-KEY(PET)) "
            "AND (TITLE-ABS-KEY(blend))"
        )
        self.assertEqual(build_elsevier_query(query), expected)


class TestPreparedBuilders(unittest.TestCase):
    def test_semanticscholar_and_europepmc_are_implemented(self) -> None:
        query = "(polyester) AND (barrier)"
        self.assertIn("polyester", build_semanticscholar_query(query))
        self.assertIn("TITLE_ABS:", build_europepmc_query(query))


class TestBuildQueryRegistry(unittest.TestCase):
    def test_known_source_uses_its_builder(self) -> None:
        query = "(polyester)"
        self.assertEqual(build_query("PubMed", query), build_pubmed_query(query))
        self.assertEqual(build_query("OpenAlex", query), build_openalex_query(query))

    def test_unknown_source_returns_query_untouched(self) -> None:
        query = "(polyester)"
        self.assertEqual(build_query("FutureAPI", query), query)


class TestDegradation(unittest.TestCase):
    def test_empty_query_returns_original(self) -> None:
        query = ""
        self.assertEqual(build_openalex_query(query), query)

    def test_free_text_degrades_to_safe_phrase(self) -> None:
        query = "just free text, no structure"
        result = build_openalex_query(query)
        self.assertIn(query, result)
        self.assertNotIn("*", result)
        self.assertEqual(result.count('"'), 2)  # entrecomillado equilibrado


if __name__ == "__main__":
    unittest.main()
