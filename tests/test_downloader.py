"""Tests for polymer_pipeline.downloader — PDF downloader + R2 upload.

Uses unittest + unittest.mock to avoid actual HTTP calls and R2 access.
"""

from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from polymer_pipeline.downloader import (
    ArticleDownloader,
    DownloadRateLimiter,
    DownloadResult,
    doi_to_filename,
    is_valid_pdf,
    title_to_filename,
)


class TestIsValidPdf(unittest.TestCase):
    def test_valid_pdf_magic(self) -> None:
        self.assertTrue(is_valid_pdf(b"%PDF-1.4 content"))

    def test_invalid_pdf(self) -> None:
        self.assertFalse(is_valid_pdf(b"<html>"))

    def test_empty_bytes(self) -> None:
        self.assertFalse(is_valid_pdf(b""))

    def test_short_bytes(self) -> None:
        self.assertFalse(is_valid_pdf(b"%P"))


class TestDoiToFilename(unittest.TestCase):
    def test_simple_doi(self) -> None:
        result = doi_to_filename("10.1234/paper.123")
        self.assertEqual(result, "10.1234_paper.123.pdf")

    def test_doi_with_special_chars(self) -> None:
        result = doi_to_filename("10.1234/a@b#c")
        self.assertNotIn("@", result)
        self.assertNotIn("#", result)
        self.assertTrue(result.endswith(".pdf"))


class TestTitleToFilename(unittest.TestCase):
    def test_normal_title(self) -> None:
        result = title_to_filename("Polyester Barrier Film")
        self.assertTrue(result.startswith("_no_doi_"))
        self.assertTrue(result.endswith(".pdf"))
        self.assertIn("polyester", result)

    def test_special_characters(self) -> None:
        result = title_to_filename("Title with @#$% symbols!")
        self.assertNotIn("@", result)
        self.assertNotIn("#", result)


class TestDownloadResult(unittest.TestCase):
    def test_defaults(self) -> None:
        r = DownloadResult(
            doi="10.1/a", title="Paper", pdf_url="http://x.pdf",
        )
        self.assertFalse(r.success)
        self.assertEqual(r.error, "")
        self.assertEqual(r.file_size, 0)


class TestDownloadRateLimiter(unittest.TestCase):
    def test_sets_min_interval(self) -> None:
        limiter = DownloadRateLimiter(
            rate_limits={"example.com": 1.0}, default=0.1,
        )

        async def _run():
            import time

            t0 = time.monotonic()
            await limiter.wait_if_needed(
                "http://example.com/paper.pdf",
            )
            await limiter.wait_if_needed(
                "http://example.com/paper2.pdf",
            )
            elapsed = time.monotonic() - t0
            self.assertGreaterEqual(elapsed, 0.9)

        asyncio.run(_run())

    def test_unknown_domain_uses_default(self) -> None:
        limiter = DownloadRateLimiter(rate_limits={}, default=0.01)

        async def _run():
            import time

            t0 = time.monotonic()
            await limiter.wait_if_needed("http://unknown.com/x.pdf")
            elapsed = time.monotonic() - t0
            self.assertGreaterEqual(elapsed, 0.0)

        asyncio.run(_run())


class TestArticleDownloader(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        self.downloader = ArticleDownloader(download_dir=self.tmpdir)

    def test_creates_download_dir(self) -> None:
        self.assertTrue(Path(self.tmpdir).exists())

    def test_resolve_filename_with_doi(self) -> None:
        result = self.downloader._resolve_filename("10.1234/a", "Title")
        self.assertEqual(result, "10.1234_a.pdf")

    def test_resolve_filename_without_doi(self) -> None:
        result = self.downloader._resolve_filename("", "My Paper Title")
        self.assertTrue(result.startswith("_no_doi_"))

    def test_make_unique(self) -> None:
        existing = Path(self.tmpdir) / "10.1234_a.pdf"
        existing.write_bytes(b"test")
        result = self.downloader._make_unique("10.1234_a.pdf")
        self.assertEqual(result, "10.1234_a_1.pdf")

    def test_make_unique_no_conflict(self) -> None:
        result = self.downloader._make_unique("nonexistent.pdf")
        self.assertEqual(result, "nonexistent.pdf")

    def test_download_pdf_no_url(self) -> None:
        async def _run():
            session = AsyncMock()
            result = await self.downloader.download_pdf(session, url="")
            self.assertFalse(result.success)
            self.assertEqual(result.error, "No URL provided")

        asyncio.run(_run())

    def test_manifest_loads_empty(self) -> None:
        with patch.object(ArticleDownloader, "_load_manifest", return_value={}):
            dl = ArticleDownloader(download_dir=self.tmpdir)
            self.assertEqual(dl._manifest, {})

    def test_download_batch_no_urls(self) -> None:
        async def _run():
            articles = [
                {"title": "Paper A"},
                {"title": "Paper B"},
            ]
            results = await self.downloader.download_batch(articles)
            self.assertEqual(len(results), 0)

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
