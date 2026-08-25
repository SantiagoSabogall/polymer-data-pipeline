"""Configuración centralizada del pipeline.

Provee ``PipelineConfig`` como dataclass y mantiene las constantes a nivel
de módulo por compatibilidad con el código existente.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


def load_settings(dotenv_path: str | Path | None = None, override: bool = False) -> None:
    """Carga las variables de entorno desde el archivo .env.

    Debe llamarse explícitamente desde el entrypoint (main.py / pipeline.main)
    antes de que los fetchers lean sus claves. Idempotente: no pisa variables
    ya definidas salvo que ``override=True``.
    """
    if dotenv_path is not None:
        load_dotenv(dotenv_path=Path(dotenv_path), override=override)
    else:
        load_dotenv(override=override)


@dataclass(frozen=True)
class PipelineConfig:
    """Configuración inmutable del pipeline.

    Se construye una sola vez en ``main()`` y se pasa explícitamente a los
    módulos que la necesitan, evitando dependencias ocultas en variables
    globales.
    """
    total_results_per_query: int = 250
    batch_size: int = 25
    sleep_between_batches: float = 0.5
    max_workers: int = 5
    cache_ttl: int = 3600
    output_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent)


# ── Constantes de módulo (compatibilidad) ──────────────────────────────
TOTAL_RESULTS_PER_QUERY: int = 250
BATCH_SIZE: int = 25
SLEEP_BETWEEN_BATCHES: float = 0.5
MAX_WORKERS: int = 5
CACHE_TTL: int = 3600

# ── API Keys ───────────────────────────────────────────────────────────
ELSEVIER_API_KEY: str | None = os.getenv("ELSEVIER_API_KEY")
SPRINGER_API_KEY: str | None = os.getenv("SPRINGER_META_API_KEY")
CROSSREF_EMAIL: str = os.getenv("CROSSREF_POLITE_EMAIL", "[EMAIL_ADDRESS]")
NCBI_EMAIL: str = os.getenv("NCBI_EMAIL", "[EMAIL_ADDRESS]")
NCBI_API_KEY: str | None = os.getenv("PUBMED_API_KEY")
OPENALEX_EMAIL: str = os.getenv("OPENALEX_EMAIL", "[EMAIL_ADDRESS]")
OPENALEX_API_KEY: str | None = os.getenv("OPENALEX_API_KEY")
LENS_API_KEY: str | None = os.getenv("LENS_API_KEY")
# Límite estándar con API key gratuita: 1 req/s en todos los endpoints
# (el fetcher aplica throttle global; ver fetchers/semantic_scholar.py).
SEMANTIC_SCHOLAR_API_KEY: str | None = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
