import os
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


TOTAL_RESULTS_PER_QUERY = 250
BATCH_SIZE = 25
SLEEP_BETWEEN_BATCHES = 0.5
MAX_WORKERS = 5

CACHE_TTL = 3600

ELSEVIER_API_KEY = os.getenv("ELSEVIER_API_KEY")
SPRINGER_API_KEY = os.getenv("SPRINGER_META_API_KEY")
CROSSREF_EMAIL = os.getenv("CROSSREF_POLITE_EMAIL", "[EMAIL_ADDRESS]")
NCBI_EMAIL = os.getenv("NCBI_EMAIL", "[EMAIL_ADDRESS]")
NCBI_API_KEY = os.getenv("PUBMED_API_KEY")
OPENALEX_EMAIL = os.getenv("OPENALEX_EMAIL", "[EMAIL_ADDRESS]")
OPENALEX_API_KEY = os.getenv("OPENALEX_API_KEY")
