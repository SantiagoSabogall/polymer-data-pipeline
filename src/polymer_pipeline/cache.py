import json
import hashlib
import time
from pathlib import Path

CACHE_DIR = Path(".cache")
CACHE_TTL = 3600


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
    except Exception:
        return None


def set_cache(key: str, data: list) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    entry = {"timestamp": time.time(), "data": data}
    path = _key_to_path(key)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entry, f, ensure_ascii=False)


def clear_cache() -> None:
    if CACHE_DIR.exists():
        for f in CACHE_DIR.iterdir():
            f.unlink(missing_ok=True)
