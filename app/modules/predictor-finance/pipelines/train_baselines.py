import argparse
import json
from pathlib import Path
from datetime import datetime
import random

# Deterministic stub trainer for predictor-finance
# Writes a minimal metrics-like artifact to app/artifacts/metrics/predictor/<model_id>.json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--model_id', type=str, default='model_pred_stub_0001')
    parser.add_argument('--horizon', type=int, default=8)
    args = parser.parse_args()

    random.seed(args.seed)

    current = Path(__file__).resolve()
    ROOT = current.parents[4]
    out_dir = ROOT / 'app' / 'artifacts' / 'metrics' / 'predictor'
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f'{args.model_id}.json'

    # Produce deterministic pseudo-metrics
    mae = round(0.9 + (args.seed % 10) * 0.001, 3)
    rmse = round(1.2 + (args.seed % 7) * 0.001, 3)
    mape = round(0.03 + (args.seed % 5) * 0.0001, 4)

    report = {
        'model_id': args.model_id,
        'capability': 'predictor',
        'seed': args.seed,
        'latency_ms': {'p50': 8.1, 'p95': 22.9},
        'mae': mae,
        'rmse': rmse,
        'mape': mape,
        'horizon': args.horizon,
        'env': {'cpu': 'x86_64', 'gpu': 'none'},
        'timestamp': datetime.now().astimezone().isoformat()
    }

    with out_path.open('w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(json.dumps({'ok': True, 'report': str(out_path)}))


if __name__ == '__main__':
    main()
