"""Helpers HTTP reutilizables asíncronos con aiohttp.

Reemplaza el módulo sync basado en requests con una versión async
que soporta rate limiting, retry con backoff+jitter, y manejo
de headers de rate limit por API.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from collections.abc import Callable

import aiohttp
from aiohttp import ClientTimeout, TCPConnector

logger = logging.getLogger(__name__)

# ── Backoff con jitter ─────────────────────────────────────────────────


def _backoff_with_jitter(attempt: int, max_wait: float = 60.0) -> float:
    """Calcula tiempo de espera con backoff exponencial + jitter."""
    base = min(2 ** attempt, max_wait)
    jitter = random.uniform(0, 1)
    return base + jitter


# ── Request con retry ──────────────────────────────────────────────────


async def request_with_retry(
    session: aiohttp.ClientSession,
    method: str,
    url: str,
    max_retries: int = 5,
    **kwargs,
) -> aiohttp.ClientResponse | None:
    """Realiza una petición HTTP con retry, backoff+jitter y manejo de 429/5xx.

    Returns:
        ClientResponse si éxito, None si se agotaron reintentos.
    """
    for attempt in range(max_retries):
        try:
            resp = await session.request(method, url, **kwargs)

            # ── 429: Too Many Requests ──────────────────────────────
            if resp.status == 429:
                retry_after = resp.headers.get("Retry-After")
                if retry_after:
                    try:
                        wait = float(retry_after)
                    except ValueError:
                        wait = _backoff_with_jitter(attempt)
                else:
                    wait = _backoff_with_jitter(attempt)

                remaining = resp.headers.get("X-RateLimit-Remaining")
                reset = resp.headers.get("X-RateLimit-Reset")
                logger.warning(
                    "[HTTP] 429 en %s (intento %d/%d). Esperando %.1fs"
                    " (Remaining=%s, Reset=%s)",
                    url[:60], attempt + 1, max_retries, wait, remaining, reset,
                )
                await asyncio.sleep(wait)
                continue

            # ── 5xx: Server Error ──────────────────────────────────
            if resp.status >= 500:
                wait = _backoff_with_jitter(attempt)
                logger.warning(
                    "[HTTP] %d en %s (intento %d/%d). Backoff %.1fs",
                    resp.status, url[:60], attempt + 1, max_retries, wait,
                )
                await asyncio.sleep(wait)
                continue

            # ── Éxito ──────────────────────────────────────────────
            return resp

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            if attempt < max_retries - 1:
                wait = _backoff_with_jitter(attempt)
                logger.warning(
                    "[HTTP] Error %s en %s (intento %d/%d). Backoff %.1fs",
                    type(e).__name__, url[:60], attempt + 1, max_retries, wait,
                )
                await asyncio.sleep(wait)
            else:
                logger.error("[HTTP] Error definitivo %s en %s: %s", type(e).__name__, url[:60], e)
                raise

    return None


# ── Session factory ────────────────────────────────────────────────────


async def make_session(
    timeout: int = 30,
    total_retries: int = 3,
) -> aiohttp.ClientSession:
    """Devuelve un ``aiohttp.ClientSession`` con timeout configurado.

    El retry se maneja en ``request_with_retry`` a nivel de cada petición.
    """
    timeout_config = ClientTimeout(total=timeout)
    connector = TCPConnector(limit=20, ttl_dns_cache=300, enable_cleanup_closed=True)
    session = aiohttp.ClientSession(
        timeout=timeout_config,
        connector=connector,
    )
    return session


# ── PageFetcher async ──────────────────────────────────────────────────


class PageFetcher:
    """Pagina una API que devuelve lotes por ``start``/``offset``.

    Versión asíncrona del PageFetcher original. Encapsula el patrón
    común de Crossref/Springer/Elsevier.
    """

    def __init__(
        self,
        *,
        url: str,
        batch_size: int,
        sleep_between: float,
        total_limit: int,
        build_params: Callable[[int], dict],
        extract_items: Callable[[dict], list],
        extract_total: Callable[[dict], int],
        name: str = "API",
        initial_start: int = 0,
    ) -> None:
        self.url = url
        self.batch_size = batch_size
        self.sleep_between = sleep_between
        self.total_limit = total_limit
        self.build_params = build_params
        self.extract_items = extract_items
        self.extract_total = extract_total
        self.name = name
        self.initial_start = initial_start

    async def run(
        self,
        session: aiohttp.ClientSession,
        start: int | None = None,
    ) -> list:
        """Ejecuta la paginación de forma asíncrona."""
        normalized: list = []
        cur = self.initial_start if start is None else start

        while cur < self.total_limit:
            params = self.build_params(cur)

            try:
                resp = await request_with_retry(session, "GET", self.url, params=params)
            except Exception as e:
                logger.error("[%s] Falló la petición en start=%d: %s", self.name, cur, e)
                cur += self.batch_size
                continue

            if resp is None:
                logger.warning("[%s] Sin respuesta en start=%d. Saltando lote.", self.name, cur)
                cur += self.batch_size
                continue

            if resp.status != 200:
                logger.warning(
                    "[%s] Error %d en start=%d. Se omite el lote.",
                    self.name, resp.status, cur,
                )
                cur += self.batch_size
                continue

            try:
                data = await resp.json()
            except (aiohttp.ContentTypeError, ValueError):
                logger.warning("[%s] Respuesta no JSON en start=%d.", self.name, cur)
                cur += self.batch_size
                continue

            items = self.extract_items(data)
            if not items:
                break

            normalized.extend(items)

            total = self.extract_total(data)
            if len(normalized) >= total:
                break

            cur += self.batch_size
            if self.sleep_between:
                await asyncio.sleep(self.sleep_between)

        return normalized
