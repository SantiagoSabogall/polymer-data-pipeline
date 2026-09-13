"""Tests for polymer_pipeline.core — pipeline orchestration.

Uses unittest + unittest.mock to avoid network calls.
"""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock

from polymer_pipeline.core import (
    _build_fetcher_specs,
    _dedupe,
    _fetch_task,
    _safe_year,
    compute_quality_metrics,
    filter_articles,
)


class TestBuildFetcherSpecs(unittest.TestCase):
    """_build_fetcher_specs filters sources and adds correct kwargs."""

    def test_returns_all_sources_when_none_specified(self) -> None:
        specs = _build_fetcher_specs("(polyester)", sources=None)
        self.assertEqual(len(specs), 8)

    def test_filters_by_source_name(self) -> None:
        specs = _build_fetcher_specs(
            "(polyester)", sources=["Crossref", "PubMed"],
        )
        names = [s[0].__name__ for s in specs]
        self.assertEqual(names, ["fetch_crossref", "fetch_pubmed"])

    def test_adds_max_results_for_applicable_fetchers(self) -> None:
        specs = _build_fetcher_specs(
            "(polyester)", sources=["PubMed"], max_results=100,
        )
        _, _, kwargs = specs[0]
        self.assertEqual(kwargs["max_results"], 100)

    def test_adds_title_abs_only_for_custom_queries(self) -> None:
        specs = _build_fetcher_specs(
            "(polyester)", sources=["Crossref"], title_abs_only=True,
        )
        _, _, kwargs = specs[0]
        self.assertTrue(kwargs["title_abs_only"])

    def test_adds_preserve_quotes_flag(self) -> None:
        specs = _build_fetcher_specs(
            "(polyester)", sources=["OpenAlex"], preserve_quotes=True,
        )
        _, _, kwargs = specs[0]
        self.assertTrue(kwargs["preserve_quotes"])

    def test_unknown_source_returns_empty(self) -> None:
        specs = _build_fetcher_specs(
            "(polyester)", sources=["FakeSource"],
        )
        self.assertEqual(len(specs), 0)


class TestDedupe(unittest.TestCase):
    """_dedupe removes duplicates by DOI and title.

    Uses sources with builtin_relevance (Springer, OpenAlex) so articles
    always pass the filter without needing specific title terms.
    """

    def _make_result(
        self, level: str, query: str, articles: list[dict],
    ) -> dict:
        return {
            "level": level,
            "query": query,
            "source": "test",
            "ok": True,
            "articles": articles,
        }

    def test_dedupes_by_doi(self) -> None:
        results = {
            ("L1", "q1"): [
                self._make_result("L1", "q1", [
                    {
                        "doi": "10.1234/a",
                        "title": "Paper A",
                        "source": "Springer",
                    },
                    {
                        "doi": "10.1234/a",
                        "title": "Paper A duplicate",
                        "source": "Springer",
                    },
                ]),
            ],
        }
        queries = {"L1": ["q1"]}
        articles = _dedupe(results, queries)
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["doi"], "10.1234/a")

    def test_dedupes_by_title_when_no_doi(self) -> None:
        results = {
            ("L1", "q1"): [
                self._make_result("L1", "q1", [
                    {
                        "doi": "",
                        "title": "Same Paper",
                        "source": "OpenAlex",
                    },
                    {
                        "doi": "",
                        "title": "Same Paper",
                        "source": "OpenAlex",
                    },
                ]),
            ],
        }
        queries = {"L1": ["q1"]}
        articles = _dedupe(results, queries)
        self.assertEqual(len(articles), 1)

    def test_keeps_different_dois(self) -> None:
        results = {
            ("L1", "q1"): [
                self._make_result("L1", "q1", [
                    {
                        "doi": "10.1234/a",
                        "title": "Paper A",
                        "source": "Springer",
                    },
                    {
                        "doi": "10.1234/b",
                        "title": "Paper B",
                        "source": "Springer",
                    },
                ]),
            ],
        }
        queries = {"L1": ["q1"]}
        articles = _dedupe(results, queries)
        self.assertEqual(len(articles), 2)

    def test_filters_out_articles_without_title(self) -> None:
        results = {
            ("L1", "q1"): [
                self._make_result("L1", "q1", [
                    {"doi": "10.1234/a", "source": "Springer"},
                    {
                        "doi": "10.1234/b",
                        "title": "Paper B",
                        "source": "Springer",
                    },
                ]),
            ],
        }
        queries = {"L1": ["q1"]}
        articles = _dedupe(results, queries)
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["doi"], "10.1234/b")

    def test_sets_level_on_articles(self) -> None:
        results = {
            ("L2", "q1"): [
                self._make_result("L2", "q1", [
                    {
                        "doi": "10.1234/a",
                        "title": "Paper A",
                        "source": "OpenAlex",
                    },
                ]),
            ],
        }
        queries = {"L2": ["q1"]}
        articles = _dedupe(results, queries)
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["level"], "L2")

    def test_empty_results_returns_empty(self) -> None:
        articles = _dedupe({}, {})
        self.assertEqual(articles, [])


class TestSafeYear(unittest.TestCase):
    def test_valid_year(self) -> None:
        self.assertEqual(_safe_year({"year": "2023"}), 2023)

    def test_invalid_year_returns_none(self) -> None:
        self.assertIsNone(_safe_year({"year": "abc"}))

    def test_missing_year_returns_none(self) -> None:
        self.assertIsNone(_safe_year({}))

    def test_string_year_with_decimals(self) -> None:
        self.assertIsNone(_safe_year({"year": "2023.5"}))


class TestFilterArticles(unittest.TestCase):
    def setUp(self) -> None:
        self.articles = [
            {
                "title": "Polyester barrier film",
                "author": "Smith",
                "doi": "10.1/a",
                "journal": "J. Mater.",
                "year": "2020",
                "source": "Crossref",
                "level": "L1",
            },
            {
                "title": "PLA blend packaging",
                "author": "Jones",
                "doi": "10.1/b",
                "journal": "Polymer",
                "year": "2022",
                "source": "PubMed",
                "level": "L2",
            },
            {
                "title": "PBAT biodegradable",
                "author": "Lee",
                "doi": "",
                "journal": "Green Chem.",
                "year": "2023",
                "source": "OpenAlex",
                "level": "L4",
            },
        ]

    def test_no_filters_returns_all(self) -> None:
        result = filter_articles(self.articles)
        self.assertEqual(len(result), 3)

    def test_query_filter(self) -> None:
        result = filter_articles(self.articles, query="polyester")
        self.assertEqual(len(result), 1)
        self.assertIn("Polyester", result[0]["title"])

    def test_year_range_filter(self) -> None:
        result = filter_articles(self.articles, year_range=(2022, 2023))
        self.assertEqual(len(result), 2)

    def test_source_filter(self) -> None:
        result = filter_articles(self.articles, sources=["Crossref"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["source"], "Crossref")

    def test_level_filter(self) -> None:
        result = filter_articles(self.articles, levels=["L1"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["level"], "L1")

    def test_combined_filters(self) -> None:
        result = filter_articles(
            self.articles,
            query="PLA",
            sources=["PubMed"],
            levels=["L2"],
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["doi"], "10.1/b")


class TestComputeQualityMetrics(unittest.TestCase):
    def test_empty_articles(self) -> None:
        metrics = compute_quality_metrics([])
        self.assertEqual(metrics["total"], 0)

    def test_counts_metrics(self) -> None:
        articles = [
            {
                "doi": "10.1/a",
                "abstract": "Some abstract",
                "pdf_url": "http://x.pdf",
                "author": "Smith",
                "journal": "J. Mater.",
            },
            {
                "doi": "",
                "abstract": "",
                "pdf_url": "",
                "author": "Desconocido",
                "journal": "No disponible",
            },
        ]
        metrics = compute_quality_metrics(articles)
        self.assertEqual(metrics["total"], 2)
        self.assertEqual(metrics["with_doi"], 1)
        self.assertEqual(metrics["with_abstract"], 1)
        self.assertEqual(metrics["with_pdf"], 1)
        self.assertEqual(metrics["unknown_author"], 1)
        self.assertEqual(metrics["unknown_journal"], 1)


class TestFetchTask(unittest.TestCase):
    """_fetch_task calls the fetcher and wraps results."""

    def test_successful_fetch(self) -> None:
        async def _run():
            mock_fn = AsyncMock(return_value=[{"title": "Paper"}])
            result = await _fetch_task(
                "L1", "q1", mock_fn, ("q1",), {},
            )
            self.assertTrue(result["ok"])
            self.assertEqual(len(result["articles"]), 1)
            self.assertEqual(result["level"], "L1")

        asyncio.run(_run())

    def test_failed_fetch(self) -> None:
        async def _run():
            mock_fn = AsyncMock(side_effect=RuntimeError("API down"))
            result = await _fetch_task(
                "L1", "q1", mock_fn, ("q1",), {},
            )
            self.assertFalse(result["ok"])
            self.assertEqual(result["articles"], [])

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
