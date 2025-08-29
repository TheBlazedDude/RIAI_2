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


def _ma(arr: List[float], window: int) -> List[float]:
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
    for i in range(1, n):
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
    Train a tiny dilated-Conv1D-like forecaster by combining two moving averages (short and long) with optimal weights.
    Deterministic; writes ckpt and metrics.
    """
    seed = int(payload.get('seed', 1337))
    set_global_seed(seed)
    w_short = int(payload.get('w_short', 3))
    w_long = int(payload.get('w_long', 12))

    y = _read_close_prices()
    ma_s = _ma(y, w_short)
    ma_l = _ma(y, w_long)

    # Fit weights a,b to minimize SSE of a*ma_s + b*ma_l to y (linear regression closed form for 2 vars)
    ss = sl = ll = sy = ly = 0.0
    for i in range(1, len(y)):
        s = ma_s[i]
        l = ma_l[i]
        ss += s * s
        ll += l * l
        sl += s * l
        sy += s * y[i]
        ly += l * y[i]
    # Solve [ss sl; sl ll] [a b]^T = [sy ly]^T
    det = ss * ll - sl * sl
    if det != 0:
        a = (sy * ll - sl * ly) / det
        b = (ss * ly - sl * sy) / det
    else:
        a = 0.5
        b = 0.5
    yhat = [a * ma_s[i] + b * ma_l[i] for i in range(len(y))]

    mae_base = _mae(y, ma_l)  # baseline: long MA
    rmse_base = _rmse(y, ma_l)
    mae_tr = _mae(y, yhat)
    rmse_tr = _rmse(y, yhat)

    run_dir = ARTIFACTS_DIR / 'predictor' / f'tsconv_{seed}'
    run_dir.mkdir(parents=True, exist_ok=True)
    ckpt = run_dir / f'ckpt_tsconv_{seed}.json'
    write_json(ckpt, {'seed': seed, 'w_short': w_short, 'w_long': w_long, 'a': a, 'b': b})

    metrics = {
        'job': 'train_tsconv',
        'seed': seed,
        'w_short': w_short,
        'w_long': w_long,
        'mae_base': mae_base,
        'rmse_base': rmse_base,
        'mae_trained': mae_tr,
        'rmse_trained': rmse_tr,
        'improved': rmse_tr <= rmse_base
    }
    write_json(run_dir / 'metrics.json', metrics)

    run_info = {
        'job': 'train_tsconv',
        'seed': seed,
        'created_at': now_iso(),
        'code_hash': _code_hash(),
        'dataset_hash': '',
        'artifacts': {'ckpt': str(ckpt), 'metrics': str(run_dir / 'metrics.json')}
    }
    write_json(run_dir / 'run.json', run_info)

    return {'status': 'ok', 'run_dir': str(run_dir), 'metrics': metrics, 'run': run_info}
