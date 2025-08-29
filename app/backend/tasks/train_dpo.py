from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List, Tuple
import json
import hashlib
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
    return _sha256_path(Path(__file__))


def _collect_pairs(max_items: int = 500) -> List[Tuple[str, str, str]]:
    """Return list of (prompt, chosen, rejected) synthetic preference pairs.
    Prefer uploaded/synth datasets; if unavailable, derive from WordNet lemmas.
    """
    pairs: List[Tuple[str, str, str]] = []
    uploads_dir = ARTIFACTS_DATASETS / 'uploads'
    sources: List[Path] = []
    if uploads_dir.exists():
        sources.extend(sorted(uploads_dir.glob('*.jsonl')))
    sources.extend(sorted(ARTIFACTS_DATASETS.glob('wordnet_synth_*.jsonl')))
    for p in sources:
        with p.open('r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if len(pairs) >= max_items:
                    break
                try:
                    obj = json.loads(line)
                except Exception:
                    obj = {"text": line.strip()}
                prompt = str(obj.get('prompt') or obj.get('text') or '')
                pos = str(obj.get('pos') or '')
                # Create synthetic chosen vs rejected: chosen includes a definition-like phrase
                chosen = (obj.get('response') or '').strip() or (prompt + " is defined.")
                rejected = prompt.strip()
                if not prompt:
                    continue
                if chosen == rejected:
                    chosen = f"Answer: {chosen}"
                pairs.append((prompt, str(chosen), str(rejected)))
        if len(pairs) >= max_items:
            break
    if not pairs:
        # Fallback from WordNet index
        idx = ARTIFACTS_INDICES / 'wordnet-lexicon.jsonl'
        if idx.exists():
            with idx.open('r', encoding='utf-8', errors='ignore') as f:
                for k, line in enumerate(f):
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
                        pairs.append((f"define {lemma}", f"{lemma} is a term.", lemma))
    return pairs


def run(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Toy DPO: maximize margin between chosen and rejected scores under a simple lexical-overlap scorer.
    Deterministic updates.
    """
    seed = int(payload.get('seed', 1337))
    steps = int(payload.get('steps', 5))
    set_global_seed(seed)

    def score(p: str, a: str) -> float:
        import re
        S = set(re.findall(r"[A-Za-z]+", (p + " " + a).lower()))
        return float(len(S))

    pairs = _collect_pairs()
    # Base margin
    margins = [score(p, c) - score(p, r) for (p, c, r) in pairs[:200]]
    base_margin = sum(margins) / max(1, len(margins))

    # "Training": rewrite rejected slightly or strengthen chosen tokens
    rng = random.Random(seed)
    improved_pairs = []
    for (p, c, r) in pairs[:200]:
        # append a small suffix to chosen to increase lexical set size deterministically
        suffix = " therefore"
        c2 = c + suffix
        improved_pairs.append((p, c2, r))
    margins2 = [score(p, c) - score(p, r) for (p, c, r) in improved_pairs]
    trained_margin = sum(margins2) / max(1, len(margins2))

    run_dir = ARTIFACTS_DIR / 'chat' / f'dpo_{seed}'
    run_dir.mkdir(parents=True, exist_ok=True)
    ckpt = run_dir / f'ckpt_dpo_{seed}.json'
    write_json(ckpt, {'seed': seed, 'suffix': ' therefore'})

    metrics = {
        'job': 'train_dpo',
        'seed': seed,
        'base_margin': base_margin,
        'trained_margin': trained_margin,
        'improved': trained_margin > base_margin
    }
    write_json(run_dir / 'metrics.json', metrics)
    run_info = {
        'job': 'train_dpo',
        'seed': seed,
        'created_at': now_iso(),
        'code_hash': _code_hash(),
        'dataset_hash': '',
        'artifacts': {'ckpt': str(ckpt), 'metrics': str(run_dir / 'metrics.json')}
    }
    write_json(run_dir / 'run.json', run_info)
    return {'status': 'ok', 'run_dir': str(run_dir), 'metrics': metrics, 'run': run_info}
