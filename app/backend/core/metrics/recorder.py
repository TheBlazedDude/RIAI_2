from __future__ import annotations
from pathlib import Path
from typing import Any, Dict
from ..utils.io import ARTIFACTS_METRICS, write_json, now_iso


def record_metrics(capability: str, model_id: str, payload: Dict[str, Any]) -> Path:
    """Write metrics JSON under artifacts\metrics\<capability>\<model_id>.json
    Adds timestamp if missing.
    """
    cap_dir = ARTIFACTS_METRICS / capability
    cap_dir.mkdir(parents=True, exist_ok=True)
    data = dict(payload)
    if "timestamp" not in data:
        data["timestamp"] = now_iso()
    if "model_id" not in data:
        data["model_id"] = model_id
    out = cap_dir / f"{model_id}.json"
    write_json(out, data)
    return out
