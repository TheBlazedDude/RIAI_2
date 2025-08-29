from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List
import json
import ast
import string
from ..utils.io import ARTIFACTS_DIR, ARTIFACTS_INDICES, ARTIFACTS_DATASETS, write_json, load_json
from ..utils.seeds import set_global_seed
import random

BUBBLE_DIR: Path = ARTIFACTS_DIR / "bubble"
BUBBLE_MODEL_PATH: Path = BUBBLE_DIR / "model.json"


def _safe_parse_index_line(line: str) -> Dict[str, Any] | None:
    line = line.strip()
    if not line:
        return None
    try:
        rec = ast.literal_eval(line)
        if isinstance(rec, dict) and rec.get("lemma"):
            return rec
    except Exception:
        try:
            rec = json.loads(line)
            if isinstance(rec, dict) and rec.get("lemma"):
                return rec
        except Exception:
            return None
    return None


def _collect_corpus() -> str:
    corpus = ""
    # 1) Synthetic dialogs (JSONL)
    synths = sorted(ARTIFACTS_DATASETS.glob("wordnet_synth_*.jsonl"), key=lambda p: p.name)
    for ds in synths:
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
    # 2) Uploads (JSONL)
    uploads_dir = ARTIFACTS_DATASETS / "uploads"
    if uploads_dir.exists():
        for ds in sorted(uploads_dir.glob("*.jsonl"), key=lambda p: p.name):
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
    # 3) WordNet index lemmas as last resort
    if not corpus:
        idx_path = ARTIFACTS_INDICES / "wordnet-lexicon.jsonl"
        if idx_path.exists():
            try:
                with idx_path.open("r", encoding="utf-8", errors="ignore") as f:
                    for k, line in enumerate(f):
                        if k >= 5000:
                            break
                        rec = _safe_parse_index_line(line)
                        if rec:
                            corpus += f"{rec.get('lemma','')} "
            except Exception:
                pass
    return corpus


def build_bubble_model(seed: int = 1337, order: int = 2) -> Path:
    """Build a minimal character-level bubble model (unigram+bigram) usable across modules.
    Deterministic and offline. Persist to artifacts\\bubble\\model.json
    """
    set_global_seed(seed)
    BUBBLE_DIR.mkdir(parents=True, exist_ok=True)
    corpus = _collect_corpus()
    # If still empty, seed with alphabet and space/punctuation to allow babbling
    if not corpus:
        corpus = (string.ascii_lowercase + " ") * 200
    order = max(1, int(order))
    # Unigram and bigram counts
    uni: Dict[str, int] = {}
    bi: Dict[str, Dict[str, int]] = {}
    # Normalize to lower-case small charset to stabilize determinism footprint
    allowed = set(string.ascii_lowercase + " .,!?:;\n")
    text = "".join([c.lower() if c.lower() in allowed else " " for c in corpus])
    for ch in text:
        uni[ch] = uni.get(ch, 0) + 1
    for i in range(len(text) - 1):
        a, b = text[i], text[i+1]
        bucket = bi.setdefault(a, {})
        bucket[b] = bucket.get(b, 0) + 1
    model = {
        "seed": seed,
        "order": 2,
        "unigram": {k: v for k, v in sorted(uni.items())[:200]},
        "bigram": {k: v for k, v in list(bi.items())[:2000]},
        "built_from": "auto"
    }
    write_json(BUBBLE_MODEL_PATH, model)
    return BUBBLE_MODEL_PATH


def load_bubble_model() -> Dict[str, Any]:
    try:
        return load_json(BUBBLE_MODEL_PATH)
    except Exception:
        return {}


def _sample_from_bucket(bucket: Dict[str, int]) -> str:
    items = sorted(bucket.items(), key=lambda kv: (kv[1], kv[0]))
    total = sum(v for _, v in items)
    if total <= 0:
        return " "
    r = random.randint(1, total)
    acc = 0
    for ch, v in items:
        acc += v
        if r <= acc:
            return ch
    return items[-1][0]


def generate_babble(seed_text: str = "", n_chars: int = 48, seed: int = 1337) -> str:
    set_global_seed(seed)
    model = load_bubble_model()
    uni: Dict[str, int] = model.get("unigram", {}) if isinstance(model, dict) else {}
    bi: Dict[str, Dict[str, int]] = model.get("bigram", {}) if isinstance(model, dict) else {}
    out = list(seed_text)
    prev = out[-1] if out else " "
    for _ in range(max(0, n_chars)):
        bucket = bi.get(prev) if prev in bi else None
        ch = _sample_from_bucket(bucket) if bucket else _sample_from_bucket(uni) if isinstance(uni, dict) and uni else " "
        out.append(ch)
        prev = ch
    return "".join(out)
