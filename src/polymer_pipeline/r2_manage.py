"""Funciones de gestión de Cloudflare R2 para la app Streamlit.

Proporciona funciones de alto nivel para subir, verificar y eliminar
PDFs en R2, diseñadas para ser llamadas desde la interfaz de usuario.
"""

from __future__ import annotations

import logging
from typing import Callable

from polymer_pipeline.downloader import ArticleDownloader
from polymer_pipeline.r2_storage import get_r2_client

logger = logging.getLogger(__name__)


def get_r2_status() -> dict | None:
    """Retorna info del bucket R2: cantidad de archivos y tamaño total.

    Retorna None si R2 no está configurado.
    """
    r2 = get_r2_client()
    if not r2:
        return None
    info = r2.get_bucket_info()
    return {
        "count": info["count"],
        "total_size_bytes": info["total_size_bytes"],
        "total_size_mb": info["total_size_bytes"] / (1024 * 1024),
    }


async def upload_pdfs_to_r2(
    articles: list[dict],
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> dict:
    """Descarga PDFs y los sube a R2 de forma asíncrona.

    Evita duplicados verificando file_exists antes de subir.

    Args:
        articles: Lista de artículos con campo pdf_url.
        progress_callback: fn(completed, total, status) para progreso.

    Returns:
        Dict con {uploaded, skipped, failed, total}.
    """
    r2 = get_r2_client()
    if not r2:
        logger.error("[R2 Manage] R2 no configurado")
        return {"uploaded": 0, "skipped": 0, "failed": 0, "total": 0}

    downloader = ArticleDownloader(r2_storage=r2)
    results = await downloader.download_batch(articles, upload_to_r2=True)

    uploaded = sum(1 for r in results if r.success and "uploaded to R2" in r.error)
    skipped = sum(1 for r in results if r.success and "Already exists in R2" in r.error)
    failed = sum(1 for r in results if not r.success)

    return {
        "uploaded": uploaded,
        "skipped": skipped,
        "failed": failed,
        "total": len(results),
    }


def delete_all_from_r2() -> dict:
    """Elimina todos los archivos del bucket R2.

    Returns:
        Dict con {deleted, errors}.
    """
    r2 = get_r2_client()
    if not r2:
        return {"deleted": 0, "errors": 1}

    deleted = r2.delete_all()
    return {"deleted": deleted, "errors": 0}


def list_r2_files() -> list[dict]:
    """Lista todos los archivos en R2."""
    r2 = get_r2_client()
    if not r2:
        return []
    return r2.list_files()
