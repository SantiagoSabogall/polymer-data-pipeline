from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
import time
from pathlib import Path

from polymer_pipeline.settings import CACHE_TTL

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CACHE_DIR = PROJECT_ROOT / ".cache"


def _key_to_path(key: str) -> Path:
    hashed = hashlib.sha256(key.encode()).hexdigest()[:16]
    return CACHE_DIR / f"{hashed}.json"


def get_cached(key: str) -> list | None:
    path = _key_to_path(key)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            entry = json.load(f)
        if time.time() - entry["timestamp"] > CACHE_TTL:
            path.unlink(missing_ok=True)
            return None
        return entry["data"]
    except (json.JSONDecodeError, KeyError, OSError) as e:
        logger.debug("[Cache] Corrupto o ilegible %s: %s", path.name, e)
        path.unlink(missing_ok=True)
        return None


def set_cache(key: str, data: list) -> None:
    """Escribe la cache de forma atómica (temp file + rename)."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    entry = {"timestamp": time.time(), "data": data}
    path = _key_to_path(key)
    try:
        fd, tmp_path = tempfile.mkstemp(dir=str(CACHE_DIR), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False)
        os.replace(tmp_path, path)
        logger.debug("Cache guardado: %s", path.name)
    except OSError as e:
        logger.warning("[Cache] Error escribiendo cache: %s", e)
        # Limpiar temp file si existe
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def clear_cache() -> None:
    if CACHE_DIR.exists():
        for f in CACHE_DIR.iterdir():
            if f.is_file():
                f.unlink(missing_ok=True)
        logger.info("Cache limpiado: %s", CACHE_DIR)
