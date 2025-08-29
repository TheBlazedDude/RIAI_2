# Registry Spec (File-based, Offline, Deterministic)

Version: 1

Purpose: Define on-disk structures for neural_nets, models, datasets, workspaces, artifacts, hashes.json, and VERSION. Include promotion history, compatibility signatures, and metrics JSON formats. All artifacts are deterministic with fixed seeds and checksums.

General conventions
- Encoding: UTF-8, JSON/JSONL for data and metrics; YAML permitted for configs.
- Paths: Windows-style backslashes (\\). Rooted at repository root.
- Checksums: SHA256 of files referenced; record in entries where relevant.
- Time: ISO-8601 local time with timezone offset.
- Seeds: integer seed recorded in every generated artifact and evaluation report.

Directory layout (logical)
- registry\\neural_nets\\<nn_id>.json
- registry\\models\\<model_id>.json
- registry\\datasets\\<dataset_id>.json
- registry\\workspaces\\<workspace_id>.json
- artifacts\\metrics\\<capability>\\<model_id>.json
- artifacts\\datasets\\*.jsonl
- artifacts\\indices\\*.jsonl
- artifacts\\traces\\*.jsonl
- hashes.json
- VERSION

1) Registry Entry: neural_nets
Fields
- id (string, unique)
- name (string)
- architecture_id (string) – must match id from neural_networks.yaml
- config (object) – hyperparameters/topology summary
- seed (integer)
- created_at (string, ISO-8601)
- checksum (string, SHA256 of canonicalized JSON of this entry)
- notes (string)
- hardware_profile (object): {cpu, gpu, ram_mb, vram_mb}

Example
{
  "id": "nn_lexicon_rnn_0001",
  "name": "Lexicon Tiny RNN",
  "architecture_id": "rnn",
  "config": {"hidden_size": 64, "layers": 1, "dropout": 0.0},
  "seed": 1337,
  "created_at": "2025-08-28T16:25:00+02:00",
  "checksum": "SHA256:7b0b...",
  "notes": "Toy RNN for chat-core tiny LM",
  "hardware_profile": {"cpu": "x86_64", "gpu": "none", "ram_mb": 512, "vram_mb": 0}
}

2) Registry Entry: models
Fields
- id (string, unique)
- name (string)
- version (string semver)
- nn_id (string) – reference to neural_nets.id
- capability (string: chat|vision|speech|predictor)
- task (string; e.g., dialogue, asr, detector, forecast)
- io_schema (object): {inputs: [types], outputs: [types]}
- dataset_ids (array of string)
- hyperparameters (object)
- resources (object): {cpu_hint, gpu_required, vram_mb, ram_mb}
- metrics (object): last known eval metrics summary
- promotion_history (array): chronological entries
  - {version, tag: candidate|staging|production, at, seed, metrics_delta}
- compatibility (object)
  - signature (string) – hash of capability+task+io_schema+resources family
  - module_requirements (object) – copy of matched module model_constraints
- artifacts (object)
  - checkpoints (array of {path, checksum})
  - reports (array of {path, checksum})
- created_at (string)
- checksum (string) – SHA256 of canonicalized JSON of this entry

Example (chat-core retrieval-only)
{
  "id": "model_chatcore_retrieval_0001",
  "name": "ChatCore Retrieval Index",
  "version": "0.1.0",
  "nn_id": "nn_index_none",
  "capability": "chat",
  "task": "dialogue",
  "io_schema": {"inputs": ["text"], "outputs": ["text"]},
  "dataset_ids": ["ds_wordnet_synth_1337"],
  "hyperparameters": {"top_k": 5},
  "resources": {"cpu_hint": "low", "gpu_required": false, "vram_mb": 0, "ram_mb": 256},
  "metrics": {"latency_p50_ms": 12.3, "latency_p95_ms": 35.6, "grounding_score": 0.71, "seed": 1337},
  "promotion_history": [
    {"version": "0.1.0", "tag": "candidate", "at": "2025-08-28T16:30:00+02:00", "seed": 1337, "metrics_delta": {}}
  ],
  "compatibility": {
    "signature": "sig:chat|dialogue|text->text|low",
    "module_requirements": {"model_type": "index", "io_schema": {"inputs": ["text"], "outputs": ["text"]}}
  },
  "artifacts": {
    "checkpoints": [],
    "reports": [{"path": "artifacts\\metrics\\chat\\model_chatcore_retrieval_0001.json", "checksum": "SHA256:ab12..."}]
  },
  "created_at": "2025-08-28T16:26:00+02:00",
  "checksum": "SHA256:9c1d..."
}

Promotion & Rollback
- Promote: append entry with tag change; update current alias in workspace mapping if tag becomes production.
- Rollback: record a new entry that sets tag back to a previous version and update workspace alias.

3) Registry Entry: datasets
Fields
- id (string, unique)
- name (string)
- origin (string: local|synthetic)
- schema (object): description of columns/fields; for timeseries include frequency
- splits (object): {train: percent/count, dev: percent/count, test: percent/count}
- license (string)
- seed (integer)
- files (array of {path, checksum})
- created_at (string)
- checksum (string) – SHA256 of canonicalized JSON of this entry

Example (Predictor OHLCV synthetic)
{
  "id": "ds_finance_synth_2025_42",
  "name": "Finance OHLCV Synthetic v2025.08.28",
  "origin": "synthetic",
  "schema": {"columns": ["timestamp","open","high","low","close","volume"], "freq": "1d"},
  "splits": {"train": 0.7, "dev": 0.15, "test": 0.15},
  "license": "local-use",
  "seed": 42,
  "files": [{"path": "artifacts\\datasets\\ohlcv_synth_42.jsonl", "checksum": "SHA256:1a2b..."}],
  "created_at": "2025-08-28T16:28:00+02:00",
  "checksum": "SHA256:7e8f..."
}

4) Registry Entry: workspaces
Fields
- id (string, unique)
- name (string)
- selected_modules (array of module ids)
- mapping (object): capability -> model_id
- guardrails (object): policy snapshot used at runtime
- panels_enabled (object): module_id -> [panel names]
- created_at (string) / updated_at (string)
- checksum (string)

Example
{
  "id": "ws_default_0001",
  "name": "Default Workspace",
  "selected_modules": ["lexicon-wordnet3", "chat-core", "predictor-finance"],
  "mapping": {"chat": "model_chatcore_retrieval_0001", "predictor": "model_pred_mlp_0007"},
  "guardrails": {"max_tokens": 256, "pii_regex": ["SSN"], "blocked_categories": ["nsfw"], "allowed_file_types": [".json", ".csv"]},
  "panels_enabled": {"chat-core": ["chat_panel"], "predictor-finance": ["predictions_dashboard"]},
  "created_at": "2025-08-28T16:29:00+02:00",
  "updated_at": "2025-08-28T16:31:00+02:00",
  "checksum": "SHA256:abcd..."
}

5) Artifacts & Metrics JSON formats
5.1 Chat-Core metrics (artifacts\\metrics\\chat\\<model_id>.json)
{
  "model_id": "model_chatcore_retrieval_0001",
  "capability": "chat",
  "seed": 1337,
  "latency_ms": {"p50": 12.3, "p95": 35.6},
  "grounding_score": 0.71,
  "perplexity": null,
  "env": {"cpu": "x86_64", "gpu": "none"},
  "timestamp": "2025-08-28T16:30:00+02:00",
  "checksums": {"report": "SHA256:ab12..."}
}

5.2 Predictor metrics (artifacts\\metrics\\predictor\\<model_id>.json)
{
  "model_id": "model_pred_mlp_0007",
  "capability": "predictor",
  "seed": 42,
  "latency_ms": {"p50": 8.1, "p95": 22.9},
  "mae": 0.92,
  "rmse": 1.24,
  "mape": 0.031,
  "timestamp": "2025-08-28T16:40:00+02:00",
  "checksums": {"report": "SHA256:de34..."}
}

6) hashes.json and VERSION
- hashes.json: map of key -> SHA256 checksum to anchor reproducibility.
Example
{
  "registry/neural_nets/nn_lexicon_rnn_0001.json": "SHA256:7b0b...",
  "registry/models/model_chatcore_retrieval_0001.json": "SHA256:9c1d...",
  "artifacts/metrics/chat/model_chatcore_retrieval_0001.json": "SHA256:ab12..."
}
- VERSION: single line application version (e.g., 0.1.0-alpha1)

7) Compatibility Matching Logic (recording)
- Eligible if: model.capability ∈ module.capabilities AND model.task == module.task AND model.io_schema ⊇ module.inputs/outputs AND resources fit.
- Record compatibility.signature as a stable string (e.g., sig:<cap>|<task>|<in>-><out>|<resource_class>), SHA256 optional.

8) Export/Import
- Export: tarball with registry/* and artifacts/* plus hashes.json and VERSION.
- Import: verify all checksums in hashes.json; refuse import if any mismatch; produce a remediation report.
