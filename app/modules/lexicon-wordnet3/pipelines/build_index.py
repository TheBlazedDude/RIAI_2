import argparse
import json
import os
from pathlib import Path
import hashlib
from datetime import datetime

# Deterministic, offline index builder stub for WordNet
# Writes artifacts\indices\wordnet-lexicon.jsonl with a single line summary for now


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return 'SHA256:' + h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=1337)
    args = parser.parse_args()

    # Resolve repo root
    current = Path(__file__).resolve()
    ROOT = current.parents[4]
    artifacts_dir = ROOT / 'app' / 'artifacts' / 'indices'
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    out_path = artifacts_dir / 'wordnet-lexicon.jsonl'

    # Minimal deterministic content
    record = {
        'seed': args.seed,
        'built_at': datetime.now().astimezone().isoformat(),
        'source': str((ROOT / 'WordNet-3.0').resolve()),
        'notes': 'Deterministic stub index. Replace with real indexer later.',
    }

    with out_path.open('w', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')

    print(json.dumps({
        'ok': True,
        'output': str(out_path),
        'checksum': sha256_of_file(out_path),
    }))


if __name__ == '__main__':
    main()
