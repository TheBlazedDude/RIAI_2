# Modular AI App — Architecture & Plan (Insel Prinzip, Offline, Frontend React + Tailwind, Backend Python)

## 0) Purpose (read me first)

We’re building an offline‑capable, modular AI application with three stages:

1. **Select Modules** (chat, speech, vision, etc.)
2. **Model Launcher & Ops** (create neural networks, create models from existing NN, or choose existing models)
3. **AI Workspace** (run the AI offline; enable/disable module panels like vision/speech; later add a Learning/Predictions module)

This document defines the plan, contracts, UX, and acceptance criteria — **no code** — plus a copy‑paste **Prompt for Junie Ultimate Agent** at the end.

---

## 1) Core Principles

* **Insel Prinzip (Island Principle):** Each module is self‑contained: bundled assets, explicit inputs/outputs, no hidden external dependencies, and **no internet** after the AI UI starts.
* **Offline‑first:** All datasets, models, and UIs must function without network access. Any optional online features must be **pre‑cached** and clearly marked as non‑essential.
* **Deterministic & Reproducible:** Fixed seeds, recorded versions, checksums of artifacts, and tracked configs. Every result is reproducible given the same artifacts.
* **Modular Extensibility:** New modules can be dropped in and automatically discovered via a manifest. No app changes required to “wire them up.”
* **Clear UX:** Wizards and panels guide the user step‑by‑step; empty states explain what to do next; progress and validation are always visible.
* **Safety & Guardrails:** Configurable limits (max tokens, PII filters, content rules) and per‑module permissions (mic/camera/file access).

---

## 2) Terminology

* **Capability:** A functional category (e.g., `chat`, `vision`, `speech`, `predictor`).
* **Module:** A plug‑in that implements one or more capabilities with its own UI panels and runtime logic.
* **Neural Network (NN):** The architecture/topology (and possibly initial weights) from which models can be derived.
* **Model:** A trained instance tied to a specific NN + dataset + params; versioned and tracked.
* **Workspace:** A running configuration that maps capabilities → selected models + module settings.
* **Registry:** On‑disk records of modules, NNs, models, datasets, metrics, and promotions.
* **Dataset/Test Kit:** Local data required by modules for training/eval/smoke tests; can include synthetic data generators.

---

## 3) End‑to‑End Flow (3 Pages)

### Page A — **Module Selection**

* Show available capabilities (Chat, Speech, Vision, …) with toggles.
* When the user clicks **Continue**, persist the selected capabilities to a **pending Workspace**.

### Page B — **Model Launcher & Ops** (per capability)

For each selected capability, user sees **three options**:

1. **Create New Neural Network** → opens NN Wizard → upon finish, offers to **Create Model** from it.
2. **Create New Model from Existing NN** → opens Model Wizard, lets user pick an NN and dataset.
3. **Choose Existing Model** → pick from registry (shows version, metrics, dataset, last promoted tag).

Notes:

* A capability is considered **ready** once one model is selected (or created and selected).
* Show a checklist of capabilities with status chips: *Not started*, *In progress*, *Ready*.
* Provide **Validation**: refuse to proceed until **all selected capabilities** have a chosen model.

### Page C — **AI Workspace** (Offline Run)

* The AI starts in **offline mode**; all assets are validated before entering this page.
* The chat panel is always present if `chat` capability selected.
* Toggling **Vision** adds a camera/stream preview & recognition panel.
* Toggling **Speech** adds mic input + speech‑to‑text and text‑to‑speech outputs.
* Later, toggling **Predictions** adds a predictions panel (time‑series, classification, etc.).
* A **Metrics** side panel shows latency, throughput, and model performance charts (from evaluations).
* A **Guardrails** panel (admin) to toggle filters, max tokens, allowed file types, etc.

---

## 4) UX/UI Plan (beautiful, clear, consistent)

* **Design System:** Tailwind utility scale, shadcn/ui components, large readable typography, generous spacing, rounded corners (2xl), subtle shadows.
* **Information Design:**

  * **Wizards** use steps with permanent navigation (Back/Next) that never disappears.
  * **Empty states**: Each list or panel explains what to do next with a one‑sentence instruction.
  * **Status & Progress:** Chips (Draft, Training, Evaluating, Ready, Promoted), progress bars for long tasks.
  * **Tooltips** on all critical fields.
  * **Context help** side drawer with concise guidance and links to local docs.
* **Accessibility:** Keyboard navigable, screen‑reader labels, color‑contrast compliant.
* **Error Handling:** Errors are plain‑language, include action advice, and link to logs.
* **Metrics Graphs:** Simple line/area charts for latency (p50/p95) and accuracy over time.

---

## 5) Module Integration Contract (Manifest)

Each module publishes a **manifest** file (conceptual shape, not code):

* **id** (string, unique), **name**, **version**, **description**
* **capabilities** (list): e.g., `chat`, `vision`, `speech`, `predictor`
* **inputs** (list): allowed input types (text/audio/image/video/timeseries/table)
* **outputs** (list): produced output types (text/transcript/labels/embeddings/forecast)
* **ui\_panels** (list): names of panels it can render in AI Workspace (e.g., `vision_preview`, `speech_console`, `predictions_dashboard`)
* **required\_models** (map capability → model requirements): e.g., `chat` → `model_type=decoder-only`, `vision` → `model_type=detector`
* **datasets** (optional): names or descriptors of expected datasets; may include **synthetic generators** with seed parameters
* **test\_kits**: smoke tests & evaluation suites (inputs + expected properties/metrics)
* **training\_pipelines**: high‑level description of training/finetune steps, compute/profile hints
* **permissions**: camera/microphone/filesystems device access flags
* **resources**: CPU/GPU/VRAM/RAM expectations and max
* **guardrails**: content filters, PII regexes, file‑type restrictions
* **artifacts**: where module stores intermediate outputs locally
* **schema\_version**: contract version for future compatibility

**Discovery:** The app scans a local `modules/` directory for manifests and lists valid modules at Page A.

---

## 6) Registry & Artifacts (on disk)

* **neural\_nets/**: entries with id, architecture name, config, seed, training notes, checksums.
* **models/**: entries with id, linked `nn_id`, dataset(s) used, hyperparameters, metrics, size, hardware profile, checksums, and **promotion history** (candidate → staging → production).
* **datasets/**: registered datasets with origin (local/synthetic), schema, split info, license, checksums.
* **workspaces/**: saved mappings capability → model id + per‑module settings.
* **artifacts/**: evaluation reports, plots, confusion matrices, and latency snapshots.
* **hashes.json** & **VERSION**: simple reproducibility anchors.

**Operations (no code, but required behaviors):**

* Create NN → write entry under `neural_nets/` with config + checksum
* Create Model → write under `models/` with links to NN + dataset + metrics + checksum
* Promote/Rollback → update `promotion_history` and current alias
* Export/Import → tarball with registry entries + artifacts for full offline portability

---

## 7) Datasets & Test Kits (offline)

* **Dataset templates** per capability (text dialog, image folder, audio clips, OHLCV CSV, tabular). All local.
* **Synthetic data generators** with fixed seeds for deterministic test data when real data is absent.
* **Smoke tests**: tiny quick checks (seconds) to validate a model runs and produces plausible outputs.
* **Evaluation suites**: capability‑specific metrics (e.g., WER for speech, mAP for vision, MASE for forecasts, BLEU/perplexity for chat). Results saved to `artifacts/metrics/*.json` and visible in the UI.

---

## 8) Learning/Predictions Module (later stage)

* **Goal:** Learn patterns from local datasets and provide predictions/forecasts/classifications offline.
* **Inputs:** timeseries (finance, sensors), tabular features, labeled histories.
* **Model choices:** classical baselines (ARIMA/Prophet‑like equivalents), gradient boosting, small neural nets — **selected via the same Model Ops flow.**
* **Test data:** either provided by the module as synthetic generators or imported by the user via the dataset templates.
* **UI panel:** dataset selector, train/eval buttons, metrics table (MAE/RMSE/MAPE), forecast preview chart, export of predictions.

**Self‑explore (offline):**

* The module scans the local `datasets/` registry tags (e.g., `domain=finance`) and suggests candidates.
* If none exist, it offers to spawn a **synthetic dataset** with seeds and explains limits.

---

## 9) Offline‑First Guarantees

* Before entering the AI Workspace, the app runs a **Readiness Check**: availability and checksums of all selected models, NNs, datasets, and module assets.
* If something is missing, show a **blocking modal** with precise instructions.
* All logs, metrics, and traces are stored locally under `artifacts/` and viewable from the UI.

---

## 10) App API Surface (names only; no code)

* **Registry API:** list/create NN, list/create model, read metrics, promote/rollback, export/import
* **Workspace API:** create/load/save workspace, map capability→model, enable/disable modules
* **Module API:** discover manifests, query required datasets/models, run test kits, run evaluations
* **Runtime API:** start/stop module runtimes, post inputs (text/audio/image/timeseries), stream outputs
* **Guardrails API:** get/set policy toggles and thresholds
* **Metrics API:** push/pull runtime metrics, render charts

---

## 11) Security & Isolation

* Per‑module permission prompts (e.g., microphone, camera, file system paths).
* Resource caps (CPU %, RAM/VRAM ceilings) per module.
* Sandboxed execution with clear crash recovery and error surfacing.
* Local‑only storage; optional encryption at rest for artifacts.

---

## 12) Evaluation, Promotion & Rollback

* **Evaluation** runs produce a canonical report (metrics + environment + seed) saved to artifacts.
* **Promotion rules:** e.g., candidate → staging if beats baseline by X; staging → production if stable on repeated runs.
* **Rollback** allows reverting the current production alias to a prior model version.
* **UI:** a timeline widget showing promotions and metric deltas; a chart comparing versions.

---

## 13) Error & Log Conventions

* Every failing operation returns: `error_code`, `human_message`, `hint`, `where_to_find_logs`.
* UI always offers: **Copy details to clipboard** and **Open local logs**.
* For JSON parsing issues, show the **first invalid token context** and a suggested fix.

---

## 14) Acceptance Criteria (Done‑Done)

* Modules can be added by dropping a folder with a manifest under `modules/` and appear automatically in Page A.
* Page B enforces exactly one selected model per chosen capability before proceeding.
* Page C runs fully offline, with working toggles/panels for enabled modules.
* Model Ops provides the three paths (new NN → model, new model from NN, pick existing) without UI dead‑ends.
* Metrics charts render p50/p95 latency and task‑specific performance for selected models.
* Guardrails can be toggled and visibly affect runtime behavior.
* Export/Import round‑trips a workspace + registry on a new machine without internet.

---

## 15) Deliverables for Junie (what to produce)

* **Manifests & Registry Schemas** (described above, as structured docs — not code).
* **Wizard copy**: step titles, descriptions, field labels, and validation rules.
* **Empty‑state texts** and tooltip texts.
* **Readiness Check** checklist and failure messages.
* **Evaluation report format** (metrics JSON keys; chart labels).
* **Promotion policy** description and UI timeline spec.
* **Local docs**: a compact “How to run this AI offline” guide accessible from any page.

---

## 16) Prompt for Junie Ultimate Agent (copy‑paste)

**Title:** Build the Modular Offline AI App (Insel Prinzip)

**You are Junie Ultimate Agent.** Implement the following **without internet** and with strict modularity. Deliver production‑ready UI copy and structured specs (no code), plus mock data/artifacts that respect the formats below. Follow each instruction exactly.

**Goals**

1. Three‑page app flow: (A) Module Selection → (B) Model Launcher & Ops → (C) AI Workspace (offline run).
2. Modules are discovered via local manifests. A module can declare capabilities (chat, speech, vision, predictor), inputs/outputs, UI panels, datasets, test kits, training pipelines, resources, permissions, guardrails.
3. Models and NNs are tracked in a local registry with artifacts, metrics, promotion history, and checksums. Workspaces map capabilities to chosen models.
4. After entering the AI Workspace, the app must run offline only. All assets are verified beforehand by a Readiness Check.

**Deliverables**

* **Module Manifest** (spec only): id, name, version, description, capabilities, inputs, outputs, ui\_panels, required\_models, datasets, test\_kits, training\_pipelines, permissions, resources, guardrails, artifacts, schema\_version.
* **Registry Spec**: structures for `neural_nets/`, `models/`, `datasets/`, `workspaces/`, `artifacts/`, and `hashes.json` + `VERSION`; include promotion\_history and metrics report formats.
* **UI/UX Spec**: copy and step logic for all wizards; empty states; validation rules; error messages; tooltips; guardrails panel texts; metrics panel (latency p50/p95 + task metrics) with chart labels.
* **Readiness Check**: checklist of preconditions and failure messaging.
* **Evaluation Policy**: smoke tests + evaluation suites per capability; report keys; pass/fail rules; promotion thresholds and rollback procedure.
* **Learning/Predictions Module Spec**: inputs, synthetic dataset generators (seeded), metrics (MAE/RMSE/MAPE), and panel layout including forecast previews.
* **Local Docs**: “How to run offline” user guide (1‑page) referenced from every page.

**Behavioral Constraints**

* **No internet** usage anywhere after the AI Workspace starts. Prefer synthetic test kits when datasets are missing.
* **Determinism**: use fixed seeds in all mock data. Every metric must be reproducible.
* **Safety**: define guardrails (PII regex, content filters, max tokens, allowed file types) and show how toggles affect runtime behavior.
* **Performance & Footprint**: specify resource hints per module (CPU/GPU/VRAM/RAM), provide guidance for low‑spec fallback behavior.

**Acceptance Tests (Junie must provide mock runs)**

* Add a new `Predictor` module by placing its manifest in `modules/`; confirm it appears in Module Selection.
* Create a new NN, then a model from it, and select it for `chat`. Verify it appears as **Ready**.
* Choose existing models for `speech` and `vision`; run Readiness Check; enter AI Workspace offline.
* Toggle `vision` and `speech` panels; perform a smoke test; view metrics updates.
* Run the `Predictor` module with a synthetic OHLCV dataset; produce MAE/RMSE/MAPE in the evaluation report and show forecast previews.
* Promote a better `chat` model and show the timeline + rollback.
* Export the entire workspace + registry; re‑import and confirm parity of metrics and selections.

**Output Format**

* Provide all specs as structured sections (headings + bullet points), not code.
* Include mock examples of metrics and artifact filenames, with example values and seeds.
* Keep texts concise and consistent; use the exact field names defined above.

**Done when** all acceptance tests pass on paper (with mock artifacts), every screen has clear copy, all structures are specified, and the offline constraints + Insel Prinzip are demonstrably satisfied.

---

## 17) WordNet‑Only Bootstrap & Fourth Page (Model Lab)

### A) WordNet‑only Bootstrapped Chat (no internet)

**Initial reality:** Only WordNet 3.x is provided at install time. No other corpora.

**Strategy:**

* **Lexicon Module (`lexicon-wordnet3`)**

  * Ships WordNet files and exposes APIs: `lookup(word)`, `synsets(word)`, `gloss(synset)`, `relations(synset)` (hypernyms, hyponyms, antonyms), `morphy(stem)`.
  * Provides a **synthetic dialog generator** that creates Q/A pairs from glosses, synonyms, and relation paths (seeded for determinism).
  * Exposes a **retrieval index** over glosses/lemmas for TF‑IDF‑like search.
* **Chat Core Module (`chat-core`)**

  * Baseline **RAG‑lite chat**: retrieve glosses by query → compose an answer using synonyms/definitions/examples; explain provenance (synset IDs) in the artifacts.
  * Optional small **language model** (character/word‑level) trained on synthetic dialogs; if training disabled or data absent, falls back to retrieval‑only mode.
  * **Evaluation:** perplexity on synthetic dev split; response grounding score using WordNet path similarity; latency p50/p95.
* **No hardcoding of responses** — generation is programmatic from WordNet content and learned weights when available.

**Artifacts produced:** `artifacts/indices/wordnet-lexicon.jsonl`, `artifacts/datasets/wordnet_synth_{seed}.jsonl`, `artifacts/metrics/chat-core/*.json`.

**User expectations:** Early output may be stilted; UI clearly marks **Learning in progress** with visible metrics.

---

### B) Fourth Page: **Model Lab** (visual insights)

**Purpose:** Deep inspection and comparison of models across modules.

**Panels:**

* **Learning Curves**: loss/accuracy/MAE/RMSE over epochs.
* **Latency & Throughput**: p50/p95 latencies and tokens/s or items/s.
* **Confusion/PR/ROC**: for classifiers (vision/speech/predictor modules).
* **Forecast Viewer**: predictions vs actuals with error bands (predictor module).
* **Promotion Timeline**: version bumps, metrics deltas, rollback points.
* **Artifact Browser**: quick access to logs, checkpoints, reports.

**Interactions:**

* Compare **two models side‑by‑side** within the same capability.
* **Filter by tag** (candidate/staging/production) and **hardware profile**.
* **Export chart as image** and **export report JSON**.

**Data contract:** Pulls from `artifacts/metrics/*.json`, `artifacts/traces/*.jsonl`, and registry entries. No live internet.

---

### C) Module Discovery & Autonomy (dynamic, Insel Prinzip)

* **On Startup** the app scans `modules/*/manifest.json` and auto‑registers modules.
* If a module declares `autotrain=true` and has data or a synthetic generator, the backend may optionally **schedule a background train+eval job** (configurable) before the user enters the Workspace.
* If required data is **missing**, the module surfaces a **blocking readiness item** with one‑click actions: *Generate synthetic seed dataset* or *Import local files*.
* **UI Tabs** are defined by each module’s `ui_panels` and are injected into:

  * **AI Workspace** (runtime panels)
  * **Model Lab** (visualization panels and metrics)
* **No internet fallbacks**: every module must function fully offline or degrade gracefully (read‑only demo mode with clear notice).

---

## 18) Prompt for Junie Ultimate Agent — **Full Backend & Frontend (Code Required)**

**You are Junie Ultimate Agent. Build a complete, offline‑first, modular AI system implementing the plan in this document.**

### Hard Constraints

* **Insel Prinzip**: Every module is a self‑contained folder with its own assets, data, pipelines, and UI panels. No hidden external dependencies, no network calls.
* **Offline‑only after AI Workspace**: All downloads and optional extras must be pre‑bundled or omitted. Prefer compact, local baselines.
* **No dummy code**: Provide working implementations, tests, and demo datasets/generators. If training data is absent, fail gracefully with clear guidance.
* **Deterministic**: Use fixed seeds; record seeds in artifacts and metrics.

### Tech Stack (default)

* **Backend**: Python FastAPI with modular routers, task queue (in‑process or local worker), file‑based registry, PyTorch or NumPy‑only fallbacks for training loops.
* **Frontend**: React + Vite + Tailwind + shadcn/ui. Routing with four pages: A) Module Selection, B) Model Launcher & Ops, C) AI Workspace, D) Model Lab.
* **Storage**: Local folders (`registry/`, `artifacts/`, `modules/`) with JSON/YAML manifests and binary checkpoints.

### Directory Layout (generate this exact structure)

```
app/
  backend/
    main.py
    api/
      registry.py
      workspace.py
      runtime.py
      modules.py
      guardrails.py
      metrics.py
      training.py
      evaluation.py
    core/
      registry/
        neural_nets.py
        models.py
        datasets.py
        workspaces.py
      runtime/
        loader.py        # module discovery & lifecycle
        scheduler.py     # local jobs for train/eval
        guardrails.py
      metrics/
        recorder.py
        readers.py
      utils/
        seeds.py
        io.py
    tasks/
      train.py          # generic train loop dispatch
      evaluate.py       # generic eval dispatch
  frontend/
    index.html
    src/
      main.tsx
      App.tsx
      pages/
        ModuleSelection.tsx
        ModelLauncherOps.tsx
        AIWorkspace.tsx
        ModelLab.tsx
      components/
        Wizard.tsx
        StatusChips.tsx
        MetricsCharts.tsx
        GuardrailsPanel.tsx
        ModulePanelHost.tsx  # dynamic panel injection per module
      lib/
        api.ts
        routes.ts
  modules/
    lexicon-wordnet3/
      manifest.json
      data/wordnet3/*    # provided
      pipelines/
        build_index.py
        synth_dialogs.py
      ui/
        panels.json      # declares no runtime panel; used by chat-core
    chat-core/
      manifest.json
      data/               # synthetic dialogs generated at first run
      models/
      pipelines/
        train_lm.py      # char/word level; optional
        eval_lm.py
        retrieve.py
      ui/
        panel_chat.json  # declares AIWorkspace chat panel
    predictor-finance/
      manifest.json
      data/
        samples/ohlcv.csv
        synth_config.yaml
      pipelines/
        train_baselines.py   # AR/GBM/small MLP
        eval_forecast.py
      ui/
        panel_predictor.json # declares AIWorkspace + ModelLab panels
registry/
artifacts/
```

### Module Manifest Schema (implement as JSON Schema + validation)

* `id`, `name`, `version`, `description`
* `capabilities`: array (e.g., `chat`, `vision`, `speech`, `predictor`)
* `ui_panels`: array (e.g., `chat_panel`, `vision_preview`, `predictions_dashboard`)
* `required_models`: map capability → constraints (e.g., `model_type`, `min_data`)
* `datasets`: list of named datasets; may include `synthetic_generators` with `seed`
* `pipelines`: `{train: path, eval: path, retrieve?: path}`
* `permissions`: camera/mic/fs flags (if applicable)
* `resources`: CPU/GPU/VRAM/RAM hints
* `guardrails`: filters and limits
* `autotrain`: boolean
* `schema_version`

### Backend Behaviors to Implement

1. **Module Discovery**: scan `modules/*/manifest.json`, validate schema, register capabilities and panels.
2. **Registry**: CRUD for NNs, models, datasets, workspaces; promotion history; checksums; export/import.
3. **Training/Eval**: generic dispatcher that calls module pipelines; stream logs to artifacts; emit metrics JSON with seeds.
4. **Readiness Check**: verify selected models, datasets, checksums before entering AI Workspace.
5. **Runtime**: start module runtimes; enforce guardrails; provide I/O endpoints (text/audio/image/timeseries) and stream outputs.
6. **Metrics Recorder**: collect latency p50/p95 and task metrics; store under `artifacts/metrics/<capability>/<model_id>.json`.
7. **Graceful Degradation**: if dataset missing and no generator, disable training with actionable error; keep retrieval‑only or demo modes where defined.

### Frontend Behaviors to Implement

* **Page A (Module Selection)**: show discovered modules/capabilities; toggle selection; persist pending workspace.
* **Page B (Model Launcher & Ops)**: three paths per capability (new NN, new model from NN, choose existing). Checklist status. Buttons never disappear.
* **Page C (AI Workspace)**: always‑on chat (if selected); dynamic panel injection from modules; toggles for vision/speech/predictor; metrics side panel; guardrails admin panel.
* **Page D (Model Lab)**: charts for learning curves, latency, PR/ROC, forecast viewer, promotion timeline, artifact browser; compare models.
* **Dynamic Tabs**: panels declared by modules auto‑appear in the correct pages.
* **Docs & Help**: context drawer with local “How to run offline” guide.

### WordNet‑Only Boot Process (must implement)

* Build lexicon index from WordNet on first run (cached).
* Generate synthetic dialog dataset (seeded), save under `modules/chat-core/data/`.
* Train a tiny LM if resources allow; otherwise run retrieval‑only chat.
* Provide evaluation and artifacts; surface metrics in Model Lab.

### Guardrails & Safety (enforce)

* Max tokens/response length; PII regex; content filters; allowed file types per module.
* Record when a guardrail blocks/edits output; show in UI.

### Tests & Acceptance (must pass)

* Module discovery adds `predictor-finance`; its panels appear in Workspace & Model Lab.
* WordNet bootstrap produces a retrieval index and synthetic dataset; chat works offline; metrics recorded.
* Training/eval cycles for `predictor-finance` run on provided CSV and synthetic data; MAE/RMSE/MAPE logged and charted.
* Readiness Check blocks when a module lacks data and no generator is declared, with clear remediation.
* Promotion & rollback update timeline and active model.
* Export/import preserves registry and artifacts with consistent checksums.

### Output Requirements

* Generate the **entire backend & frontend codebase**, manifests, and example data per directory layout. No TODOs or placeholders; runnable offline.
* Provide **README (offline)**: setup, seed choices, how to run, and how to add a new module folder.
* Ensure all scripts accept **`--seed`** and emit **checksums**.

**Done when** the system runs offline end‑to‑end with only WordNet 3.x provided initially, supports dynamic module addition, and the Model Lab visualizes training/evaluation across modules.

---

## 19) Reworked Structure & Prompt v2 (per your 3‑sites + Model Lab tab)

> This section **supersedes** earlier flow notes. It encodes the exact three sites you described, with **Model Lab as a tab on Site 3**. It also formalizes compatibility rules, NN↔Model flows, Git practices, README, and CHANGELOG requirements.

### SITES OVERVIEW

* **Site 1 — Module Selection**
  Choose which modules participate in this run (Chat, Speech, Vision, Predictor, etc.). Persist selection to a *pending workspace*.

* **Site 2 — Model Selection & Ops**
  For **each selected module**, map **only compatible models**. Provide three actions:

  1. **Create New Neural Network** → then **Create New Model** from that NN.
  2. **Create New Model from Existing NN** (pick an NN, dataset/hparams → produce a new model).
  3. **Choose Existing Model** (already trained & registered).
     A module becomes **Ready** when exactly one compatible model is mapped. Proceed only when all selected modules are Ready.

* **Site 3 — AI Frontend (Workspace)**
  The live UI (chat page). Module UIs are addable windows (dockable/resizable).
  **Tab inside Site 3:** **Model Lab** — rich visual analytics (learning curves, latency, PR/ROC, forecasts, promotion timeline, artifact browser).

### COMPATIBILITY RULES (prevents mismatched models)

To ensure correct model mapping in **Site 2**, we define **typed contracts**:

* **Module manifest** must include: `capabilities`, `task`, `inputs`, `outputs`, `model_constraints` (e.g., `task=asr` with `audio→text`, or `task=dialogue` with `text↔text`).
* **Model registry entry** must include: `capability`, `task`, `io_schema` (input/output types), `nn_id`, `dataset_ids`, `resources` (CPU/GPU/VRAM), `version`, `metrics`, and `compatibility.signature`.
* **Matching logic:** A model is **eligible** for a module iff:
  `model.capability ∈ module.capabilities` AND `model.task == module.task` AND `model.io_schema ⊇ module.inputs/outputs` AND `resources fit` AND (optional) `semantic_signature` match.
* If no models match, **Site 2** prompts the user to create one (Path 1 or 2), or to import artifacts.

**Important NN↔Model rules:**

* You **cannot** change the NN of an existing model; to reuse an NN with new data/hparams, **create a new model** (Path 2).
* Choosing an **existing model** (Path 3) uses its own NN by definition.
* Creating a **new NN** (Path 1) must immediately offer to create a model from it before it can be mapped.

### WORDNET‑ONLY BOOTSTRAP (Chat)

* Ship **`lexicon-wordnet3`** module (WordNet files, retrieval index, synthetic dialog generator — seeded & deterministic).
* Ship **`chat-core`** module: retrieval‑first chat using WordNet glosses/relations; optional tiny LM trained on synthetic dialogs; no hardcoded responses.
* Early outputs may be rudimentary; UI surfaces **Learning in progress** and links to Model Lab metrics.

### OFFLINE & INSEL PRINZIP (unchanged, enforced)

* After entering **Site 3**, the app runs **offline only**. All assets validated by a **Readiness Check** beforehand.
* Each module is an **island** (self‑contained folder with manifest, data/pipelines/UI panels). No hidden external calls.

### GIT, README, CHANGELOG (traceable development)

* **Repository layout**: monorepo `app/` with `backend/`, `frontend/`, `modules/`, `registry/`, `artifacts/`.
* **Commit conventions**: use **Conventional Commits** (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `perf:`), scoped by area (e.g., `feat(frontend): add Model Lab tab`).
* **Branching**: trunk‑based with short‑lived feature branches; tag **milestones** (e.g., `v0.1.0-alpha1`).
* **Git hooks (generated by Junie):** commit‑msg validator, lint/test on pre‑commit (offline tools only).
* **README.md (required, generated by Junie):**

  1. Purpose & offline constraints
  2. Quickstart (first run builds WordNet index; how to pick modules/models)
  3. Site 1/2/3 walkthrough and **Model Lab tab**
  4. How to add a new module folder (manifest fields, datasets, UI panels)
  5. How compatibility is enforced (why a model may not appear)
  6. Export/import of registry & artifacts
  7. Troubleshooting (readiness failures, missing data)
* **CHANGELOG.md (single file, compact):** per commit or grouped by day; include date, short hash, scope, and one‑line summary. Example line:
  `2025‑08‑28 (a1b2c3d) feat(model‑lab): add latency p95 chart & export button`
  Junie must **append automatically** on each meaningful commit.

### MODEL LAB (as **tab** inside Site 3)

* **Visuals:** learning curves (loss/acc/MAE/RMSE), latency p50/p95, PR/ROC, confusion matrix, forecast previews, promotion timeline, artifact browser.
* **Compare** two models side‑by‑side; filter by tag (candidate/staging/production) & hardware profile; export charts + metrics JSON.

### ACCEPTANCE CRITERIA (revised)

1. **Site 1** lists discovered modules (from `modules/*/manifest.json`); selection persists to a pending workspace.
2. **Site 2** shows only **compatible** models per selected module; all three paths (new NN→model, new model from NN, choose existing) function without dead‑ends. Proceed button enabled only when all modules are **Ready**.
3. **Site 3** runs offline: chat window present; speech/vision/predictor windows are addable; **Model Lab** is a **tab within Site 3**, not a separate page.
4. WordNet bootstrap works out‑of‑the‑box; chat produces answers via retrieval and/or tiny LM; metrics populate Model Lab.
5. Git history uses Conventional Commits; **README.md** and **CHANGELOG.md** exist and are accurate; tags present.
6. Export/import preserves registry/artifacts; checksums stable; promotion & rollback reflected on timeline.

### PROMPT FOR JUNIE ULTIMATE AGENT (v2 — build everything)

**Role:** You are Junie Ultimate Agent. Build a **complete**, **offline‑first**, **modular** AI system with the exact **three sites + Model Lab tab** described above. Generate **backend + frontend code**, **module folders**, **manifests**, **registry**, **artifacts**, **README.md**, and **CHANGELOG.md**. Use Git with Conventional Commits and create meaningful, traceable commits for each step.

**Must‑haves**

* **Modules as islands** (self‑contained folders). Discovery via `modules/*/manifest.json` at startup.
* **Compatibility enforcement**: only show eligible models in Site 2; provide clear reasons when none are available and offer creation/import options.
* **NN→Model flows**: Path 1 (new NN→new model), Path 2 (existing NN→new model), Path 3 (choose existing model).
* **Site 3** offline runtime with addable windows; **Model Lab** as a **tab** inside Site 3.
* **WordNet‑only bootstrap** for chat (lexicon index, synthetic dialogs, optional tiny LM).
* **Guardrails** (max tokens, PII regex, content filters, file‑type limits) applied at runtime with visible effects in UI.
* **Metrics** (latency p50/p95 and task‑specific metrics) recorded to `artifacts/metrics/...` and visualized in Model Lab.
* **Git, README, CHANGELOG** as specified above; CHANGELOG updated automatically with each meaningful commit.

**Output format**

* Produce a runnable repository with code and assets; include scripts for first‑run setup (index build, synthetic data generation).
* Provide mock datasets where needed (seeded), but **no placeholders** — everything should run offline end‑to‑end.
* Include enforcement of compatibility at API & UI levels.

**Definition of Done**

* The app guides a new user from **Site 1 → Site 2 → Site 3**; compatible models mapped; AI runs offline; Model Lab tab visualizes learning/evaluation; Git history + README + CHANGELOG reflect all work.
