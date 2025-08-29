from __future__ import annotations
from typing import Dict, Any
from ..utils.io import REGISTRY_WS_DIR, write_json, load_json, now_iso

PENDING_WS_PATH = REGISTRY_WS_DIR / "pending.json"
MAPPINGS_PATH = REGISTRY_WS_DIR / "mappings.json"


def get_pending_workspace() -> Dict[str, Any]:
    if PENDING_WS_PATH.exists():
        return load_json(PENDING_WS_PATH)
    return {"id": "pending", "name": "Pending Workspace", "selected_modules": [], "updated_at": None}


def save_pending_workspace(selected_modules: list[str]) -> Dict[str, Any]:
    snapshot = {
        "id": "pending",
        "name": "Pending Workspace",
        "selected_modules": selected_modules,
        "updated_at": now_iso(),
    }
    write_json(PENDING_WS_PATH, snapshot)
    return snapshot


def get_mappings() -> Dict[str, Any]:
    return load_json(MAPPINGS_PATH) if MAPPINGS_PATH.exists() else {"module_map": {}, "capability_map": {}}


def save_mappings(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = {
        "module_map": payload.get("module_map", {}),
        "capability_map": payload.get("capability_map", {}),
    }
    write_json(MAPPINGS_PATH, data)
    return data
