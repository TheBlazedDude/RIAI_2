# How to Run This AI Offline (One-Page Guide)

Version: 1

Goal: Run the modular AI Workspace entirely offline with deterministic behavior. This guide covers first‑run setup, the three sites flow, readiness checks, guardrails, and export/import.

Prerequisites
- Local data present:
  - WordNet-3.0\ (this repo includes it)
  - neural_networks.yaml at repo root (architecture catalog)
- No internet required after entering Site 3 (Workspace). Prefer disabling network to ensure compliance.

First Run (WordNet Bootstrap for Chat)
1) Build Lexicon Index
- Input: WordNet-3.0 data
- Output: artifacts\indices\wordnet-lexicon.jsonl (deterministic)
- Seed: 1337 (record seed in any metrics or logs)

2) Generate Synthetic Dialogs (optional for tiny LM)
- Input: WordNet glosses and relations
- Output: artifacts\datasets\wordnet_synth_1337.jsonl and modules\chat-core\data\wordnet_synth_1337.jsonl
- Seed: 1337

3) Evaluate Retrieval
- Produce initial metrics file: artifacts\metrics\chat\<model_id>.json with latency_ms.{p50,p95} and grounding_score.

Three Sites Flow
- Site 1 — Module Selection
  - The app auto-discovers modules under modules\*\manifest.json. Select the modules to include.
- Site 2 — Model Selection & Ops
  - For each selected module, choose exactly one compatible model using one of three paths:
    1) Create New Neural Network → Create Model
    2) Create New Model from Existing NN
    3) Choose Existing Model
  - Proceed only when all modules show status Ready.
- Site 3 — AI Workspace (Offline)
  - Chat is available if a chat model is selected. Other panels appear based on modules’ ui_panels.
  - Model Lab tab provides charts (learning curves, latency p50/p95, PR/ROC, forecasts) and promotion timeline.

Readiness Check (Blocking)
All items below must pass before entering Site 3:
- Modules discovered and manifests valid (docs\specs\module_manifest_schema.json)
- Exactly one compatible model per selected module (capability/task/IO/resources)
- Registry entries exist for models, NNs, datasets (registry\*)
- Dataset/artifact checksums match hashes.json
- WordNet index and synthetic dataset available for chat
- Guardrails configured (max_tokens, PII regex, allowed_file_types)
- Required permissions acknowledged (camera/microphone/filesystem)
- Resources within limits; artifacts folders writable; no network access

Guardrails (Applied at Runtime)
- Max tokens: limits response length
- PII filter: redact/deny outputs matching configured regexes
- Blocked categories: prevent disallowed content
- Allowed file types: restrict file ingestion per module
- All guardrail decisions are recorded under artifacts\traces\*.jsonl

Export / Import (Offline Portability)
- Export: create a tarball containing registry\*, artifacts\*, hashes.json, VERSION.
- Import: unpack to a new machine and verify hashes.json; if mismatch, fix by re‑generating synthetic data with the same seeds or re‑evaluating models.

Troubleshooting (Common Blocking Messages)
- manifest_invalid: Fix the module manifest fields per module_manifest_schema.json.
- mapping_incomplete: Use Site 2 to map one compatible model per module.
- dataset_checksum_mismatch: Re‑generate dataset with the same seed or re‑import.
- wordnet_index_missing: Run the first‑run index build step.
- guardrails_invalid: Adjust Guardrails panel values.
- resources_insufficient: Choose a lighter model or disable modules.
- filesystem_readonly: Ensure artifacts\metrics and artifacts\traces are writable.

Determinism Notes
- Always pass --seed when generating data or training/evaluating. The same seed and artifacts must reproduce identical results (within numerical tolerance) and stable checksums.
