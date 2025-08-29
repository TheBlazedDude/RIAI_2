import argparse
import json
from pathlib import Path
from datetime import datetime
import hashlib

# Deterministic synthetic dialogs stub based on WordNet glosses concept
# Writes artifacts\datasets\wordnet_synth_{seed}.jsonl and modules\chat-core\data\wordnet_synth_{seed}.jsonl


def ensure_dir(p: Path):
  p.mkdir(parents=True, exist_ok=True)


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

  current = Path(__file__).resolve()
  ROOT = current.parents[4]
  artifacts_ds = ROOT / 'app' / 'artifacts' / 'datasets'
  chat_data = ROOT / 'app' / 'modules' / 'chat-core' / 'data'
  ensure_dir(artifacts_ds)
  ensure_dir(chat_data)

  out_name = f'wordnet_synth_{args.seed}.jsonl'
  out1 = artifacts_ds / out_name
  out2 = chat_data / out_name

  # Tiny deterministic examples
  examples = [
    {"q": "Define bank.", "a": "A financial institution that accepts deposits. [synset:bank%1:14:00::]", "seed": args.seed},
    {"q": "What is a canine?", "a": "Relating to or resembling a dog. [synset:canine%3:01:00::]", "seed": args.seed}
  ]

  def write_jsonl(path: Path):
    with path.open('w', encoding='utf-8') as f:
      for ex in examples:
        f.write(json.dumps(ex, ensure_ascii=False) + '\n')

  write_jsonl(out1)
  write_jsonl(out2)

  print(json.dumps({
    'ok': True,
    'outputs': [str(out1), str(out2)],
    'checksums': [sha256_of_file(out1), sha256_of_file(out2)],
    'timestamp': datetime.now().astimezone().isoformat()
  }))


if __name__ == '__main__':
  main()
