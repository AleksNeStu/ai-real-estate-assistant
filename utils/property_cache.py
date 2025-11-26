from pathlib import Path
import json
from typing import Optional
from data.schemas import PropertyCollection

CACHE_DIR = Path(".app_cache")
CACHE_FILE = CACHE_DIR / "properties.json"

def save_collection(collection: PropertyCollection) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    data = collection.model_dump()
    CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False))

def load_collection() -> Optional[PropertyCollection]:
    if not CACHE_FILE.exists():
        return None
    try:
        data = json.loads(CACHE_FILE.read_text())
        return PropertyCollection.model_validate(data)
    except Exception:
        return None

def clear_cache() -> None:
    try:
        CACHE_FILE.unlink()
    except Exception:
        pass
