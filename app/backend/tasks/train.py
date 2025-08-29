from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List
import csv
import math
from ..core.utils.io import (
    WORDNET_ROOT,
    ARTIFACTS_INDICES,
    ARTIFACTS_DATASETS,
    ARTIFACTS_DIR,
    REGISTRY_MODELS_DIR,
    REGISTRY_NN_DIR,
    write_json,
    now_iso,
    MODULES_DIR,
)
from ..core.utils.seeds import set_global_seed
import json
from ..core.runtime.bubble import build_bubble_model
from ..core.utils.io import load_json

# Note: This module is imported via relative path from core.runtime.scheduler
# ensure imports resolve when package is app.backend


def get_nn_family(nn_id: str | None) -> str | None:
    if not nn_id:
        return None
    p = REGISTRY_NN_DIR / f"{nn_id}.json"
    if not p.exists():
        return None
    try:
        entry = load_json(p)
        fam = entry.get("family") if isinstance(entry, dict) else None
        return str(fam) if fam else None
    except Exception:
        return None


def _wordnet_index_paths() -> List[Path]:
    d = WORDNET_ROOT / "dict"
    return [
        d / "index.noun",
        d / "index.verb",
        d / "index.adj",
        d / "index.adv",
    ]


POS_MAP = {
    "index.noun": "noun",
    "index.verb": "verb",
    "index.adj": "adj",
    "index.adv": "adv",
}


def build_wordnet_index() -> Path:
    ARTIFACTS_INDICES.mkdir(parents=True, exist_ok=True)
    out = ARTIFACTS_INDICES / "wordnet-lexicon.jsonl"
    count = 0
    with out.open("w", encoding="utf-8") as wf:
        for p in _wordnet_index_paths():
            if not p.exists():
                continue
            pos = POS_MAP.get(p.name, "?")
            with p.open("r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith(" ") or line.startswith("#"):
                        continue
                    parts = line.split()
                    # heuristic: offsets are the trailing integers; lemma is first token
                    if len(parts) < 3:
                        continue
                    lemma = parts[0]
                    # find last N integer tokens (sense offsets); ensure at least one
                    offsets: List[int] = []
                    for tok in parts[::-1]:
                        try:
                            offsets.append(int(tok))
                        except ValueError:
                            # stop when tokens no longer parse as int (reached non-offset zone)
                            break
                    if not offsets:
                        continue
                    offsets = list(reversed(offsets))
                    rec = {
                        "lemma": lemma,
                        "pos": pos,
                        "offsets": offsets[:8],  # cap to keep file small-ish
                    }
                    wf.write(f"{rec}\n")
                    count += 1
    # write small metrics-ish sidecar if desired later
    return out


def register_model(module_id: str, model_id: str, capability: str, task: str, extra: Dict[str, Any] | None = None, nn_id: str | None = None) -> Path:
    entry = {
        "id": model_id,
        "name": model_id,
        "capability": capability,
        "task": task,
        "created_at": now_iso(),
        "metrics": {},
    }
    if nn_id:
        entry["nn_id"] = nn_id
    if extra:
        entry.update(extra)
    REGISTRY_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    path = REGISTRY_MODELS_DIR / f"{model_id}.json"
    write_json(path, entry)
    return path


def train_predictor_baseline(payload: Dict[str, Any]) -> Dict[str, Any]:
    seed = int(payload.get("seed", 1337))
    nn_id = payload.get("nn_id")
    fam = get_nn_family(nn_id)
    # Choose a small deterministic window based on family
    window = 5
    if fam in ("vision", "vision_edge", "vision_detection", "vision_segmentation", "vision_transformer"):
        window = 3
    elif fam in ("sequence_model", "nlp_transformer", "nlp"):
        window = 5
    elif fam in ("rl", "graph"):
        window = 7
    # Checkpoint and model id (include nn_id if provided to avoid collisions)
    base_id = f"predictor_ma_{seed}"
    model_id = base_id if not nn_id else f"predictor_{nn_id}_{seed}"
    ckpt_dir = MODULES_DIR / "predictor-finance" / "models"
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    ckpt = {"type": "moving_average", "window": window, "seed": seed, "nn_id": nn_id}
    write_json(ckpt_dir / f"{model_id}.json", ckpt)
    reg_path = register_model("predictor-finance", model_id, "predictor", "forecast", {"checkpoint": str(ckpt_dir / f"{model_id}.json"), "window": window, "train_seed": seed}, nn_id=nn_id)
    return {"model_id": model_id, "registry": str(reg_path)}


def build_chat_ngram_from_datasets(seed: int, order: int = 3) -> Path:
    """Build a tiny char-level n-gram from local datasets (synth + uploads) and persist.
    Deterministic and offline; caps contexts for footprint.
    """
    from collections import defaultdict
    set_global_seed(seed)
    chat_dir = ARTIFACTS_DIR / "chat"
    chat_dir.mkdir(parents=True, exist_ok=True)
    out_path = chat_dir / "lm_ngram.json"

    # Collect sources
    synths = sorted(ARTIFACTS_DATASETS.glob("wordnet_synth_*.jsonl"), key=lambda p: p.name)
    uploads_dir = ARTIFACTS_DATASETS / "uploads"
    uploads = sorted(uploads_dir.glob("*.jsonl"), key=lambda p: p.name) if uploads_dir.exists() else []
    sources = synths + uploads

    corpus = ""
    built_from = None
    if sources:
        built_from = ",".join([p.name for p in sources[:3]]) + ("+" if len(sources) > 3 else "")
        for ds in sources:
            try:
                with ds.open("r", encoding="utf-8") as f:
                    for k, line in enumerate(f):
                        if k >= 2000:
                            break
                        try:
                            obj = json.loads(line)
                        except Exception:
                            obj = {"text": line.strip()}
                        txt = str(obj.get("response", "")) + "\n" + str(obj.get("prompt", obj.get("text", ""))) + "\n"
                        corpus += txt
            except Exception:
                continue

    if not corpus:
        # As last resort, create a minimal corpus
        corpus = "hello world " * 100

    order = max(1, int(order))
    counts: Dict[str, Dict[str, int]] = defaultdict(dict)
    for i in range(len(corpus) - order):
        ctx = corpus[i:i+order]
        nxt = corpus[i+order]
        bucket = counts.setdefault(ctx, {})
        bucket[nxt] = bucket.get(nxt, 0) + 1

    # Persist capped counts for footprint
    capped = {k: v for k, v in list(counts.items())[:20000]}
    write_json(out_path, {"order": order, "counts": capped, "seed": seed, "built_from": built_from})
    return out_path


def train_chat_core(payload: Dict[str, Any]) -> Dict[str, Any]:
    seed = int(payload.get("seed", 1337))
    nn_id = payload.get("nn_id")
    fam = get_nn_family(nn_id)
    # Determine tiny LM order by family (deterministic, small footprints)
    order = 3
    if fam in ("feedforward",):
        order = 2
    elif fam in ("nlp_transformer",):
        order = 4
    elif fam in ("sequence_model",):
        order = 3
    # Build/update tiny LM from datasets and register a retrieval-first chat model
    lm_path = build_chat_ngram_from_datasets(seed, order=order)
    # Also (re)build shared bubble model for early-stage babbling across modules
    try:
        bubble_path = build_bubble_model(seed)
    except Exception:
        bubble_path = None
    # Model id: keep legacy id for no nn_id, otherwise include nn_id to avoid collisions
    base_id = f"chat_retrieval_{seed}"
    model_id = base_id if not nn_id else f"chat_{nn_id}_{seed}"
    reg_path = register_model("chat-core", model_id, "chat", "dialogue", {"mode": "retrieval+ngram", "lm_path": str(lm_path), "order": order, "train_seed": seed}, nn_id=nn_id)
    out = {"model_id": model_id, "registry": str(reg_path), "lm": str(lm_path)}
    if bubble_path:
        out["bubble"] = str(bubble_path)
    return out


def train_lexicon(payload: Dict[str, Any]) -> Dict[str, Any]:
    seed = int(payload.get("seed", 1337))
    # Build index and bubble (shared)
    idx = str(build_wordnet_index())
    try:
        bub = str(build_bubble_model(seed))
    except Exception:
        bub = None
    out = {"index": idx}
    if bub:
        out["bubble"] = bub
    return out


MODULE_ACTIONS = {
    "lexicon-wordnet3": train_lexicon,
    "chat-core": train_chat_core,
    "predictor-finance": train_predictor_baseline,
}


def run(payload: Dict[str, Any]) -> Dict[str, Any]:
    module_id = payload.get("module_id")
    seed = int(payload.get("seed", 1337))
    set_global_seed(seed)
    if module_id not in MODULE_ACTIONS:
        raise ValueError(f"Unknown module_id: {module_id}")
    action = MODULE_ACTIONS[module_id]
    out = action(payload)
    out.update({"module_id": module_id, "seed": seed, "status": "ok"})
    return out
