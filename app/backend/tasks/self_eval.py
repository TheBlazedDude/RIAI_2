from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List
import json
import re
from ..core.utils.io import ARTIFACTS_DIR, now_iso, write_json
from ..core.utils.seeds import set_global_seed


def _score(a: str, b: str) -> float:
    # Simple lexical Jaccard over words
    ta = set(re.findall(r"[A-Za-z]+", (a or "").lower()))
    tb = set(re.findall(r"[A-Za-z]+", (b or "").lower()))
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / max(1, union)


def run(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Self-reflection pass: given pairs of {prompt, response}, compute a score and optionally rewrite.
    Inputs: payload may include {items?: [{prompt, response}], rewrite?: bool, seed?: int}
    Output file: artifacts/chat/self_eval_<seed>.json
    """
    seed = int(payload.get('seed', 1337))
    set_global_seed(seed)
    items: List[Dict[str, str]] = payload.get('items') or []
    # If no items provided, create a tiny synthetic set to keep offline determinism
    if not items:
        items = [
            {"prompt": "define apple", "response": "apple is a fruit"},
            {"prompt": "what is run", "response": "run means to move fast"},
        ]
    results = []
    for it in items:
        p = str(it.get('prompt') or '')
        r = str(it.get('response') or '')
        s = _score(p, r)
        out = {"prompt": p, "response": r, "score": s}
        if bool(payload.get('rewrite')) and s < 0.5:
            out['rewritten'] = f"Answer: {r}"
            out['rewrite_reason'] = 'low lexical grounding'
        results.append(out)
    out_dir = ARTIFACTS_DIR / 'chat'
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f'self_eval_{seed}.json'
    write_json(out_path, {"created_at": now_iso(), "items": results})
    return {"status": "ok", "self_eval": str(out_path), "count": len(results)}
