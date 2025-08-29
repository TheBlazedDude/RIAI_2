from __future__ import annotations
import json
from pathlib import Path

from app.backend.main import train_sft_job, runtime_post
from app.backend.core.utils.io import ARTIFACTS_DIR

def test_sft_smoke_and_no_echo():
    seed = 1337
    # Run SFT tiny training
    resp = train_sft_job({'seed': seed, 'steps': 5, 'order': 3})
    assert resp.get('ok') is True
    job = resp.get('job') or {}
    result = job.get('result') or {}
    metrics = result.get('metrics') or {}
    assert 'ppl_base' in metrics and 'ppl_trained' in metrics
    assert float(metrics['ppl_trained']) < float(metrics['ppl_base'])

    # Metrics file exists on disk
    run_dir = Path(result.get('run_dir') or (ARTIFACTS_DIR / 'chat' / f'sft_{seed}'))
    mpath = run_dir / 'metrics.json'
    assert mpath.exists()

    # Anti-echo: ensure runtime answer is not exactly the input
    text = 'apple'
    r = runtime_post({'text': text})
    ans = (((r or {}).get('answer') or {}).get('guarded') or {}).get('result')
    assert isinstance(ans, str) and ans.strip().lower() != text.strip().lower()
