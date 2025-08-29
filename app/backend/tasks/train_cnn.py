from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List
import csv
import hashlib
import math
from ..core.utils.io import ARTIFACTS_DIR, write_json, now_iso, ROOT
from ..core.utils.seeds import set_global_seed


def _sha256_path(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def _code_hash() -> str:
    return _sha256_path(Path(__file__))


def _read_close_prices() -> List[float]:
    csv_path = ROOT / 'app' / 'modules' / 'predictor-finance' / 'data' / 'samples' / 'ohlcv.csv'
    prices: List[float] = []
    with csv_path.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                prices.append(float(row['close']))
            except Exception:
                pass
    return prices


def _ma(arr: List[float], window: int = 5) -> List[float]:
    out: List[float] = [arr[0]] * len(arr)
    for i in range(window, len(arr)):
        out[i] = sum(arr[i-window:i]) / window
    return out


def _rmse(y: List[float], yhat: List[float]) -> float:
    n = min(len(y), len(yhat))
    if n == 0:
        return float('inf')
    se = 0.0
    c = 0
    for i in range(1, n):  # skip first (no forecast)
        se += (y[i] - yhat[i]) ** 2
        c += 1
    return math.sqrt(se / max(1, c))


def _mae(y: List[float], yhat: List[float]) -> float:
    n = min(len(y), len(yhat))
    if n == 0:
        return float('inf')
    ae = 0.0
    c = 0
    for i in range(1, n):
        ae += abs(y[i] - yhat[i])
        c += 1
    return ae / max(1, c)


def run(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Train a tiny Conv1D-like forecaster by scaling a moving-average kernel to minimize RMSE (closed-form scale).
    Deterministic; writes ckpt and metrics.
    """
    seed = int(payload.get('seed', 1337))
    set_global_seed(seed)
    window = int(payload.get('window', 5))

    y = _read_close_prices()
    yhat_base = _ma(y, window)

    # Fit scale s to minimize SSE: s = (sum(yhat*y) / sum(yhat^2))
    num = 0.0
    den = 0.0
    for i in range(1, len(y)):
        num += yhat_base[i] * y[i]
        den += yhat_base[i] * yhat_base[i]
    s = (num / den) if den > 0 else 1.0
    yhat_cnn = [v * s for v in yhat_base]

    mae_base = _mae(y, yhat_base)
    rmse_base = _rmse(y, yhat_base)
    mae_tr = _mae(y, yhat_cnn)
    rmse_tr = _rmse(y, yhat_cnn)

    run_dir = ARTIFACTS_DIR / 'predictor' / f'cnn_{seed}'
    run_dir.mkdir(parents=True, exist_ok=True)
    ckpt = run_dir / f'ckpt_cnn_{seed}.json'
    write_json(ckpt, {'seed': seed, 'window': window, 'scale': s})

    metrics = {
        'job': 'train_cnn',
        'seed': seed,
        'window': window,
        'mae_base': mae_base,
        'rmse_base': rmse_base,
        'mae_trained': mae_tr,
        'rmse_trained': rmse_tr,
        'improved': rmse_tr <= rmse_base
    }
    write_json(run_dir / 'metrics.json', metrics)

    # Dataset hash (ohlcv.csv)
    csv_path = ROOT / 'app' / 'modules' / 'predictor-finance' / 'data' / 'samples' / 'ohlcv.csv'
    try:
        dataset_hash = _sha256_path(csv_path)
    except Exception:
        dataset_hash = ''

    run_info = {
        'job': 'train_cnn',
        'seed': seed,
        'created_at': now_iso(),
        'code_hash': _code_hash(),
        'dataset_hash': dataset_hash,
        'artifacts': {'ckpt': str(ckpt), 'metrics': str(run_dir / 'metrics.json')}
    }
    write_json(run_dir / 'run.json', run_info)

    return {'status': 'ok', 'run_dir': str(run_dir), 'metrics': metrics, 'run': run_info}
