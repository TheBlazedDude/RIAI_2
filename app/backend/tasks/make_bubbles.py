from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List
import json
import hashlib
from ..core.utils.io import ARTIFACTS_DATASETS, ARTIFACTS_DIR, now_iso, write_json
from ..core.utils.seeds import set_global_seed


def _hash_text(s: str) -> str:
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


def run(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a simple Bubble-Curriculum by bucketing chat examples by prompt length.
    Inputs: payload may include {dataset_id?: str, seed?: int, buckets?: List[int]}
    Outputs: writes artifacts/datasets/bubbles_<dataset_id>_<seed>.json with buckets metadata.
    Deterministic across the same dataset + seed.
    """
    seed = int(payload.get('seed', 1337))
    set_global_seed(seed)
    ds_id = str(payload.get('dataset_id', 'wordnet_synth'))
    # Source candidates
    uploads = sorted((ARTIFACTS_DATASETS / 'uploads').glob('*.jsonl'))
    synths = sorted(ARTIFACTS_DATASETS.glob('wordnet_synth_*.jsonl'))
    sources = [p for p in uploads if p.stem == ds_id] or synths or uploads
    if not sources:
        # Nothing to bucket; create empty structure
        sources = []
    # Read up to N items deterministically
    items: List[Dict[str, Any]] = []
    for p in sources[:1]:
        with p.open('r', encoding='utf-8') as f:
            for k, line in enumerate(f):
                if k >= 1000:
                    break
                try:
                    obj = json.loads(line)
                except Exception:
                    obj = {"text": line.strip()}
                prompt = str(obj.get('prompt') or obj.get('text') or obj.get('question') or '')
                response = str(obj.get('response') or obj.get('answer') or '')
                items.append({"prompt": prompt, "response": response})
    # Bucketing by prompt length
    cuts = payload.get('buckets') or [16, 32, 64, 128, 256]
    bubbles: Dict[str, List[int]] = {f"<= {c}": [] for c in cuts}
    bubbles["> 256"] = []
    for i, ex in enumerate(items):
        L = len(ex.get('prompt', ''))
        placed = False
        for c in cuts:
            if L <= c:
                bubbles[f"<= {c}"].append(i)
                placed = True
                break
        if not placed:
            bubbles["> 256"].append(i)
    # Persist
    out_dir = ARTIFACTS_DIR / 'bubble'
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"bubbles_{ds_id}_{seed}.json"
    write_json(out_path, {
        'dataset_id': ds_id,
        'seed': seed,
        'built_at': now_iso(),
        'buckets': bubbles,
        'count': len(items),
        'source_count': len(sources)
    })
    return {
        'status': 'ok',
        'bubbles': str(out_path)
    }
