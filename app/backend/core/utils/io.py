from __future__ import annotations
from pathlib import Path
import json
import hashlib
from datetime import datetime

# Paths (Windows-friendly; use backslashes when writing literals elsewhere)
ROOT: Path = Path(__file__).resolve().parents[4]
APP_DIR: Path = ROOT / "app"
MODULES_DIR: Path = APP_DIR / "modules"
REGISTRY_DIR: Path = APP_DIR / "registry"
REGISTRY_WS_DIR: Path = REGISTRY_DIR / "workspaces"
REGISTRY_NN_DIR: Path = REGISTRY_DIR / "neural_nets"
REGISTRY_MODELS_DIR: Path = REGISTRY_DIR / "models"
REGISTRY_DATASETS_DIR: Path = REGISTRY_DIR / "datasets"
GUARDRAILS_DIR: Path = REGISTRY_DIR / "guardrails"
ARTIFACTS_DIR: Path = APP_DIR / "artifacts"
ARTIFACTS_INDICES: Path = ARTIFACTS_DIR / "indices"
ARTIFACTS_METRICS: Path = ARTIFACTS_DIR / "metrics"
ARTIFACTS_LOGS: Path = ARTIFACTS_DIR / "logs"
ARTIFACTS_JOBS: Path = ARTIFACTS_DIR / "jobs"
ARTIFACTS_TRACES: Path = ARTIFACTS_DIR / "traces"
ARTIFACTS_DATASETS: Path = ARTIFACTS_DIR / "datasets"
SCHEMA_PATH: Path = ROOT / "docs" / "specs" / "module_manifest_schema.json"
WORDNET_ROOT: Path = ROOT / "WordNet-3.0"

ESSENTIAL_DIRS = [
    REGISTRY_WS_DIR, REGISTRY_NN_DIR, REGISTRY_MODELS_DIR, REGISTRY_DATASETS_DIR, GUARDRAILS_DIR,
    ARTIFACTS_DIR, ARTIFACTS_INDICES, ARTIFACTS_METRICS, ARTIFACTS_LOGS, ARTIFACTS_JOBS, ARTIFACTS_TRACES, ARTIFACTS_DATASETS
]


def ensure_dirs():
    for d in ESSENTIAL_DIRS:
        d.mkdir(parents=True, exist_ok=True)


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def compute_sha256(path: Path, chunk_size: int = 65536) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def now_iso() -> str:
    return datetime.now().astimezone().isoformat()
