from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List
from ..utils.io import REGISTRY_NN_DIR, write_json, load_json


def list_neural_nets() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for p in REGISTRY_NN_DIR.glob("*.json"):
        try:
            items.append(load_json(p))
        except Exception:
            continue
    return items


def create_neural_net(nn_id: str, name: str | None = None, family: str | None = None, extra: Dict[str, Any] | None = None) -> Dict[str, Any]:
    entry: Dict[str, Any] = {
        "id": nn_id,
        "name": name or nn_id,
        "family": family,
    }
    if extra:
        entry.update(extra)
    out = REGISTRY_NN_DIR / f"{nn_id}.json"
    write_json(out, entry)
    return entry
