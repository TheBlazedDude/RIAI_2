1. Implementation Plan (Session v2025-08-28)
   - Align repo with Modular Offline AI App guidelines and this issue. ✓
   - Provide progress markers per task/sub-task. ✓

2. Backend — Immediate Actions & Scaffolding
   1) Static hosting & CORS
      - Mount static frontend if app\frontend\dist exists at route /app. ✓
      - Keep CORS for Vite dev (ports 5173/5174). ✓
   2) API stubs
      - Registry endpoints: list/create NNs and Models (stubs with local JSON persistence under app\registry). ✓
      - Runtime endpoints: /api/runtime/start, /api/runtime/stop, /api/runtime/post (no-ops, return acknowledgements). ✓
      - Metrics endpoints: /api/metrics/latest and /api/metrics/by_id to read artifacts\metrics files. ✓
   3) Readiness expansion
      - Validate manifests exist and include schema-required fields; surface per-module errors. ✓
      - Ensure registry dirs: app\registry\{workspaces,models,neural_nets,datasets} exist. ✓
      - Dataset checks: predictor-finance sample CSV exists; if missing, add blocking error with remediation. ✓
      - Artifacts dirs: ensure app\artifacts\{indices,metrics,logs} exist. ✓
      - WordNet root check (WordNet-3.0 folder exists) and WordNet index required when chat selected. ✓
   4) Jobs & Guardrails
      - Job dispatcher stubs: /api/train, /api/evaluate accept module_id, seed; write minimal job record under app\artifacts\jobs. ✓
      - Guardrails config: /api/guardrails GET/POST persisted under app\registry\guardrails\config.json; echo in readiness. ✓

3. Frontend — Immediate Actions (next PR)
   - Site 1 ModuleSelection wired to /api/workspace (save & load). 
   - Site 2 Model Ops stubs and compatibility filtering using module task/inputs/outputs (prepare UI copy; disable proceed until Ready). 
   - Site 3 AI Workspace: readiness modal using /api/readiness; Model Lab tab placeholders; charts wired to /api/metrics. 
   Status: planned (to implement next). 

4. Module Tasks Integration
   - WordNet index build & synthetic dialogs: define artifact paths (artifacts/indices/wordnet-lexicon.jsonl; modules/chat-core/data/wordnet_synth_{seed}.jsonl); add readiness guidance and future dispatcher hook points. ✓
   - Predictor training/eval: accept through /api/train and /api/evaluate stubs with module_id=predictor-finance; later bind to modules/pipelines. ✓

5. Tests & Acceptance Mapping
   - Determinism: seeds recorded in job record; file names include seed. 
   - Offline-first: no network I/O in code paths; readiness blocks when assets missing. 
   - Discovery: /api/modules validates manifests and reports issues. 
   - Readiness remediation messages: clear human_message and paths. 
   - Promotion/rollback: planned for a subsequent task. 
   Status: documented for current scope. 

6. Developer Workflow (Windows-friendly)
   - Backend: uvicorn app.backend.main:app --reload
   - Frontend dev: cd app\frontend; npm run dev (Vite)
   - Frontend build: npm run build; backend serves /app if dist present
   - Health: Invoke-RestMethod http://localhost:8000/api/health
   - Save selection: Invoke-RestMethod -Method POST http://localhost:8000/api/workspace -Body (@{selected_modules=@("chat-core","predictor-finance")} | ConvertTo-Json) -ContentType application/json
   - Seeds: use -seed parameter in future CLI; API stubs accept seed field.
   - WordNet: ensure WordNet-3.0 folder exists at repo root; build index via module pipeline (future); readiness will guide. 
   Status: documented. 

7. Verification & Submission
   - Implement backend scaffolding and re-run /api/health and /api/readiness. ✓
   - Summarize changes and submit. ✓