"""Rate limiter por API usando sliding window.

Cada API tiene su propia instancia de RateLimiter que controla
la velocidad de peticiones de forma independiente.
"""

from __future__ import annotations

import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter async con sliding window.

    Ejemplo::

        limiter = RateLimiter(max_requests=40, window_seconds=1.0)

        async with limiter:
            resp = await session.get(url)
    """

    def __init__(self, max_requests: int, window_seconds: float = 1.0, name: str = ""):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.name = name
        self._timestamps: list[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Adquiere un permiso. Bloquea si se excede el rate limit."""
        async with self._lock:
            now = time.monotonic()
            # Limpiar timestamps fuera de la ventana
            self._timestamps = [
                t for t in self._timestamps if now - t < self.window_seconds
            ]
            if len(self._timestamps) >= self.max_requests:
                wait_time = self.window_seconds - (now - self._timestamps[0])
                if wait_time > 0:
                    logger.debug("[%s] Rate limit: esperando %.2fs", self.name, wait_time)
                    await asyncio.sleep(wait_time)
            self._timestamps.append(time.monotonic())

    async def __aenter__(self) -> RateLimiter:
        await self.acquire()
        return self

    async def __aexit__(self, *args) -> None:
        pass


# ── Instancias por API ────────────────────────────────────────────────

RATE_LIMITERS: dict[str, RateLimiter] = {}

# OpenAlex y MDPI comparten la misma API
_openalex_limiter = RateLimiter(max_requests=9, window_seconds=1.0, name="OpenAlex")

RATE_LIMITERS = {
    "Crossref": RateLimiter(max_requests=40, window_seconds=1.0, name="Crossref"),
    "PubMed": RateLimiter(max_requests=9, window_seconds=1.0, name="PubMed"),
    "Springer": RateLimiter(max_requests=8, window_seconds=1.0, name="Springer"),
    "Elsevier": RateLimiter(max_requests=5, window_seconds=1.0, name="Elsevier"),
    "OpenAlex": _openalex_limiter,
    "MDPI": _openalex_limiter,  # Misma instancia que OpenAlex
    "SemanticScholar": RateLimiter(max_requests=8, window_seconds=1.0, name="SemanticScholar"),
    "Lens": RateLimiter(max_requests=8, window_seconds=1.0, name="Lens"),
}


def get_rate_limiter(source: str) -> RateLimiter:
    """Obtiene el rate limiter para una fuente dada."""
    return RATE_LIMITERS.get(source, RateLimiter(max_requests=10, window_seconds=1.0, name=source))
