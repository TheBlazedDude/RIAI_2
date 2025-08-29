from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List
from ..utils.io import MODULES_DIR, SCHEMA_PATH, load_json


REQUIRED_FIELDS = [
    "id", "name", "version", "description",
    "capabilities", "task", "inputs", "outputs",
    "ui_panels", "model_constraints", "pipelines",
    "resources", "guardrails", "autotrain", "schema_version"
]


def discover_modules() -> List[Dict[str, Any]]:
    modules: List[Dict[str, Any]] = []
    for manifest in MODULES_DIR.glob("*/manifest.json"):
        try:
            data = load_json(manifest)
            for k in REQUIRED_FIELDS:
                if k not in data:
                    raise ValueError(f"manifest missing field: {k}")
            data["_manifest_path"] = str(manifest)
            modules.append(data)
        except Exception as e:
            modules.append({"id": manifest.parent.name, "error": str(e)})
    return modules
