from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List, Tuple
import json
import hashlib
import math
import random
from ..core.utils.io import ARTIFACTS_DIR, ARTIFACTS_DATASETS, ARTIFACTS_INDICES, write_json, now_iso
from ..core.utils.seeds import set_global_seed


def _sha256_path(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def _code_hash() -> str:
    p = Path(__file__)
    return _sha256_path(p)


def _collect_corpus(max_items: int = 2000) -> Tuple[str, List[Path]]:
    corpus = ""
    sources: List[Path] = []
    # Prefer uploaded/synth chat datasets
    uploads_dir = ARTIFACTS_DATASETS / 'uploads'
    if uploads_dir.exists():
        for f in sorted(uploads_dir.glob('*.jsonl')):
            sources.append(f)
    for f in sorted(ARTIFACTS_DATASETS.glob('wordnet_synth_*.jsonl')):
        sources.append(f)
    count = 0
    for p in sources:
        try:
            with p.open('r', encoding='utf-8') as fp:
                for line in fp:
                    if count >= max_items:
                        break
                    try:
                        obj = json.loads(line)
                    except Exception:
                        obj = {"text": line.strip()}
                    txt = str(obj.get('response') or obj.get('text') or obj.get('prompt') or '')
                    if not txt:
                        continue
                    corpus += txt + "\n"
                    count += 1
        except Exception:
            continue
        if count >= max_items:
            break
    if not corpus:
        # Fallback: lemmas from WordNet index
        idx = ARTIFACTS_INDICES / 'wordnet-lexicon.jsonl'
        if idx.exists():
            k = 0
            with idx.open('r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if k >= max_items:
                        break
                    try:
                        obj = json.loads(line)
                    except Exception:
                        try:
                            obj = eval(line)
                        except Exception:
                            obj = {}
                    lemma = str(obj.get('lemma') or '')
                    if lemma:
                        corpus += lemma + ' '
                        k += 1
    return corpus, sources


def _build_ngram_counts(text: str, order: int = 3) -> Dict[str, Dict[str, int]]:
    counts: Dict[str, Dict[str, int]] = {}
    n = len(text)
    if n <= order:
        return counts
    for i in range(n - order):
        ctx = text[i:i+order]
        nx = text[i+order]
        c = counts.setdefault(ctx, {})
        c[nx] = c.get(nx, 0) + 1
    return counts


def _ppl(text: str, counts: Dict[str, Dict[str, int]], order: int = 3, alpha: float = 0.0) -> float:
    # Perplexity with optional add-alpha smoothing
    if len(text) <= order:
        return float('inf')
    V = 128  # byte-ish vocab proxy
    N = 0
    logprob = 0.0
    for i in range(len(text) - order):
        ctx = text[i:i+order]
        nx = text[i+order]
        bucket = counts.get(ctx, {})
        total = sum(bucket.values()) + alpha * V
        p = (bucket.get(nx, 0) + alpha) / total if total > 0 else 1.0 / V
        logprob += -math.log(max(p, 1e-12))
        N += 1
    return math.exp(logprob / max(1, N))


def run(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Supervised fine-tuning (SFT) for a tiny char-level LM using local datasets only.
    Deterministic with seeds. Produces ckpt, metrics.json (ppl_base vs ppl_trained), and run.json with hashes.
    """
    seed = int(payload.get('seed', 1337))
    order = int(payload.get('order', 3))
    steps = int(payload.get('steps', 5))  # tiny smoke run
    set_global_seed(seed)

    corpus, sources = _collect_corpus()
    # Split deterministically
    split = int(0.9 * len(corpus))
    train_txt = corpus[:split]
    val_txt = corpus[split:] or corpus[: max(1, len(corpus)//10)]

    base_counts = _build_ngram_counts(train_txt, order=order)
    ppl_base = _ppl(val_txt, base_counts, order=order, alpha=0.1)

    # "Training": reinforce observed transitions by a small factor over multiple passes
    counts = {k: v.copy() for k, v in base_counts.items()}
    for s in range(steps):
        # Sample positions deterministically based on seed
        rng = random.Random(seed + s)
        n = len(train_txt)
        if n <= order:
            break
        idxs = list(range(0, n - order, max(1, (n - order)//50 or 1)))
        rng.shuffle(idxs)
        for i in idxs[:200]:
            ctx = train_txt[i:i+order]
            nx = train_txt[i+order]
            bucket = counts.setdefault(ctx, {})
            bucket[nx] = bucket.get(nx, 0) + 1  # simple positive update
    ppl_trained = _ppl(val_txt, counts, order=order, alpha=0.1)

    run_dir = ARTIFACTS_DIR / 'chat' / f'sft_{seed}'
    run_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = run_dir / f'ckpt_sft_{seed}.json'
    write_json(ckpt_path, {"order": order, "counts": {k: v for k, v in list(counts.items())[:20000]}, "seed": seed})

    # Metrics and run info
    metrics = {
        'job': 'train_sft',
        'seed': seed,
        'order': order,
        'ppl_base': ppl_base,
        'ppl_trained': ppl_trained,
        'improved': float(ppl_trained) < float(ppl_base)
    }
    write_json(run_dir / 'metrics.json', metrics)

    data_hash = hashlib.sha256()
    for p in sources:
        try:
            with p.open('rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    data_hash.update(chunk)
        except Exception:
            continue

    run_info = {
        'job': 'train_sft',
        'seed': seed,
        'created_at': now_iso(),
        'code_hash': _code_hash(),
        'dataset_hash': data_hash.hexdigest(),
        'artifacts': {'ckpt': str(ckpt_path), 'metrics': str(run_dir / 'metrics.json')}
    }
    write_json(run_dir / 'run.json', run_info)

    return {
        'status': 'ok',
        'run_dir': str(run_dir),
        'ckpt': str(ckpt_path),
        'metrics': metrics,
        'run': run_info
    }
