from __future__ import annotations
import os
import random

def set_global_seed(seed: int | None) -> int:
    """Set global seeds for determinism and return the used seed.
    If seed is None, derive from RIAI_SEED env or default 1337.
    """
    if seed is None:
        seed = int(os.environ.get("RIAI_SEED", "1337"))
    random.seed(seed)
    try:
        import numpy as np  # optional
        np.random.seed(seed)
    except Exception:
        pass
    return seed
