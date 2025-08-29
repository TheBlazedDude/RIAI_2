from __future__ import annotations
import re
from typing import Dict, Any


def apply_guardrails(text: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Apply simple guardrails: max_tokens (by words), PII masking via regex, and content filtering flags.
    Returns a dict with original, result, actions.
    """
    actions = []
    result = text

    # Max tokens by splitting on whitespace
    max_tokens = int(cfg.get("max_tokens", 256))
    tokens = result.split()
    if len(tokens) > max_tokens:
        result = " ".join(tokens[:max_tokens])
        actions.append({"type": "truncate", "max_tokens": max_tokens})

    # PII regex mask
    for pattern in cfg.get("pii_regex", []) or []:
        try:
            regex = re.compile(pattern)
            if regex.search(result):
                result = regex.sub("[PII]", result)
                actions.append({"type": "pii_mask", "pattern": pattern})
        except re.error:
            # ignore invalid regex
            continue

    # Content filters (just flag if words appear)
    flags = []
    for cat in cfg.get("content_filters", []) or []:
        if re.search(rf"\b{re.escape(cat)}\b", result, re.IGNORECASE):
            flags.append(cat)
    if flags:
        actions.append({"type": "content_flag", "categories": flags})

    return {"original": text, "result": result, "actions": actions}
