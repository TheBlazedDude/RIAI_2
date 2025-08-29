from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List
from ..utils.io import ARTIFACTS_METRICS, load_json


def list_metrics(capability: str) -> List[Dict[str, Any]]:
    cap_dir = ARTIFACTS_METRICS / capability
    items: List[Dict[str, Any]] = []
    if not cap_dir.exists():
        return items
    for f in cap_dir.glob("*.json"):
        try:
            items.append(load_json(f))
        except Exception:
            pass
    return items


def latest_metric(capability: str, model_id: str | None = None) -> Dict[str, Any]:
    items = list_metrics(capability)
    if model_id:
        items = [x for x in items if x.get("model_id") == model_id]
    items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return items[0] if items else {}


def metric_by_filename(filename: str) -> Dict[str, Any] | None:
    for cap_dir in ARTIFACTS_METRICS.glob("*"):
        candidate = cap_dir / filename
        if candidate.exists():
            try:
                return load_json(candidate)
            except Exception:
                return None
    return None
