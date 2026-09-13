"""Configuración centralizada del pipeline.

Provee ``PipelineConfig`` como dataclass y mantiene getters de API keys
que leen desde variables de entorno (lazy loading).
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


# ── API Keys — lazy getters ────────────────────────────────────────────
# Estos se evalúan en tiempo de uso, no en import, para respetar load_dotenv().


def get_elsevier_api_key() -> str | None:
    return os.getenv("ELSEVIER_API_KEY")


def get_springer_api_key() -> str | None:
    return os.getenv("SPRINGER_META_API_KEY")


def get_crossref_email() -> str:
    return os.getenv("CROSSREF_POLITE_EMAIL", "")


def get_ncbi_email() -> str:
    return os.getenv("NCBI_EMAIL", "")


def get_ncbi_api_key() -> str | None:
    return os.getenv("PUBMED_API_KEY")


def get_openalex_email() -> str:
    return os.getenv("OPENALEX_EMAIL", "[EMAIL_ADDRESS]")


def get_openalex_api_key() -> str | None:
    return os.getenv("OPENALEX_API_KEY")


def get_lens_api_key() -> str | None:
    return os.getenv("LENS_API_KEY")


def get_semantic_scholar_api_key() -> str | None:
    return os.getenv("SEMANTIC_SCHOLAR_API_KEY")


# ── Cloudflare R2 Storage ─────────────────────────────────────────────


def get_r2_access_key() -> str | None:
    return os.getenv("R2_ACCESS_KEY")


def get_r2_secret_key() -> str | None:
    return os.getenv("R2_SECRET_KEY")


def get_r2_endpoint() -> str | None:
    return os.getenv("R2_ENDPOINT")


def get_r2_bucket_name() -> str:
    return os.getenv("R2_BUCKET_NAME", "polymer-papers")
