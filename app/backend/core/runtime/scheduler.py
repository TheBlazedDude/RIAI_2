from __future__ import annotations
from typing import Any, Dict
from pathlib import Path
import uuid
from ..utils.io import ARTIFACTS_JOBS, now_iso, write_json, ensure_dirs
from ..utils.seeds import set_global_seed


def run_job(job_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Run a job synchronously and persist job record to artifacts\jobs.
    job_type: "train" | "evaluate"
    payload must include module_id and may include seed and other params.
    """
    ensure_dirs()
    job_id = f"{job_type}_{uuid.uuid4().hex[:10]}"
    record = {
        "job_id": job_id,
        "type": job_type,
        "module_id": payload.get("module_id"),
        "seed": int(payload.get("seed", 1337)),
        "created_at": now_iso(),
        "status": "running"
    }
    write_json(ARTIFACTS_JOBS / f"{job_id}.json", record)

    set_global_seed(record["seed"])  # determinism

    try:
        import importlib
        if job_type == "train":
            mod = importlib.import_module("app.backend.tasks.train")
            out = mod.run(payload)
        elif job_type == "evaluate":
            mod = importlib.import_module("app.backend.tasks.evaluate")
            out = mod.run(payload)
        else:
            # Dynamic task import for specialized jobs (e.g., train_sft, train_dpo, train_cnn, train_tsconv, train_rl,
            # make_bubbles, self_eval). The module must expose run(payload) -> dict.
            try:
                mod = importlib.import_module(f"app.backend.tasks.{job_type}")
                out = mod.run(payload)
            except Exception as _e:
                raise ValueError(f"Unknown job type or import failed: {job_type} ({_e})")
        record.update({
            "status": "finished",
            "finished_at": now_iso(),
            "result": out
        })
    except Exception as e:
        record.update({
            "status": "failed",
            "finished_at": now_iso(),
            "error": str(e)
        })
    finally:
        write_json(ARTIFACTS_JOBS / f"{job_id}.json", record)

    return record
