# Implementation Plan — Modular Offline AI App (Insel Prinzip)

Version: 2 (refreshed after initial scaffolding)
Owner: Junie
Scope: Complete the offline-first modular AI system per <issue_description>, building on the scaffolding already added to the repo.

Guiding Constraints
- Insel Prinzip: each module is a self-contained folder with manifest, pipelines, data, and UI panel descriptors. ✓
- Offline-only after entering Site 3; readiness gate blocks otherwise. *
- Determinism: fixed seeds; all scripts accept --seed; checksums recorded; reproducible artifacts. *
- Windows paths in examples; cross-platform-safe code where possible. ✓

Repository Targets (state)
- app\backend\main.py — FastAPI with /api/modules and /api/readiness endpoints. ✓
- app\frontend\ — React scaffold with Sites 1–3 and Model Lab tab placeholders. ✓
- modules\lexicon-wordnet3\, modules\chat-core\, modules\predictor-finance\ — manifests + stub pipelines/data/ui. ✓
- registry\, artifacts\ — present as directories; content to be generated at runtime. ✓

Milestones & Phases (with progress)

Phase 0 — Repo Hygiene (0.5d)
1. Add Git hooks (offline) for Conventional Commits and lint/test on pre-commit. 
2. Ensure CHANGELOG.md auto-update script (PowerShell/Python). 
3. tools\hashes_update.py to compute SHA256 into hashes.json. 
4. Document these in README. 
Status: not started.

Phase 1 — Backend Scaffolding (2–3d)
1. App factory, routers mounted (main.py present; expand routes). *
   - Add CORS for local dev; serve frontend static files in production mode. 
2. api\modules.py: manifest discovery with JSON Schema validation (docs\specs\module_manifest_schema.json). 
3. api\registry.py: CRUD for NNs/models/datasets/workspaces; promotion/rollback; export/import stubs. 
4. api\workspace.py: pending workspace CRUD; readiness check endpoint (extend current stub to full checks). 
5. api\runtime.py: start/stop runtimes; I/O endpoints (text/audio/image/timeseries). 
6. api\guardrails.py: get/set guardrail policies; enforce on runtime responses. 
7. api\metrics.py: push/pull metrics; list metrics files. 
8. api\training.py, api\evaluation.py: enqueue jobs and stream logs. 
9. Core utilities: io.py (checksums), seeds.py; registry file CRUD; runtime loader/scheduler; guardrails; metrics recorder/readers. 
10. tasks\train.py and tasks\evaluate.py (subprocess dispatcher with --seed). 
Outputs: Running API with discovery, registry CRUD, expanded readiness check, and training/eval dispatch.
Status: partially started (modules+readiness stubs exist).

Phase 2 — Frontend Scaffolding (2–3d)
1. Vite + Tailwind + shadcn/ui setup; ensure BrowserRouter works across refresh. 
2. Site 1 — Module Selection: persist selection to pending workspace via API. 
3. Site 2 — Model Selection & Ops: three paths UI; compatibility filtering; status chips; Proceed enabled only when all Ready. 
4. Site 3 — AI Workspace: readiness modal on failure; Chat panel; dynamic panel injection; Guardrails + Metrics side panels. 
5. Model Lab tab: placeholder charts wired to metrics endpoints. 
Outputs: Buildable SPA talking to backend; dynamic panels from manifests.
Status: scaffold present; wiring pending.

Phase 3 — WordNet Bootstrap (1–2d)
1. lexicon-wordnet3\pipelines\build_index.py — implemented stub; replace with real indexer later. ✓
2. lexicon-wordnet3\pipelines\synth_dialogs.py — implemented stub output + checksum. ✓
3. chat-core\pipelines\retrieve.py — implemented stub retrieval. ✓
4. Backend /runtime/chat endpoint calling retrieve.py; metrics writeback. 
Outputs: First run builds index and synthetic dialogs; chat retrieval works offline; metrics recorded. Partial.

Phase 4 — Readiness, Guardrails, Metrics (1–2d)
1. Implement readiness_check per docs\specs\readiness_check.md (manifests, mapping, registry, checksums, WordNet, guardrails, permissions, resources, offline mode, writable artifacts). *
2. GuardrailsPanel → backend policy; record blocks under artifacts\traces\guardrails.jsonl. 
3. Metrics recorder integrated with runtime/evaluation outputs (artifacts\metrics\<cap>\<model_id>.json). 
Outputs: Blocking modal on frontend; visible guardrail effects; charts render p50/p95 and task metrics.
Status: partial (stub readiness endpoint exists).

Phase 5 — Predictor-Finance Module (2–3d)
1. train_baselines.py & eval_forecast.py — stubs created; connect via backend task dispatcher. ✓/*
2. Frontend predictor panels: runtime dashboard + Model Lab forecast viewer wiring. 
Outputs: Deterministic dataset generation; train/eval cycles with metrics; charts in Model Lab.
Status: partially started.

Phase 6 — Export/Import, Promotion/Rollback (1–2d)
1. Registry export/import endpoints (tarball + hashes.json). 
2. Promotion/rollback endpoints; update promotion_history and workspace mapping; UI timeline. 
Outputs: Offline round-trip; timeline + rollback.
Status: not started.

Phase 7 — Tests & Acceptance (1–2d)
1. Backend unit tests: schema validation, registry CRUD, readiness, guardrails, metrics I/O, export/import. 
2. Module smoke tests: chat-core retrieval, predictor forecasts. 
3. Frontend e2e flows: Site 1 → Site 2 → Site 3; Model Lab; readiness gate. 
4. Determinism tests: same seed ⇒ same checksums (within tolerance). 
Outputs: Local test reports; acceptance criteria satisfied.
Status: not started.

Compatibility Enforcement (Site 2)
- Compute model.compatibility.signature as sig:<cap>|<task>|<in>-><out>|<resource_class> and enforce: model.capability ∈ module.capabilities AND model.task == module.task AND model.io_schema ⊇ module.inputs/outputs AND resources fit. 
- Disabled models show mismatch reasons; offer create/import actions. 
Status: to implement.

Determinism & Checksums
- tools\hashes_update.py: canonical JSON dumps; sorted keys; CRLF normalization; SHA256 to hashes.json. 
- Seed recording in datasets/models/metrics; metrics include checksums.report and checksums.source. 
Status: to implement.

Runtime & Safety
- Enforce max_tokens; redact PII; log guardrail events; deny network calls post-readiness. 
Status: to implement.

Permissions & Resources
- Respect manifest permissions; aggregate resource hints; block if over local limits with remediation. 
Status: to implement.

Developer Runbook (Windows-friendly)
- Backend dev: `uvicorn app.backend.main:app --reload` (set working directory to repo root). 
- Frontend dev: `cd app\frontend && npm run dev` (Vite) — to be added with package.json and Vite config. 
- First run setup (manual, until wired):
  - `python app\modules\lexicon-wordnet3\pipelines\build_index.py --seed 1337`
  - `python app\modules\lexicon-wordnet3\pipelines\synth_dialogs.py --seed 1337`
  - `python app\modules\predictor-finance\pipelines\train_baselines.py --seed 42 --model_id model_pred_stub_0001`
  - `python app\modules\predictor-finance\pipelines\eval_forecast.py --seed 42 --model_id model_pred_stub_0001`

Acceptance Mapping
- Site 1 discovery and selection → pending workspace snapshot. 
- Site 2 compatibility-only listings; 3 path flows; Proceed enabled when all Ready. 
- Site 3 offline runtime; Model Lab tab visualizes metrics; promotion timeline + rollback. 
- WordNet bootstrap; predictor metrics; export/import; checksums stable. 
Status: in progress.

Next Actions (immediate, in order)
1. Backend: add static files mount for frontend build and enable CORS for dev. 
2. Backend: implement /api/modules using JSON Schema validation (reuse existing endpoint; add validation via module_manifest_schema.json). 
3. Backend: extend /api/readiness to execute all checks specified in docs\specs\readiness_check.md. 
4. Backend: stub /api/workspace endpoints to persist module selection to registry\workspaces. 
5. Frontend: wire ModuleSelection to call /api/workspace to save selection. 
6. Backend: add /runtime/chat endpoint to call chat-core\pipelines\retrieve.py; record latency metrics. 
7. Frontend: readiness modal in Site 3; show errors from /api/readiness. 
8. Add tools\hashes_update.py and hashes.json generation to anchor reproducibility. 
