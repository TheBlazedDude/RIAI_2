from __future__ import annotations
from typing import Dict, Any, List
from ..utils.io import REGISTRY_MODELS_DIR, write_json, load_json, now_iso


def list_models() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for p in REGISTRY_MODELS_DIR.glob("*.json"):
        try:
            items.append(load_json(p))
        except Exception:
            continue
    return items


def create_model(model_id: str, capability: str, task: str, name: str | None = None, extra: Dict[str, Any] | None = None) -> Dict[str, Any]:
    entry: Dict[str, Any] = {
        "id": model_id,
        "name": name or model_id,
        "capability": capability,
        "task": task,
        "created_at": now_iso(),
        "metrics": {},
    }
    if extra:
        entry.update(extra)
    path = REGISTRY_MODELS_DIR / f"{model_id}.json"
    write_json(path, entry)
    return entry
