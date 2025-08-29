import argparse
import json
from pathlib import Path
from datetime import datetime

# Offline retrieval stub: reads synthetic dialogs if present and returns a canned response

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--query', type=str, default='Define bank')
    parser.add_argument('--seed', type=int, default=1337)
    args = parser.parse_args()

    current = Path(__file__).resolve()
    ROOT = current.parents[4]
    synth = ROOT / 'app' / 'modules' / 'chat-core' / 'data' / f'wordnet_synth_{args.seed}.jsonl'

    provenance = []
    if synth.exists():
        provenance.append(str(synth))
    answer = "A financial institution that accepts deposits. [synset:bank%1:14:00::]"

    print(json.dumps({
        'ok': True,
        'query': args.query,
        'answer': answer,
        'provenance': provenance,
        'timestamp': datetime.now().astimezone().isoformat()
    }))

if __name__ == '__main__':
    main()
