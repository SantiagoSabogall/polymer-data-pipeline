"""CLI entry point — uses core.run_pipeline() to avoid code duplication.

Run with: python -m polymer_pipeline.pipeline
Or via pyproject.toml: polymer-pipeline
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from polymer_pipeline.core import run_pipeline
from polymer_pipeline.dashboard import generate_dashboard
from polymer_pipeline.export import export_all
from polymer_pipeline.plots import generate_all_plots
from polymer_pipeline.settings import load_settings

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


async def main() -> None:
    load_settings()

    logger.info("=" * 60)
    logger.info(" INICIANDO PIPELINE DE BÚSQUEDA CIENTÍFICA CONSOLIDADA ")
    logger.info("=" * 60)

    try:
        articles = await run_pipeline()
    except Exception as e:
        logger.error("[Error] Pipeline falló: %s", e)
        sys.exit(1)

    try:
        exports = export_all(articles, output_dir=PROJECT_ROOT)
        for fmt, path in exports.items():
            logger.info("[Éxito] %s exportado en %s", fmt.upper(), path)
    except Exception as e:
        logger.warning("[Advertencia] Exportación falló: %s", e)

    try:
        plots = generate_all_plots(
            articles, pdf_dir=str(PROJECT_ROOT / "plots_output"),
        )
    except Exception as e:
        logger.warning("[Advertencia] Generación de gráficas falló: %s", e)
        plots = {}

    try:
        html = generate_dashboard(articles, plots=plots)
        html_path = PROJECT_ROOT / "dashboard.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info("[Éxito] Dashboard generado en %s", html_path)
    except Exception as e:
        logger.warning("[Advertencia] Dashboard falló: %s", e)

    logger.info("Proceso finalizado con éxito!")


if __name__ == "__main__":
    asyncio.run(main())
