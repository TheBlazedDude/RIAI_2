# Modular Offline AI App — Specs & Local Docs (Insel Prinzip)

This repository contains the complete specifications and local documentation to build an offline‑first, modular AI system with three sites:

1. Site 1 — Module Selection
2. Site 2 — Model Selection & Ops
3. Site 3 — AI Workspace (with a Model Lab tab)

The specs implement the Insel Prinzip: each module is an island with a manifest, local assets, and explicit contracts. Offline‑only operation is enforced after entering the AI Workspace.

Contents:
- docs/specs: Contracts and structured specifications (manifests, registry, UX copy, readiness, evaluation, predictor module)
- docs/local_docs: One‑page offline run guide
- docs/local_docs/anleitung_de.md: Deutsche Anleitung – Modell einrichten, Daten importieren, Training starten, Anti‑Echo im Chat
- neural_networks.yaml: Authoritative v1 architecture catalog for NN choices in Model Ops
- WordNet-3.0/: Local WordNet 3.x data for bootstrapped chat flows

Quickstart (Specs)
- Read docs/local_docs/how_to_run_offline.md for the offline run model and readiness checks.
- Use docs/specs/module_manifest_schema.json to author module manifests.
- Use docs/specs/registry_spec.md to format registry entries and artifacts.
- Follow docs/specs/ui_ux_spec.md for page copy and validation rules.

How to add a new module folder (concept)
- Create modules/<your_module>/manifest.json conforming to docs/specs/module_manifest_schema.json.
- Bundle local datasets/test kits and optional synthetic generators (deterministic seeds required).
- Declare ui_panels for AI Workspace/Model Lab and list pipelines for training/eval.

Compatibility enforcement
- A model maps to a module only if capability, task, IO schema, and resources match. See docs/specs/registry_spec.md (compatibility.signature) and ui_ux_spec.md (Site 2 rules).

Export/Import
- Registries and artifacts must be exportable as a tarball with checksums recorded in hashes.json. See registry_spec.md for expected layout.

Troubleshooting
- Readiness Check blocking conditions and remediation steps are listed in docs/specs/readiness_check.md.

License and Scope
- This repo now includes a minimal FastAPI backend implementing module discovery, readiness checks, registry/workspace stubs, runtime/metrics/job/guardrails endpoints, and artifacts directories. Offline guarantees apply after entering Site 3; development can run locally.


## Quickstart (Run end-to-end offline)

Prereqs:
- Python 3.10+ and Node.js 18+ installed locally.
- WordNet-3.0 folder is present at the repository root (already included).

1) Start the backend (PowerShell):
- python -m pip install fastapi uvicorn
- python -m uvicorn app.backend.main:app --reload --port 8000

2) Option A — Bootstrap artifacts (recommended)
- .\tools\bootstrap.ps1 -Seed 1337
  This will:
  - Save a pending workspace with modules: lexicon-wordnet3, chat-core, predictor-finance
  - Train base artifacts (WordNet index; chat retrieval model entry; predictor moving-average baseline)
  - Save module→model mappings
  - Evaluate chat and predictor to produce metrics JSON under app\artifacts\metrics\
  - Confirm Readiness status is ready

3) Start the frontend (separate terminal):
- cd app\frontend
- npm install
- npm run dev
- Open http://localhost:5174

4) Walkthrough (Stepper: Modules → Neural Nets → Models → Workspace → Lab):
- Site 1 (Module Selection): ensure your desired modules are toggled and click Save or Save & Continue.
- Site 1.5 (Neural Nets): create/list Neural Networks (NNs) you plan to use. Save or Save & Continue.
- Site 2 (Model Selection & Ops): map exactly one compatible model per selected module. Click Save or Save & Continue.
- Site 3 (AI Workspace): Readiness gate must be green. Use the Chat panel; runtime is offline-only.
- Model Lab tab: run Train/Evaluate jobs and view metrics (latency p50/p95; MAE/RMSE/MAPE for predictor). Use “Refresh metrics” to re-read local artifacts.

Notes:
- Offline guarantee: After you enter Site 3, the app does not attempt any network calls. All data lives under app\artifacts and app\registry.
- Determinism: Jobs use the provided seed (default 1337). Metrics and datasets incorporate the seed.
- Troubleshooting: Call GET /api/readiness or use the Readiness modal errors with human_message, hint, and logs path.

## Docker Quickstart (Backend + Frontend)

Prereqs:
- Docker Desktop (Windows/macOS) or Docker Engine (Linux).
- This repo includes WordNet-3.0 locally; artifacts/ and registry/ will be persisted via volumes.

Build & run with Docker Compose:

- docker compose build
- docker compose up -d

You should see:
- Backend API at http://localhost:8000/api/health → {"status":"ok","offline":true}
- Frontend at http://localhost:5174 → Site 1 should list modules. All /api requests are proxied to the backend container.

Persisted data:
- Host ./app/artifacts is mounted to container /app/app/artifacts
- Host ./app/registry is mounted to container /app/app/registry

Bootstrap (optional, in a separate shell on host):
- .\tools\bootstrap.ps1 -Seed 1337

Stopping:
- docker compose down

Troubleshooting:
- If frontend shows “failed to load modules”, ensure the backend is healthy: docker logs riai_backend
- If builds are slow, ensure .dockerignore is applied (node_modules and artifacts are excluded from build context).
- If you previously saw a compose warning about the `version` field, it’s been removed; re-run `docker compose build`.
- If nginx logs show "upstream 'backend' may not have port 8000" inside the frontend container, ensure your image includes the fix (proxy_pass http://backend/api/). Run: docker compose build --no-cache && docker compose up -d
- To rebuild after code changes: docker compose build --no-cache && docker compose up -d


## Training Jobs (Offline, Deterministic)

New backend job endpoints are available to run local, offline learning tasks with fixed seeds:
- POST /api/train/sft → tiny char-level SFT; artifacts under app\artifacts\chat\sft_<seed> (ckpt_*, metrics.json, run.json)
- POST /api/train/dpo → toy DPO on synthetic preferences; artifacts under app\artifacts\chat\dpo_<seed>
- POST /api/train/cnn → Conv1D-like scaler on OHLCV; artifacts under app\artifacts\predictor\cnn_<seed>
- POST /api/train/tsconv → Dilated Conv1D-like (two-MA blend); artifacts under app\artifacts\predictor\tsconv_<seed>
- POST /api/train/rl → toy PPO bandit; artifacts under app\artifacts\rl\ppo_<seed>
- Tools: POST /api/tools/make_bubbles (bubble curriculum), POST /api/tools/self_eval (self-reflection scorer)

All jobs are 100% offline, deterministic (seeded), and emit dataset/code hashes in run.json.

Workspace Gating & Anti‑Echo
- /api/runtime/start now blocks unless /api/readiness reports status="ready".
- runtime_post applies guardrails and an anti‑echo safeguard so answers never equal the input verbatim.

CI/Smoke Guidance
- SFT smoke: run with {"seed":1337, "steps":5} and assert metrics.ppl_trained < metrics.ppl_base. See tests/test_sft_smoke.py.


---

Autogenerated base datasets (offline)
- On backend startup, the app now auto-bootstraps essential local assets (deterministic, no network):
  - Builds artifacts\indices\wordnet-lexicon.jsonl if missing.
  - Generates artifacts\datasets\wordnet_synth_1337.jsonl if missing and registers it in registry\datasets.
  - Registers modules\predictor-finance\data\samples\ohlcv.csv as dataset predictor_ohlcv_sample if not already registered.
- This means you can train/evaluate immediately without uploading data. Determinism is guaranteed (seed=1337).
