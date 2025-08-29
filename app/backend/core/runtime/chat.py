from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Tuple
import json
import ast
import re
import random
from ..utils.io import ARTIFACTS_INDICES, ARTIFACTS_DIR, ARTIFACTS_DATASETS, WORDNET_ROOT, write_json, load_json
from ..utils.seeds import set_global_seed
from .bubble import generate_babble

_INDEX_CACHE: List[Dict[str, Any]] | None = None
_LEMMA_SET: set[str] | None = None
_COUNTS_PATH: Path = ARTIFACTS_DIR / "chat" / "lm_counts.json"
_LM_PATH: Path = ARTIFACTS_DIR / "chat" / "lm_ngram.json"
_LM_CACHE: Dict[str, Any] | None = None


def _safe_parse_line(line: str) -> Dict[str, Any] | None:
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


def load_index() -> List[Dict[str, Any]]:
    global _INDEX_CACHE, _LEMMA_SET
    if _INDEX_CACHE is not None:
        return _INDEX_CACHE
    idx_path = ARTIFACTS_INDICES / "wordnet-lexicon.jsonl"
    recs: List[Dict[str, Any]] = []
    if idx_path.exists():
        with idx_path.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                rec = _safe_parse_line(line)
                if rec:
                    recs.append(rec)
    # build lemma set for quick membership
    _INDEX_CACHE = recs
    _LEMMA_SET = {str(r.get("lemma")).lower() for r in recs}
    return recs


def _get_counts() -> Dict[str, int]:
    try:
        return load_json(_COUNTS_PATH)
    except Exception:
        return {}


def _save_counts(counts: Dict[str, int]) -> None:
    _COUNTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_json(_COUNTS_PATH, counts)


def update_counts(lemma: str) -> Dict[str, int]:
    if not lemma:
        return _get_counts()
    counts = _get_counts()
    counts[lemma] = int(counts.get(lemma, 0)) + 1
    _save_counts(counts)
    return counts


def most_seen_lemma() -> str | None:
    counts = _get_counts()
    if not counts:
        return None
    # deterministic: max by count, then lexicographically
    items = sorted(counts.items(), key=lambda kv: (-int(kv[1]), kv[0]))
    return items[0][0] if items else None


def extract_lemma(text: str) -> str | None:
    # Prefer a quoted token 'like this'
    m = re.search(r"'([^']+)'", text)
    if m:
        return m.group(1).strip().lower()
    # Else, choose the first token present in index lemma set
    load_index()
    global _LEMMA_SET
    if not _LEMMA_SET:
        return None
    tokens = [t.lower() for t in re.findall(r"[A-Za-z]+", text)]
    for tok in tokens:
        if tok in _LEMMA_SET:
            return tok
    # Fallback to most seen lemma (learning bias)
    return most_seen_lemma()


def _find_record_for_lemma(lemma: str) -> Dict[str, Any] | None:
    if not lemma:
        return None
    recs = load_index()
    for r in recs[:100000]:  # safety cap
        if str(r.get("lemma", "")).lower() == lemma:
            return r
    return None


# ---------------- Small offline LM (character-level n-gram) ----------------

def _load_or_build_lm(order: int = 3) -> Dict[str, Any]:
    """Builds or loads a tiny char-level n-gram from local datasets.
    Preference order: prebuilt artifacts\chat\lm_ngram.json → synth datasets → index lemmas.
    Deterministic given the same dataset and seed. Cached and persisted to _LM_PATH.
    """
    global _LM_CACHE
    if _LM_CACHE is not None:
        return _LM_CACHE

    # Prefer prebuilt LM if available
    try:
        if _LM_PATH.exists():
            obj = load_json(_LM_PATH)
            if isinstance(obj, dict) and obj.get("counts"):
                _LM_CACHE = {"order": int(obj.get("order", order)), "counts": obj.get("counts", {}), "seed": int(obj.get("seed", 1337)), "built_from": obj.get("built_from", "prebuilt")}
                return _LM_CACHE
    except Exception:
        pass

    # If an SFT checkpoint exists, preferentially use it (real learned counts)
    try:
        sft_root = ARTIFACTS_DIR / "chat"
        if sft_root.exists():
            # Find latest sft_<seed>/ckpt_sft_*.json deterministically by name
            ckpts = sorted(sft_root.glob("sft_*\\ckpt_sft_*.json"), key=lambda p: p.name)
            if ckpts:
                latest = ckpts[-1]
                obj = load_json(latest)
                if isinstance(obj, dict) and isinstance(obj.get("counts"), dict):
                    _LM_CACHE = {"order": int(obj.get("order", 3)), "counts": obj.get("counts", {}), "seed": int(obj.get("seed", 1337)), "built_from": f"sft:{latest.name}"}
                    # Persist a small aggregated lm_ngram.json for reuse in future runs
                    try:
                        _LM_PATH.parent.mkdir(parents=True, exist_ok=True)
                        write_json(_LM_PATH, {"order": _LM_CACHE["order"], "counts": _LM_CACHE["counts"], "seed": _LM_CACHE["seed"], "built_from": _LM_CACHE["built_from"]})
                    except Exception:
                        pass
                    return _LM_CACHE
    except Exception:
        pass

    model: Dict[str, Any] = {"order": order, "counts": {}, "seed": 1337, "built_from": None}

    # Aggregate corpus from synth and uploads
    corpus = ""
    synths = sorted(ARTIFACTS_DATASETS.glob("wordnet_synth_*.jsonl"), key=lambda p: p.name)
    uploads_dir = ARTIFACTS_DATASETS / "uploads"
    uploads = sorted(uploads_dir.glob("*.jsonl"), key=lambda p: p.name) if uploads_dir.exists() else []
    srcs = synths + uploads
    if srcs:
        model["built_from"] = ",".join([p.name for p in srcs[:3]]) + ("+" if len(srcs) > 3 else "")
        for ds_file in srcs:
            try:
                with ds_file.open("r", encoding="utf-8") as f:
                    for k, line in enumerate(f):
                        if k >= 2000:
                            break
                        try:
                            obj = json.loads(line)
                            txt = str(obj.get("response", "")) + "\n" + str(obj.get("prompt", obj.get("text", ""))) + "\n"
                            corpus += txt
                        except Exception:
                            continue
            except Exception:
                continue

    if not corpus:
        # Fallback to lemmas from index to form a minimal corpus
        for r in load_index()[:5000]:
            corpus += f"{r.get('lemma','')} "

    # Build n-gram counts
    order = max(1, int(order))
    counts: Dict[str, Dict[str, int]] = {}
    for i in range(len(corpus) - order):
        ctx = corpus[i:i+order]
        nxt = corpus[i+order]
        bucket = counts.setdefault(ctx, {})
        bucket[nxt] = bucket.get(nxt, 0) + 1
    model["counts"] = counts

    # Persist small model for reuse
    try:
        _LM_PATH.parent.mkdir(parents=True, exist_ok=True)
        write_json(_LM_PATH, {"order": order, "counts": {k: v for k, v in list(counts.items())[:20000]}, "seed": 1337, "built_from": model["built_from"]})
    except Exception:
        pass

    _LM_CACHE = model
    return model


def _sample_from_counts(d: Dict[str, int]) -> str:
    # Deterministic tie-breaking via sorted items and a fixed PRNG seeded each call upstream
    items = sorted(d.items(), key=lambda kv: (kv[1], kv[0]))  # sort by count then char
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


def _lm_generate(seed_text: str, n_tokens: int = 40, order: int = 3, seed: int = 1337) -> str:
    set_global_seed(seed)
    model = _load_or_build_lm(order=order)
    counts = model.get("counts", {})
    order = int(model.get("order", order))
    if not counts:
        # Fallback to shared Bubble Learner for early-stage babbling
        try:
            return generate_babble(seed_text, n_tokens, seed)
        except Exception:
            # Never echo back the input; provide a minimal offline stub instead
            return "offline continuation"
    ctx = (seed_text or " ")
    if len(ctx) < order:
        ctx = (" " * order + ctx)[-order:]
    out = list(seed_text)
    for _ in range(max(0, n_tokens)):
        bucket = counts.get(ctx)
        if not bucket:
            # backoff: reduce order by 1
            ctx = ctx[1:]
            if not ctx:
                ctx = " " * order
            bucket = counts.get(ctx, None)
            if not bucket:
                break
        ch = _sample_from_counts(bucket)
        out.append(ch)
        ctx = (ctx + ch)[-order:]
    return "".join(out)


# ---- WordNet gloss lookup helpers ----
_GLOSS_CACHE: Dict[Tuple[str, int], Tuple[str, List[str]]] = {}

_DEF_DATA_FILES = {
    "noun": "data.noun",
    "verb": "data.verb",
    "adj": "data.adj",
    "adv": "data.adv",
}


def _pos_to_data_path(pos: str) -> Path | None:
    if not pos:
        return None
    p = str(pos).lower()
    if p.startswith("n"):
        fname = _DEF_DATA_FILES["noun"]
    elif p.startswith("v"):
        fname = _DEF_DATA_FILES["verb"]
    elif p.startswith("a"):
        fname = _DEF_DATA_FILES["adj"]
    elif p.startswith("r"):
        fname = _DEF_DATA_FILES["adv"]
    else:
        return None
    return WORDNET_ROOT / "dict" / fname


def _read_synset(pos: str, offset: int) -> Tuple[str, List[str]] | None:
    key = (pos, int(offset))
    if key in _GLOSS_CACHE:
        return _GLOSS_CACHE[key]
    data_path = _pos_to_data_path(pos)
    if not data_path or not data_path.exists():
        return None
    target = str(int(offset)).rjust(8, "0")
    try:
        with data_path.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if not line or line.startswith(" ") or line.startswith("#"):
                    continue
                if line.startswith(target):
                    # Split gloss
                    parts = line.split(" | ", 1)
                    pre = parts[0]
                    gloss = parts[1].strip() if len(parts) > 1 else ""
                    toks = pre.strip().split()
                    if len(toks) < 4:
                        syns: List[str] = []
                    else:
                        # w_cnt is hex at index 3
                        try:
                            w_cnt = int(toks[3], 16)
                        except Exception:
                            w_cnt = 0
                        syns = []
                        i = 4
                        for _ in range(max(0, w_cnt)):
                            if i >= len(toks):
                                break
                            syns.append(toks[i].lower())
                            i += 2  # skip lex_id
                    _GLOSS_CACHE[key] = (gloss, syns)
                    return _GLOSS_CACHE[key]
    except Exception:
        return None
    return None


def _choose_offset(offsets: List[int]) -> int | None:
    nums = []
    for x in offsets:
        try:
            nums.append(int(x))
        except Exception:
            continue
    if not nums:
        return None
    return sorted(nums)[0]


def generate_answer(text: str) -> Tuple[str, Dict[str, Any]]:
    """
    Return (answer_raw, meta): retrieval-first grounded answer from local WordNet; LM used only as last fallback.
    Deterministic and fully offline.
    """
    lemma = extract_lemma(text) or "unknown"
    rec = _find_record_for_lemma(lemma)
    if rec:
        pos = rec.get("pos")
        offsets = rec.get("offsets", [])
        off = _choose_offset(offsets)
        if off is not None:
            syn = _read_synset(pos, off)
            if syn:
                gloss, syns = syn
                counts = update_counts(lemma)
                syns_display = ", ".join(sorted({s.replace("_", " ") for s in syns if s})) or "(none)"
                answer = (
                    f"{lemma} ({pos}) — Definition: {gloss}. Synonyms: {syns_display}. "
                    f"Provenance: WordNet offset {str(off).rjust(8,'0')} in data.{pos[0] if pos else '?'}"
                )
                meta = {
                    "lemma": lemma,
                    "pos": pos,
                    "offsets": offsets,
                    "chosen_offset": off,
                    "counts": {lemma: counts.get(lemma, 1)},
                    "lm": {"used": False}
                }
                return answer, meta
    # Last fallback: tiny LM continuation without stubby phrasing
    seed_text = f"{lemma} — "
    continuation = _lm_generate(seed_text, n_tokens=48, order=3, seed=1337)
    answer = f"No exact WordNet gloss was found for '{lemma}'. Local continuation: {continuation.strip()}"
    meta = {"lemma": lemma, "pos": rec.get("pos") if rec else None, "offsets": rec.get("offsets", []) if rec else [], "lm": {"used": True, "order": 3, "seed": 1337}}
    return answer, meta
