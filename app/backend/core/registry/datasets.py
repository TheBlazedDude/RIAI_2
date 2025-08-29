from __future__ import annotations
from typing import Dict, Any, List
from pathlib import Path
from ..utils.io import REGISTRY_DATASETS_DIR, write_json, load_json, compute_sha256, ROOT


def list_datasets() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for p in REGISTRY_DATASETS_DIR.glob("*.json"):
        try:
            items.append(load_json(p))
        except Exception:
            continue
    return items


def _to_rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT))
    except Exception:
        return str(p)


def register_dataset(ds_id: str, name: str, files: List[Path]) -> Dict[str, Any]:
    file_entries: List[Dict[str, Any]] = []
    for f in files:
        f = Path(f)
        file_entries.append({
            "path": _to_rel(f),
            "sha256": compute_sha256(f) if f.exists() else None
        })
    entry: Dict[str, Any] = {
        "id": ds_id,
        "name": name,
        "files": file_entries
    }
    out = REGISTRY_DATASETS_DIR / f"{ds_id}.json"
    write_json(out, entry)
    return entry


def verify_dataset(entry: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return list of problems for dataset entry (missing files or checksum mismatches)."""
    problems: List[Dict[str, Any]] = []
    for fdesc in entry.get("files", []):
        p = Path(fdesc.get("path", ""))
        if not p.is_absolute():
            p = ROOT / p
        if not p.exists():
            problems.append({"error": "missing", "path": str(p)})
            continue
        sha = fdesc.get("sha256")
        if sha:
            calc = compute_sha256(p)
            if calc.lower() != sha.lower():
                problems.append({"error": "checksum_mismatch", "path": str(p), "expected": sha, "actual": calc})
    return problems
