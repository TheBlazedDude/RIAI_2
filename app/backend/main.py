from fastapi import FastAPI, Body
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import json
from datetime import datetime
import uuid

app = FastAPI(title="Modular Offline AI App", version="0.1.0-alpha1")

# Enable CORS for local frontend development (Vite default ports: 5173/5174)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ROOT = Path(__file__).resolve().parents[2]
MODULES_DIR = ROOT / "app" / "modules"
SCHEMA_PATH = ROOT / "docs" / "specs" / "module_manifest_schema.json"
REGISTRY_DIR = ROOT / "app" / "registry"
REGISTRY_WS_DIR = REGISTRY_DIR / "workspaces"
REGISTRY_NN_DIR = REGISTRY_DIR / "neural_nets"
REGISTRY_MODELS_DIR = REGISTRY_DIR / "models"
REGISTRY_DATASETS_DIR = REGISTRY_DIR / "datasets"
GUARDRAILS_DIR = REGISTRY_DIR / "guardrails"
ARTIFACTS_DIR = ROOT / "app" / "artifacts"
ARTIFACTS_INDICES = ARTIFACTS_DIR / "indices"
ARTIFACTS_METRICS = ARTIFACTS_DIR / "metrics"
ARTIFACTS_LOGS = ARTIFACTS_DIR / "logs"
ARTIFACTS_JOBS = ARTIFACTS_DIR / "jobs"
ARTIFACTS_TRACES = ARTIFACTS_DIR / "traces"
ARTIFACTS_DATASETS = ARTIFACTS_DIR / "datasets"

# Ensure essential directories exist
for d in [REGISTRY_WS_DIR, REGISTRY_NN_DIR, REGISTRY_MODELS_DIR, REGISTRY_DATASETS_DIR, GUARDRAILS_DIR,
          ARTIFACTS_DIR, ARTIFACTS_INDICES, ARTIFACTS_METRICS, ARTIFACTS_LOGS, ARTIFACTS_JOBS, ARTIFACTS_TRACES, ARTIFACTS_DATASETS]:
    d.mkdir(parents=True, exist_ok=True)

# --- Offline bootstrap of essential datasets and indices (deterministic, no network) ---
def _ensure_bootstrap_assets():
    try:
        seed = 1337
        # Build WordNet index if missing
        try:
            idx_path = ARTIFACTS_INDICES / "wordnet-lexicon.jsonl"
            if not idx_path.exists():
                from app.backend.tasks.train import build_wordnet_index
                idx_path = build_wordnet_index()
        except Exception:
            pass
        # Generate synthetic WordNet dialogs if missing
        try:
            ds_path = ARTIFACTS_DATASETS / f"wordnet_synth_{seed}.jsonl"
            if not ds_path.exists():
                from app.backend.tasks.evaluate import synth_wordnet_dialogs
                ds_path = synth_wordnet_dialogs(seed)
        except Exception:
            pass
        # Register synthetic dialogs dataset in registry if not present
        try:
            from app.backend.core.registry.datasets import register_dataset as _reg_ds, list_datasets as _list_ds
            want_id = f"wordnet_synth_{seed}"
            have = any((isinstance(e, dict) and e.get("id") == want_id) for e in _list_ds())
            ds_path2 = ARTIFACTS_DATASETS / f"wordnet_synth_{seed}.jsonl"
            if (not have) and ds_path2.exists():
                _reg_ds(want_id, f"WordNet Synthetic Dialogs ({seed})", [ds_path2])
        except Exception:
            pass
        # Register predictor OHLCV sample dataset if available
        try:
            from app.backend.core.registry.datasets import register_dataset as _reg_ds2, list_datasets as _list_ds2
            sample_csv = MODULES_DIR / "predictor-finance" / "data" / "samples" / "ohlcv.csv"
            if sample_csv.exists():
                have2 = any((isinstance(e, dict) and e.get("id") == "predictor_ohlcv_sample") for e in _list_ds2())
                if not have2:
                    _reg_ds2("predictor_ohlcv_sample", "Predictor OHLCV Sample", [sample_csv])
        except Exception:
            pass
        # Ensure uploads dir exists for user-provided data (even if unused)
        try:
            (ARTIFACTS_DATASETS / "uploads").mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
    except Exception:
        # Never block API startup due to bootstrap
        pass

# Invoke bootstrap at import time
_ensure_bootstrap_assets()

PENDING_WS_PATH = REGISTRY_WS_DIR / "pending.json"
GUARDRAILS_CONFIG = GUARDRAILS_DIR / "config.json"

# Mount static frontend if built
FRONTEND_DIST = ROOT / "app" / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/app", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")

# Simple offline guard: no external calls are implemented; runtime should not perform network I/O.


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def compute_sha256(path: Path, chunk_size: int = 65536) -> str:
    import hashlib
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


# Preload schema and required fields to avoid external jsonschema dependency
try:
    _schema = load_json(SCHEMA_PATH)
    _schema_required = list(_schema.get("required", []))
except Exception:
    _schema = None
    _schema_required = [
        "id", "name", "version", "description",
        "capabilities", "task", "inputs", "outputs",
        "ui_panels", "model_constraints", "pipelines",
        "resources", "guardrails", "autotrain", "schema_version"
    ]


@app.get("/api/health")
def health():
    return {"status": "ok", "offline": True}


@app.get("/api/modules")
def list_modules():
    # Use centralized discovery to avoid drift with schema/validation rules
    try:
        from app.backend.core.runtime.loader import discover_modules
        discovered = discover_modules()
        modules = []
        for m in discovered:
            if isinstance(m, dict) and m.get("error"):
                modules.append({"id": m.get("id"), "error": m.get("error")})
            else:
                modules.append({
                    "id": m.get("id"),
                    "name": m.get("name", m.get("id")),
                    "version": m.get("version", "0.0.0"),
                    "description": m.get("description", ""),
                    "capabilities": m.get("capabilities", []),
                    "task": m.get("task"),
                    "inputs": m.get("inputs", []),
                    "outputs": m.get("outputs", []),
                    "ui_panels": m.get("ui_panels", []),
                    "resources": m.get("resources", {}),
                    "permissions": m.get("permissions", {}),
                })
        return {"modules": modules}
    except Exception:
        # Fallback to previous simple scan if loader import fails
        modules = []
        for manifest in MODULES_DIR.glob("*/manifest.json"):
            try:
                data = load_json(manifest)
                for key in _schema_required:
                    if key not in data:
                        raise ValueError(f"manifest missing field: {key}")
                modules.append({
                    "id": data.get("id", manifest.parent.name),
                    "name": data.get("name", manifest.parent.name),
                    "version": data.get("version", "0.0.0"),
                    "description": data.get("description", ""),
                    "capabilities": data.get("capabilities", []),
                    "task": data.get("task"),
                    "inputs": data.get("inputs", []),
                    "outputs": data.get("outputs", []),
                    "ui_panels": data.get("ui_panels", []),
                    "resources": data.get("resources", {}),
                    "permissions": data.get("permissions", {}),
                })
            except Exception as e:
                modules.append({"id": manifest.parent.name, "error": str(e)})
        return {"modules": modules}


@app.get("/api/readiness")
def readiness():
    def make_err(code: str, human: str, hint: str, log_name: str, extra: dict | None = None):
        item = {
            "error_code": code,
            "human_message": human,
            "hint": hint,
            "where_to_find_logs": str(ARTIFACTS_LOGS / log_name)
        }
        if extra:
            item.update(extra)
        return item

    modules_resp = list_modules()
    errors = []

    # Manifests validation results
    for m in modules_resp["modules"]:
        if isinstance(m, dict) and m.get("error"):
            errors.append(make_err(
                "manifest_invalid",
                f"Module manifest {m.get('id')} is invalid.",
                "Validate fields against docs/specs/module_manifest_schema.json.",
                "modules.txt",
                {"details": m.get("error"), "module_id": m.get("id")}
            ))

    # Load pending workspace (selected modules)
    try:
        ws = load_json(PENDING_WS_PATH) if PENDING_WS_PATH.exists() else {"selected_modules": []}
    except Exception as e:
        errors.append(make_err(
            "workspace_read_failed",
            f"Failed to read pending workspace: {e}",
            "Re-save your selection on Site 1.",
            "workspace.txt"
        ))
        ws = {"selected_modules": []}

    selected = ws.get("selected_modules", [])

    # Mapping completeness and registry verification (mappings.json expected from Site 2)
    mappings_path = REGISTRY_WS_DIR / "mappings.json"
    mappings = None
    if selected and not mappings_path.exists():
        errors.append(make_err(
            "mapping_incomplete",
            "One or more selected modules are not Ready (no model mappings).",
            "Open Site 2 (Model Selection & Ops) and map exactly one compatible model per module.",
            "workspace.txt",
            {"selected_modules": selected}
        ))
    elif mappings_path.exists():
        try:
            mappings = load_json(mappings_path)
        except Exception as e:
            errors.append(make_err(
                "mapping_read_failed",
                f"Failed to read mappings.json: {e}",
                "Re-save mappings on Site 2.",
                "workspace.txt"
            ))
        if isinstance(mappings, dict):
            # Build module map for capability cross-checks
            mod_resp = list_modules()
            mod_map_full = {m.get("id"): m for m in mod_resp.get("modules", []) if isinstance(m, dict) and m.get("id")}
            module_map = mappings.get("module_map") if isinstance(mappings.get("module_map"), dict) else None
            cap_map = mappings.get("capability_map") if isinstance(mappings.get("capability_map"), dict) else None
            if module_map:
                for mid in selected:
                    model_id = module_map.get(mid)
                    if not model_id:
                        errors.append(make_err(
                            "mapping_incomplete",
                            f"Module {mid} has no mapped model.",
                            "Map exactly one compatible model for this module.",
                            "workspace.txt",
                            {"module_id": mid}
                        ))
                        continue
                    model_path = REGISTRY_MODELS_DIR / f"{model_id}.json"
                    if not model_path.exists():
                        errors.append(make_err(
                            "registry_missing",
                            f"Missing registry entry {str(model_path)}.",
                            "Create model or import registry entry.",
                            "registry.txt",
                            {"model_id": model_id}
                        ))
                    else:
                        try:
                            model_entry = load_json(model_path)
                            # Verify NN entry if referenced
                            nn_id = model_entry.get("nn_id")
                            if nn_id:
                                nn_path = REGISTRY_NN_DIR / f"{nn_id}.json"
                                if not nn_path.exists():
                                    errors.append(make_err(
                                        "registry_missing",
                                        f"Missing registry entry {str(nn_path)}.",
                                        "Create NN or import registry entry.",
                                        "registry.txt",
                                        {"nn_id": nn_id}
                                    ))
                            # Verify datasets if referenced
                            for ds_id in model_entry.get("dataset_ids", []):
                                ds_path = REGISTRY_DATASETS_DIR / f"{ds_id}.json"
                                if not ds_path.exists():
                                    errors.append(make_err(
                                        "registry_missing",
                                        f"Missing registry entry {str(ds_path)}.",
                                        "Register dataset or import registry entry.",
                                        "registry.txt",
                                        {"dataset_id": ds_id}
                                    ))
                                else:
                                    try:
                                        ds_entry = load_json(ds_path)
                                        for fdesc in ds_entry.get("files", []):
                                            fpath = Path(fdesc.get("path"))
                                            if not fpath.is_absolute():
                                                fpath = ROOT / fpath
                                            if not fpath.exists():
                                                errors.append(make_err(
                                                    "dataset_missing",
                                                    f"Dataset file missing: {str(fpath)}",
                                                    "Re-import dataset or regenerate.",
                                                    "datasets.txt",
                                                    {"dataset_id": ds_id}
                                                ))
                                            else:
                                                sha = fdesc.get("sha256")
                                                if sha:
                                                    calc = compute_sha256(fpath)
                                                    if sha.lower() != calc.lower():
                                                        errors.append(make_err(
                                                            "dataset_checksum_mismatch",
                                                            f"Dataset checksum mismatch: {str(fpath)}",
                                                            "Regenerate with the same seed or update registry.",
                                                            "datasets.txt",
                                                            {"dataset_id": ds_id, "expected": sha, "actual": calc}
                                                        ))
                                    except Exception:
                                        pass
                            # Verify metrics artifact presence per capability
                            cap = model_entry.get("capability") or (mod_map_full.get(mid) or {}).get("capabilities", [None])[0]
                            if cap:
                                metrics_path = ARTIFACTS_METRICS / cap / f"{model_id}.json"
                                if not metrics_path.exists():
                                    errors.append(make_err(
                                        "artifact_missing",
                                        f"Missing artifact: {str(metrics_path)}",
                                        "Run evaluation to produce metrics.",
                                        "artifacts.txt",
                                        {"model_id": model_id}
                                    ))
                                # Enforce runnable chat model when not in retrieval mode
                                if cap == "chat":
                                    mode = str(model_entry.get("mode", "")) if isinstance(model_entry.get("mode"), (str,)) else ""
                                    if not mode.startswith("retrieval"):
                                        weights_path = model_entry.get("weights_path")
                                        tokenizer_path = model_entry.get("tokenizer_path")
                                        adapter = model_entry.get("inference_adapter")
                                        missing = []
                                        def _resolve(p):
                                            if not p:
                                                return None
                                            q = Path(p)
                                            if not q.is_absolute():
                                                q = ROOT / q
                                            return q
                                        w_path = _resolve(weights_path)
                                        t_path = _resolve(tokenizer_path)
                                        if not weights_path:
                                            missing.append("weights_path")
                                        if not tokenizer_path:
                                            missing.append("tokenizer_path")
                                        if not adapter:
                                            missing.append("inference_adapter")
                                        fs_missing = []
                                        if w_path and (not w_path.exists() or (w_path.exists() and w_path.is_file() and w_path.stat().st_size <= 0)):
                                            fs_missing.append(str(w_path))
                                        if t_path and (not t_path.exists() or (t_path.exists() and t_path.is_file() and t_path.stat().st_size <= 0)):
                                            fs_missing.append(str(t_path))
                                        if missing or fs_missing:
                                            details = {}
                                            if missing:
                                                details["missing_fields"] = missing
                                            if fs_missing:
                                                details["missing_files"] = fs_missing
                                            errors.append(make_err(
                                                "model_not_runnable",
                                                "Model not runnable (no weights).",
                                                "Train or attach local weights/tokenizer and set an inference_adapter, or switch the model to retrieval mode.",
                                                "runtime.txt",
                                                {"model_id": model_id, **details}
                                            ))
                        except Exception:
                            pass
            elif cap_map:
                for mid in selected:
                    m = mod_map_full.get(mid) or {}
                    found = False
                    for cap in (m.get("capabilities") or []):
                        model_id = cap_map.get(cap)
                        if model_id:
                            found = True
                            model_path = REGISTRY_MODELS_DIR / f"{model_id}.json"
                            if not model_path.exists():
                                errors.append(make_err(
                                    "registry_missing",
                                    f"Missing registry entry {str(model_path)}.",
                                    "Create model or import registry entry.",
                                    "registry.txt",
                                    {"model_id": model_id}
                                ))
                            else:
                                cap_dir = ARTIFACTS_METRICS / cap
                                metrics_path = cap_dir / f"{model_id}.json"
                                if not metrics_path.exists():
                                    errors.append(make_err(
                                        "artifact_missing",
                                        f"Missing artifact: {str(metrics_path)}",
                                        "Run evaluation to produce metrics.",
                                        "artifacts.txt",
                                        {"model_id": model_id}
                                    ))
                    if not found:
                        errors.append(make_err(
                            "mapping_incomplete",
                            f"Module {mid} has no mapped model via capability_map.",
                            "Map exactly one compatible model for this module.",
                            "workspace.txt",
                            {"module_id": mid}
                        ))

    # WordNet root check
    wn_root = ROOT / "WordNet-3.0"
    if not wn_root.exists():
        errors.append(make_err(
            "wordnet_root_missing",
            f"WordNet-3.0 folder not found at {str(wn_root)}",
            "Place the WordNet-3.0 folder at the repository root.",
            "wordnet.txt"
        ))

    # If any selected module has chat capability, require WordNet index artifact and synthetic dialogs
    try:
        mod_map = {m.get("id"): m for m in modules_resp["modules"] if isinstance(m, dict) and m.get("id")}
        selected_mods = [mod_map[mid] for mid in selected if mid in mod_map]
        chat_selected = any("chat" in (m.get("capabilities") or []) for m in selected_mods)
        if chat_selected:
            index_path = ARTIFACTS_INDICES / "wordnet-lexicon.jsonl"
            if not index_path.exists():
                errors.append(make_err(
                    "wordnet_index_missing",
                    f"WordNet index not found at {str(index_path)}",
                    "Run modules/lexicon-wordnet3/pipelines/build_index.py to build the retrieval index.",
                    "wordnet.txt"
                ))
            synths = list(ARTIFACTS_DATASETS.glob("wordnet_synth_*.jsonl"))
            if not synths:
                errors.append(make_err(
                    "wordnet_synth_missing",
                    f"Synthetic dialog dataset not found under {str(ARTIFACTS_DATASETS)}",
                    "Run modules/lexicon-wordnet3/pipelines/synth_dialogs.py --seed 1337 to generate.",
                    "wordnet.txt"
                ))
    except Exception as e:
        errors.append(make_err(
            "readiness_internal",
            f"Error checking chat readiness: {e}",
            "See logs.",
            "wordnet.txt"
        ))

    # Predictor dataset check (sample presence)
    predictor_manifest = MODULES_DIR / "predictor-finance" / "manifest.json"
    if predictor_manifest.exists():
        sample_csv = MODULES_DIR / "predictor-finance" / "data" / "samples" / "ohlcv.csv"
        if not sample_csv.exists():
            errors.append(make_err(
                "predictor_dataset_missing",
                f"Predictor sample dataset not found at {str(sample_csv)}",
                "Place ohlcv.csv under modules/predictor-finance/data/samples or generate synthetic data.",
                "datasets.txt"
            ))

    # Guardrails validation
    try:
        cfg = load_json(GUARDRAILS_CONFIG) if GUARDRAILS_CONFIG.exists() else default_guardrails()
        if not isinstance(cfg.get("max_tokens", 0), int) or cfg.get("max_tokens", 0) < 1:
            errors.append(make_err(
                "guardrails_invalid",
                "Guardrails max_tokens must be an integer >= 1.",
                "Open the Guardrails panel and set a valid max_tokens.",
                "guardrails.txt"
            ))
        if "allowed_file_types" in cfg and isinstance(cfg["allowed_file_types"], list) and len(cfg["allowed_file_types"]) == 0:
            errors.append(make_err(
                "guardrails_invalid",
                "Guardrails allowed_file_types cannot be empty when files are enabled.",
                "Add at least one file extension or disable file access in modules.",
                "guardrails.txt"
            ))
    except Exception as e:
        errors.append(make_err(
            "guardrails_read_failed",
            f"Failed to read guardrails: {e}",
            "Reset guardrails via POST /api/guardrails.",
            "guardrails.txt"
        ))

    # Filesystem writability checks for metrics and traces
    for target_dir, log_name in [(ARTIFACTS_METRICS, "fs.txt"), (ARTIFACTS_TRACES, "fs.txt")]:
        try:
            probe = target_dir / f".__writetest_{uuid.uuid4().hex}.tmp"
            with probe.open("w", encoding="utf-8") as f:
                f.write("ok")
            probe.unlink(missing_ok=True)
        except Exception as e:
            errors.append(make_err(
                "filesystem_readonly",
                f"Artifacts directory not writable: {str(target_dir)} ({e})",
                "Fix permissions or path.",
                log_name
            ))

    status = "ready" if not errors else "blocked"
    return {
        "status": status,
        "errors": errors,
        "workspace": ws,
        "guardrails": (load_json(GUARDRAILS_CONFIG) if GUARDRAILS_CONFIG.exists() else default_guardrails())
    }


@app.get("/api/workspace")
def get_workspace():
    if PENDING_WS_PATH.exists():
        ws = load_json(PENDING_WS_PATH)
        # Backward compatibility defaults
        if "name" not in ws:
            ws["name"] = "Pending Workspace"
        if "seed" not in ws:
            ws["seed"] = 1337
        return ws
    return {"id": "pending", "name": "Pending Workspace", "selected_modules": [], "seed": 1337, "updated_at": None}


@app.post("/api/workspace")
def save_workspace(payload: dict = Body(...)):
    selected = payload.get("selected_modules", [])
    if not isinstance(selected, list):
        return JSONResponse(status_code=400, content={"error_code": "invalid_payload", "human_message": "selected_modules must be a list of module ids"})
    name = payload.get("name") or "Pending Workspace"
    try:
        seed = int(payload.get("seed", 1337))
    except Exception:
        seed = 1337
    snapshot = {
        "id": "pending",
        "name": name,
        "selected_modules": selected,
        "seed": seed,
        "updated_at": datetime.now().astimezone().isoformat()
    }
    write_json(PENDING_WS_PATH, snapshot)
    return {"ok": True, "workspace": snapshot}


# -------- Registry Stubs --------

@app.get("/api/registry/neural_nets")
def list_neural_nets():
    # Seed registry from neural_networks.yaml if present, then list all
    def _parse_catalog() -> list[dict]:
        cat_path = ROOT / "neural_networks.yaml"
        if not cat_path.exists():
            return []
        ids_names: list[dict] = []
        current: dict | None = None
        try:
            for raw in cat_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = raw.rstrip()
                if not line.strip() or line.strip().startswith("#"):
                    continue
                if line.lstrip().startswith("- id:"):
                    # Start a new block
                    # Extract id token
                    try:
                        tid = line.split(":", 1)[1].strip()
                    except Exception:
                        tid = None
                    tid = tid.strip('"') if isinstance(tid, str) else tid
                    if current:
                        ids_names.append(current)
                    current = {"id": tid}
                elif current is not None:
                    # parse simple key: value lines at same indent
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        k = parts[0].strip()
                        v = parts[1].strip()
                        v = v.strip('"')
                        if k in ("name", "family") and v:
                            current[k] = v
            if current:
                ids_names.append(current)
        except Exception:
            return []
        # normalize
        out = []
        for e in ids_names:
            if isinstance(e, dict) and e.get("id"):
                out.append({
                    "id": str(e.get("id")),
                    "name": str(e.get("name", e.get("id"))),
                    "family": e.get("family")
                })
        return out

    # Seed missing entries into registry
    try:
        catalog = _parse_catalog()
        existing_ids = {p.stem for p in REGISTRY_NN_DIR.glob("*.json")}
        for entry in catalog:
            nn_id = entry.get("id")
            if not nn_id or nn_id in existing_ids:
                continue
            write_json(REGISTRY_NN_DIR / f"{nn_id}.json", {
                "id": nn_id,
                "name": entry.get("name", nn_id),
                "family": entry.get("family")
            })
            existing_ids.add(nn_id)
    except Exception:
        pass

    items = []
    for path in REGISTRY_NN_DIR.glob("*.json"):
        try:
            items.append(load_json(path))
        except Exception:
            pass
    return {"neural_nets": items}


@app.post("/api/registry/neural_nets")
def create_neural_net(payload: dict = Body(...)):
    nn_id = payload.get("id") or f"nn_{uuid.uuid4().hex[:8]}"
    # Accept full NNSpec fields; keep backward compatibility with minimal entries.
    entry = {
        "id": nn_id,
        "name": payload.get("name", nn_id),
        "family": payload.get("family"),
        "task": payload.get("task"),
        "input": payload.get("input"),
        "output": payload.get("output"),
        "init": payload.get("init"),
        "spec": payload.get("spec"),  # optional full spec blob
        "created_at": datetime.now().astimezone().isoformat(),
    }
    # Include optional visualization helpers if provided by frontend (param counts/shapes)
    if "param_count" in payload:
        entry["param_count"] = payload.get("param_count")
    if "shapes" in payload:
        entry["shapes"] = payload.get("shapes")
    write_json(REGISTRY_NN_DIR / f"{nn_id}.json", {k: v for k, v in entry.items() if v is not None})
    return {"ok": True, "neural_net": entry}


@app.get("/api/registry/models")
def list_models():
    items = []
    for path in REGISTRY_MODELS_DIR.glob("*.json"):
        try:
            items.append(load_json(path))
        except Exception:
            pass
    return {"models": items}


@app.post("/api/registry/models")
def create_model(payload: dict = Body(...)):
    model_id = payload.get("id") or f"model_{uuid.uuid4().hex[:8]}"
    entry = {
        "id": model_id,
        "name": payload.get("name", model_id),
        "capability": payload.get("capability"),
        "task": payload.get("task"),
        "nn_id": payload.get("nn_id"),
        "train_seed": payload.get("train_seed"),
        "dataset_id": payload.get("dataset_id"),
        "dataset_hash": payload.get("dataset_hash"),
        "created_at": datetime.now().astimezone().isoformat(),
        "metrics": payload.get("metrics", {}),
    }
    # Remove keys with None to keep files tidy
    entry = {k: v for k, v in entry.items() if v is not None}
    write_json(REGISTRY_MODELS_DIR / f"{model_id}.json", entry)
    return {"ok": True, "model": entry}


# -------- Runtime Stubs --------

@app.post("/api/runtime/start")
def runtime_start(payload: dict = Body(...)):
    # Enforce workspace gating: block if readiness is not ready
    rd = readiness()
    if rd.get("status") != "ready":
        return JSONResponse(status_code=400, content={
            "error_code": "workspace_not_ready",
            "human_message": "Workspace is not ready. Resolve readiness errors before starting runtime.",
            "errors": rd.get("errors", [])
        })
    return {"ok": True, "message": "Runtime start requested", "payload": payload}


@app.post("/api/runtime/stop")
def runtime_stop(payload: dict = Body(...)):
    return {"ok": True, "message": "Runtime stop requested", "payload": payload}


@app.post("/api/runtime/post")
def runtime_post(payload: dict = Body(...)):
    # Apply guardrails to text input; generate retrieval-based answer from WordNet index
    cfg = load_json(GUARDRAILS_CONFIG) if GUARDRAILS_CONFIG.exists() else default_guardrails()
    text = payload.get("text") if isinstance(payload, dict) else None
    processed = None
    answer = None
    if isinstance(text, str):
        try:
            from app.backend.core.runtime.guardrails import apply_guardrails
            processed = apply_guardrails(text, cfg)
        except Exception as e:
            processed = {"original": text, "result": text, "actions": [], "error": str(e)}
        # Retrieval-based answer + learning counts
        try:
            from app.backend.core.runtime.chat import generate_answer
            raw, meta = generate_answer(text)
            # Anti-echo: if output equals input after normalization, prepend a minimal explanation
            def _norm(s: str) -> str:
                import re as _re
                return _re.sub(r"\W+", "", (s or "").lower()).strip()
            if _norm(raw) == _norm(text):
                raw = f"Answer: {raw}"
            # Guard the generated answer using same guardrails
            try:
                from app.backend.core.runtime.guardrails import apply_guardrails as _apply
                guarded = _apply(raw, cfg)
            except Exception:
                guarded = {"original": raw, "result": raw, "actions": []}
            # Re-apply anti-echo on guarded result
            if isinstance(guarded, dict) and _norm(guarded.get("result", "")) == _norm(text):
                guarded["result"] = f"Answer: {guarded.get('result')}"
                if isinstance(guarded.get("actions"), list):
                    guarded["actions"].append({"type": "anti_echo", "reason": "output matched input"})
            answer = {"raw": raw, "guarded": guarded, "meta": meta}
        except Exception as e:
            answer = {"error": str(e)}
    return {"ok": True, "received": payload, "processed": processed, "answer": answer, "guardrails": cfg}


# -------- Datasets (ingestion + list) --------

from app.backend.core.registry.datasets import list_datasets as _list_datasets_reg, register_dataset as _register_dataset
from app.backend.core.utils.io import ARTIFACTS_DATASETS, ROOT

@app.get("/api/datasets")
def api_list_datasets():
    try:
        return {"datasets": _list_datasets_reg()}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error_code": "datasets_list_failed", "human_message": str(e)})


@app.post("/api/datasets/ingest")
def api_ingest_dataset(payload: dict = Body(...)):
    """
    Accepts JSON payload and writes a normalized JSONL under artifacts\\datasets\\uploads.
    Payload shape: {
      id?: string, name?: string, format: 'jsonl'|'text', content: string, capability: 'chat'|'predictor', tags?: []
    }
    For 'text', we wrap content lines as {id, prompt, response} for chat.
    Deterministic ids if not provided.
    """
    try:
        fmt = str(payload.get("format", "jsonl")).lower()
        content = payload.get("content", "")
        ds_id = payload.get("id") or f"upload_{uuid.uuid4().hex[:8]}"
        name = payload.get("name", ds_id)
        capability = payload.get("capability", "chat")
        uploads_dir = ARTIFACTS_DATASETS / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        out_path = uploads_dir / f"{ds_id}.jsonl"
        # Normalize
        if fmt == "jsonl":
            # validate it's line-delimited JSON
            lines = [ln for ln in str(content).splitlines() if ln.strip()]
            with out_path.open("w", encoding="utf-8") as wf:
                for ln in lines:
                    # best-effort parse; re-dump to ensure validity
                    try:
                        obj = json.loads(ln)
                    except Exception:
                        obj = {"text": ln}
                    wf.write(json.dumps(obj, ensure_ascii=False) + "\n")
        elif fmt == "text":
            # each non-empty line becomes a simple chat item
            with out_path.open("w", encoding="utf-8") as wf:
                for k, ln in enumerate(str(content).splitlines()):
                    ln = ln.strip()
                    if not ln:
                        continue
                    obj = {"id": f"t_{k}", "prompt": ln, "response": ln}
                    wf.write(json.dumps(obj, ensure_ascii=False) + "\n")
        elif fmt == "csv":
            # parse CSV lines; each row becomes a chat item using first column as both prompt/response
            import csv as _csv
            with out_path.open("w", encoding="utf-8", newline="") as wf:
                reader = _csv.reader(str(content).splitlines())
                for k, row in enumerate(reader):
                    if not row:
                        continue
                    txt = str(row[0]).strip()
                    if not txt:
                        continue
                    obj = {"id": f"c_{k}", "prompt": txt, "response": txt}
                    wf.write(json.dumps(obj, ensure_ascii=False) + "\n")
        elif fmt == "json":
            # Accept a JSON array of objects or a single object. Convert to JSONL.
            try:
                obj = json.loads(str(content))
            except Exception as e:
                return JSONResponse(status_code=400, content={"error_code": "json_parse_failed", "human_message": f"Invalid JSON: {e}"})
            with out_path.open("w", encoding="utf-8") as wf:
                if isinstance(obj, list):
                    for i, item in enumerate(obj):
                        if not isinstance(item, dict):
                            item = {"text": str(item)}
                        wf.write(json.dumps(item, ensure_ascii=False) + "\n")
                elif isinstance(obj, dict):
                    # if it contains an 'items' array prefer that, else write the object as a single line
                    if isinstance(obj.get("items"), list):
                        for i, item in enumerate(obj["items"]):
                            if not isinstance(item, dict):
                                item = {"text": str(item)}
                            wf.write(json.dumps(item, ensure_ascii=False) + "\n")
                    else:
                        wf.write(json.dumps(obj, ensure_ascii=False) + "\n")
                else:
                    wf.write(json.dumps({"text": str(obj)}, ensure_ascii=False) + "\n")
        else:
            return JSONResponse(status_code=400, content={"error_code": "unsupported_format", "human_message": f"Unsupported format: {fmt}"})
        # Register dataset
        entry = _register_dataset(ds_id, name, [out_path])
        # attach tags/capability for UI if desired
        if payload.get("tags"):
            entry["tags"] = payload.get("tags")
        entry["capability"] = capability
        write_json(REGISTRY_DATASETS_DIR / f"{ds_id}.json", entry)
        return {"ok": True, "dataset": entry}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error_code": "ingest_failed", "human_message": str(e)})


# -------- Metrics --------

@app.get("/api/metrics/latest")
def metrics_latest(capability: str = "chat", model_id: str | None = None):
    # Minimal stub: return empty if none
    path = ARTIFACTS_METRICS / capability
    data = []
    if path.exists():
        for f in path.glob("*.json"):
            try:
                j = load_json(f)
                if (not model_id) or (j.get("model_id") == model_id):
                    data.append(j)
            except Exception:
                pass
    latest = sorted(data, key=lambda x: x.get("timestamp", ""), reverse=True)[:1]
    return {"metrics": latest[0] if latest else {}}


@app.get("/api/metrics/by_id/{metric_file}")
def metrics_by_id(metric_file: str):
    for cap_dir in ARTIFACTS_METRICS.glob("*"):
        candidate = cap_dir / metric_file
        if candidate.exists():
            try:
                return load_json(candidate)
            except Exception:
                break
    return JSONResponse(status_code=404, content={"error_code": "metrics_not_found", "human_message": "Metrics file not found"})


# -------- Jobs Dispatcher Stubs --------

@app.post("/api/train")
def train_job(payload: dict = Body(...)):
    # Run synchronously via local scheduler to produce real artifacts
    try:
        from app.backend.core.runtime.scheduler import run_job
        record = run_job("train", payload)
        return {"ok": record.get("status") == "finished", "job": record}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error_code": "train_failed", "human_message": str(e)})


@app.post("/api/evaluate")
def evaluate_job(payload: dict = Body(...)):
    try:
        from app.backend.core.runtime.scheduler import run_job
        record = run_job("evaluate", payload)
        return {"ok": record.get("status") == "finished", "job": record}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error_code": "evaluate_failed", "human_message": str(e)})


# Specialized training jobs
@app.post("/api/train/sft")
def train_sft_job(payload: dict = Body(...)):
    try:
        from app.backend.core.runtime.scheduler import run_job
        record = run_job("train_sft", payload)
        return {"ok": record.get("status") == "finished", "job": record}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error_code": "train_sft_failed", "human_message": str(e)})


@app.post("/api/train/dpo")
def train_dpo_job(payload: dict = Body(...)):
    try:
        from app.backend.core.runtime.scheduler import run_job
        record = run_job("train_dpo", payload)
        return {"ok": record.get("status") == "finished", "job": record}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error_code": "train_dpo_failed", "human_message": str(e)})


@app.post("/api/train/cnn")
def train_cnn_job(payload: dict = Body(...)):
    try:
        from app.backend.core.runtime.scheduler import run_job
        record = run_job("train_cnn", payload)
        return {"ok": record.get("status") == "finished", "job": record}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error_code": "train_cnn_failed", "human_message": str(e)})


@app.post("/api/train/tsconv")
def train_tsconv_job(payload: dict = Body(...)):
    try:
        from app.backend.core.runtime.scheduler import run_job
        record = run_job("train_tsconv", payload)
        return {"ok": record.get("status") == "finished", "job": record}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error_code": "train_tsconv_failed", "human_message": str(e)})


@app.post("/api/train/rl")
def train_rl_job(payload: dict = Body(...)):
    try:
        from app.backend.core.runtime.scheduler import run_job
        record = run_job("train_rl", payload)
        return {"ok": record.get("status") == "finished", "job": record}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error_code": "train_rl_failed", "human_message": str(e)})


# Tools
@app.post("/api/tools/make_bubbles")
def api_make_bubbles(payload: dict = Body(...)):
    try:
        from app.backend.core.runtime.scheduler import run_job
        record = run_job("make_bubbles", payload)
        return {"ok": record.get("status") == "finished", "job": record}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error_code": "make_bubbles_failed", "human_message": str(e)})


@app.post("/api/tools/self_eval")
def api_self_eval(payload: dict = Body(...)):
    try:
        from app.backend.core.runtime.scheduler import run_job
        record = run_job("self_eval", payload)
        return {"ok": record.get("status") == "finished", "job": record}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error_code": "self_eval_failed", "human_message": str(e)})


@app.get("/api/jobs")
def list_jobs():
    items = []
    for path in ARTIFACTS_JOBS.glob("*.json"):
        try:
            items.append(load_json(path))
        except Exception:
            pass
    items = sorted(items, key=lambda x: x.get("created_at", ""), reverse=True)
    return {"jobs": items}


# -------- Guardrails --------

def default_guardrails():
    return {
        "max_tokens": 256,
        "pii_regex": ["\\b\\d{3}-\\d{2}-\\d{4}\\b"],
        "content_filters": ["hate", "violence"],
        "allowed_file_types": [".txt", ".csv", ".json"]
    }


@app.get("/api/guardrails")
def get_guardrails():
    return load_json(GUARDRAILS_CONFIG) if GUARDRAILS_CONFIG.exists() else default_guardrails()


@app.post("/api/guardrails")
def set_guardrails(payload: dict = Body(...)):
    cfg = default_guardrails()
    cfg.update({k: v for k, v in payload.items() if k in cfg})
    write_json(GUARDRAILS_CONFIG, cfg)
    return {"ok": True, "guardrails": cfg}


# -------- Workspace Mappings --------
@app.get("/api/workspace/mappings")
def get_mappings():
    path = REGISTRY_WS_DIR / "mappings.json"
    return load_json(path) if path.exists() else {"module_map": {}, "capability_map": {}}


@app.post("/api/workspace/mappings")
def save_mappings(payload: dict = Body(...)):
    # Accept either module_map or capability_map, both optional dicts
    data = {
        "module_map": payload.get("module_map", {}),
        "capability_map": payload.get("capability_map", {})
    }
    write_json(REGISTRY_WS_DIR / "mappings.json", data)

    # Auto-evaluate mapped models that are missing metrics so Readiness can pass immediately
    try:
        ws = load_json(PENDING_WS_PATH) if PENDING_WS_PATH.exists() else {"seed": 1337, "selected_modules": []}
        seed = int(ws.get("seed", 1337))
        selected = ws.get("selected_modules", [])
        # Build module lookup with capabilities
        mod_resp = list_modules()
        mod_map_full = {m.get("id"): m for m in mod_resp.get("modules", []) if isinstance(m, dict) and m.get("id")}

        def _ensure_metrics(module_id: str, model_id: str):
            if not module_id or not model_id:
                return
            # Determine capability directory to check metrics path
            cap = None
            reg_path = REGISTRY_MODELS_DIR / f"{model_id}.json"
            if reg_path.exists():
                try:
                    reg = load_json(reg_path)
                    cap = reg.get("capability")
                except Exception:
                    cap = None
            if not cap:
                mod = mod_map_full.get(module_id) or {}
                caps = mod.get("capabilities") or []
                if caps:
                    cap = caps[0]
            if cap:
                metrics_path = ARTIFACTS_METRICS / cap / f"{model_id}.json"
                if not metrics_path.exists():
                    try:
                        # Synchronously evaluate via local scheduler
                        evaluate_job({"module_id": module_id, "seed": seed, "model_id": model_id})
                    except Exception:
                        pass

        # Handle direct module->model mappings
        if isinstance(data.get("module_map"), dict):
            for mid, model_id in data["module_map"].items():
                _ensure_metrics(str(mid), str(model_id))

        # Handle capability->model mappings across selected modules
        if isinstance(data.get("capability_map"), dict):
            cap_map = data["capability_map"]
            for mid in selected:
                mod = mod_map_full.get(mid) or {}
                for cap in (mod.get("capabilities") or []):
                    model_id = cap_map.get(cap)
                    if model_id:
                        _ensure_metrics(str(mid), str(model_id))
    except Exception:
        # Never fail the save due to auto-eval convenience
        pass

    return {"ok": True, "mappings": data}
