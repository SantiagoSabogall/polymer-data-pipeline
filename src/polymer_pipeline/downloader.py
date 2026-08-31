"""Open-access article downloader for the polymer-data-pipeline.

Downloads PDF articles from URLs provided by the fetchers into a local
``downloads/`` folder. Handles rate limiting, error recovery, PDF
validation, and a download manifest for tracking state.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DOWNLOAD_DIR = PROJECT_ROOT / "downloads"
MANIFEST_PATH = DOWNLOAD_DIR / "manifest.json"
PDF_MAGIC = b"%PDF"
MAX_FILENAME_LENGTH = 120
CHUNK_SIZE = 8192
DEFAULT_TIMEOUT: tuple[int, int] = (10, 60)
MAX_FILE_SIZE = 50 * 1024 * 1024

DEFAULT_RATE_LIMIT = 0.5
RATE_LIMITS: dict[str, float] = {
    "api.openalex.org": 0.15,
    "api.semanticscholar.org": 1.0,
    "api.lens.org": 0.15,
    "api.crossref.org": 0.1,
    "doi.org": 0.1,
    "www.ncbi.nlm.nih.gov": 0.35,
}


@dataclass
class DownloadResult:
    doi: str
    title: str
    pdf_url: str
    filename: str = ""
    success: bool = False
    error: str = ""
    file_size: int = 0
    sha256: str = ""


class DownloadRateLimiter:
    def __init__(self, rate_limits: dict[str, float] | None = None,
                 default: float = DEFAULT_RATE_LIMIT):
        self._limits = rate_limits or RATE_LIMITS
        self._default = default
        self._last_request: dict[str, float] = {}
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)

    def wait_if_needed(self, url: str) -> None:
        domain = urlparse(url).netloc
        min_interval = self._limits.get(domain, self._default)
        with self._cond:
            last = self._last_request.get(domain, 0.0)
            elapsed = time.monotonic() - last
            if elapsed < min_interval:
                wait_time = min_interval - elapsed
                self._cond.wait(wait_time)
            self._last_request[domain] = time.monotonic()


def is_valid_pdf(data: bytes) -> bool:
    return len(data) >= 4 and data[:4] == PDF_MAGIC


def doi_to_filename(doi: str) -> str:
    safe = doi.replace("/", "_").replace(":", "_")
    safe = re.sub(r"[^a-zA-Z0-9._-]", "_", safe)
    return f"{safe}.pdf"


def title_to_filename(title: str) -> str:
    text = title.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return f"_no_doi_{text[:MAX_FILENAME_LENGTH]}.pdf"


class ArticleDownloader:
    def __init__(
        self,
        download_dir: Path | str = DOWNLOAD_DIR,
        rate_limiter: DownloadRateLimiter | None = None,
    ):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.rate_limiter = rate_limiter or DownloadRateLimiter()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "polymer-pipeline/1.0 (PDF-downloader)",
            "Accept": "application/pdf, */*;q=0.1",
        })
        self._manifest = self._load_manifest()

    def _load_manifest(self) -> dict:
        if MANIFEST_PATH.exists():
            try:
                return json.loads(MANIFEST_PATH.read_text("utf-8"))
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save_manifest(self) -> None:
        MANIFEST_PATH.write_text(
            json.dumps(self._manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _resolve_filename(self, doi: str, title: str) -> str:
        if doi:
            return doi_to_filename(doi)
        return title_to_filename(title)

    def _make_unique(self, filename: str) -> str:
        path = self.download_dir / filename
        if not path.exists():
            return filename
        stem = Path(filename).stem
        suffix = Path(filename).suffix
        counter = 1
        while path.exists():
            filename = f"{stem}_{counter}{suffix}"
            path = self.download_dir / filename
            counter += 1
        return filename

    def download_pdf(
        self,
        url: str,
        doi: str = "",
        title: str = "",
        max_retries: int = 2,
        _depth: int = 0,
    ) -> DownloadResult:
        result = DownloadResult(doi=doi, title=title, pdf_url=url)

        if not url:
            result.error = "No URL provided"
            return result

        filename = self._resolve_filename(doi, title)
        filepath = self.download_dir / filename

        if filename in self._manifest and filepath.exists():
            entry = self._manifest[filename]
            result.filename = filename
            result.success = True
            result.file_size = entry.get("file_size", 0)
            result.sha256 = entry.get("sha256", "")
            result.error = "Already downloaded (cached)"
            return result

        last_error = ""
        for attempt in range(max_retries + 1):
            try:
                self.rate_limiter.wait_if_needed(url)
                resp = self.session.get(url, timeout=DEFAULT_TIMEOUT,
                                        allow_redirects=True, stream=True)

                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 5))
                    last_error = "429 Too Many Requests"
                    if attempt < max_retries:
                        time.sleep(retry_after)
                        continue
                    break

                if resp.status_code in (403, 404):
                    last_error = f"HTTP {resp.status_code}"
                    break

                if resp.status_code >= 500:
                    last_error = f"HTTP {resp.status_code}"
                    if attempt < max_retries:
                        time.sleep(2 ** (attempt + 1))
                        continue
                    break

                if resp.status_code != 200:
                    last_error = f"HTTP {resp.status_code}"
                    break

                buffer = b""
                total_size = 0
                for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        buffer += chunk
                        total_size += len(chunk)
                        if total_size > MAX_FILE_SIZE:
                            last_error = f"File exceeds {MAX_FILE_SIZE} bytes"
                            break
                resp.close()

                if total_size == 0:
                    last_error = "Empty response body"
                    break

                if not is_valid_pdf(buffer):
                    if _depth < 3 and b"<html" in buffer[:2048].lower():
                        extracted = self._extract_pdf_link_from_html(buffer)
                        if extracted and extracted != url:
                            return self.download_pdf(extracted, doi, title,
                                                     max_retries=max_retries - attempt,
                                                     _depth=_depth + 1)
                    last_error = "Not a valid PDF"
                    break

                filename = self._make_unique(filename)
                filepath = self.download_dir / filename
                filepath.write_bytes(buffer)

                sha256 = hashlib.sha256(buffer).hexdigest()
                result.filename = filename
                result.success = True
                result.file_size = total_size
                result.sha256 = sha256

                self._manifest[filename] = {
                    "doi": doi, "title": title, "pdf_url": url,
                    "filename": filename, "file_size": total_size,
                    "sha256": sha256,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
                self._save_manifest()
                return result

            except requests.Timeout:
                last_error = "Request timed out"
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
                    continue
                break
            except requests.ConnectionError:
                last_error = "Connection error"
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
                    continue
                break
            except requests.RequestException as e:
                last_error = f"Request error: {e}"
                break

        result.error = last_error
        return result

    @staticmethod
    def _extract_pdf_link_from_html(html_bytes: bytes) -> str | None:
        text = html_bytes.decode("utf-8", errors="ignore")
        patterns = [
            r'href="([^"]*\.pdf[^"]*)"',
            r'href=\'([^\']*\.pdf[^\']*)\'',
        ]
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def download_batch(self, articles: list[dict],
                       max_workers: int = 3) -> list[DownloadResult]:
        results: list[DownloadResult] = []
        downloadable = [art for art in articles if art.get("pdf_url")]
        total = len(downloadable)

        if total == 0:
            logger.info("[Downloader] No hay artículos con URLs de PDF para descargar.")
            return results

        logger.info("[Downloader] Iniciando descarga de %d PDFs...", total)
        success_count = 0
        fail_count = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {
                executor.submit(
                    self.download_pdf,
                    url=art["pdf_url"],
                    doi=art.get("doi", ""),
                    title=art.get("title", ""),
                ): art
                for art in downloadable
            }
            for future in as_completed(future_map):
                art = future_map[future]
                try:
                    result = future.result()
                except Exception as e:
                    result = DownloadResult(
                        doi=art.get("doi", ""),
                        title=art.get("title", ""),
                        pdf_url=art.get("pdf_url", ""),
                        error=f"Unexpected error: {e}",
                    )
                results.append(result)
                if result.success:
                    success_count += 1
                else:
                    fail_count += 1
                done = success_count + fail_count
                if done % 50 == 0 or done == total:
                    logger.info("  [Downloader] %d/%d (%d OK, %d fallidos)",
                                done, total, success_count, fail_count)

        logger.info("[Downloader] Completo: %d descargados, %d fallidos",
                     success_count, fail_count)
        return results
