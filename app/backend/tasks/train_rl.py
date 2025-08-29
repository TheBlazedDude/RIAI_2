from __future__ import annotations
from typing import Dict, Any
from pathlib import Path
import hashlib
from ..core.utils.io import ARTIFACTS_DIR, write_json, now_iso
from ..core.utils.seeds import set_global_seed


def _sha256_path(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def _code_hash() -> str:
    return _sha256_path(Path(__file__))


def run(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Toy PPO on a deterministic 2-armed bandit with stationary rewards.
    We compute a simple policy parameter that increases probability of the better arm.
    """
    seed = int(payload.get('seed', 1337))
    set_global_seed(seed)

    # Bandit arms: arm0 ~ N(0.0, 1), arm1 ~ N(0.5, 1) but deterministic pseudo rewards
    # Deterministic pseudo-rewards via hash of (seed, t, arm)
    def reward(t: int, arm: int) -> float:
        v = (seed * 1315423911 + t * 2654435761 + arm * 97531) & 0xFFFFFFFF
        # map to [0,1)
        r = (v % 10000) / 10000.0
        # shift arm1 higher
        return r + (0.5 if arm == 1 else 0.0)

    # Policy parameter p selects arm1 with probability sigmoid(theta)
    import math
    theta = 0.0
    def sigmoid(x: float) -> float:
        return 1.0 / (1.0 + math.exp(-x))

    T = int(payload.get('steps', 200))
    lr = float(payload.get('lr', 0.1))
    baseline = 0.0
    avg_rewards = []
    for t in range(T):
        p1 = sigmoid(theta)
        # choose action deterministically by thresholding p1 with a fixed schedule
        a = 1 if (t % 100) < int(p1 * 100) else 0
        r = reward(t, a)
        # advantage estimate (r - baseline)
        adv = r - baseline
        # simple policy gradient ascent on theta for chosen action
        grad = (1 - p1) if a == 1 else (-p1)
        theta += lr * adv * grad
        # update baseline
        baseline = 0.9 * baseline + 0.1 * r
        avg_rewards.append(r)
    avg_reward = sum(avg_rewards[-50:]) / max(1, min(50, len(avg_rewards)))

    run_dir = ARTIFACTS_DIR / 'rl' / f'ppo_{seed}'
    run_dir.mkdir(parents=True, exist_ok=True)
    ckpt = run_dir / f'ckpt_ppo_{seed}.json'
    write_json(ckpt, {'seed': seed, 'theta': theta})

    metrics = {
        'job': 'train_rl',
        'seed': seed,
        'avg_reward_last50': avg_reward,
        'theta': theta,
        'improved': theta > 0.0
    }
    write_json(run_dir / 'metrics.json', metrics)

    run_info = {
        'job': 'train_rl',
        'seed': seed,
        'created_at': now_iso(),
        'code_hash': _code_hash(),
        'dataset_hash': '',
        'artifacts': {'ckpt': str(ckpt), 'metrics': str(run_dir / 'metrics.json')}
    }
    write_json(run_dir / 'run.json', run_info)

    return {'status': 'ok', 'run_dir': str(run_dir), 'metrics': metrics, 'run': run_info}
