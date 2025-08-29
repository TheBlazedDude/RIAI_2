# UI/UX Spec — Three Sites + Model Lab (Offline, Insel Prinzip)

Version: 1

Design System
- Tailwind scale, shadcn/ui components, large readable typography, generous spacing, rounded corners (2xl), subtle shadows.
- Accessibility: keyboard navigable (Tab order consistent), ARIA labels on controls, color-contrast AA+.
- Error style: plain-language messages, action advice, and link to local logs.

Global UI Elements
- Top Bar: app title, current workspace name, offline status indicator (green when all checks pass), Help button (opens local docs drawer).
- Side Drawer: “How to run offline” (docs/local_docs/how_to_run_offline.md) content rendered; searchable.
- Status Chips: Draft, Training, Evaluating, Ready, Promoted.
- Progress Indicators: spinners for short (<2s), progress bars for long tasks.

Site 1 — Module Selection
Purpose: Discover modules (modules/*/manifest.json) and choose which capabilities to include.

Layout
- Header: “Select Modules”
- Body: grid of module cards (name, description, capabilities, resources hints, permissions badges)
- Footer: Back (disabled) | Continue → (enabled if ≥1 module selected)

Interactions
- Module Card: toggle Include (checkbox). Tooltip: “Add this module to the pending workspace.”
- Details popover: shows inputs/outputs, ui_panels, datasets/test_kits, guardrails.

Empty State
- “No modules found. Drop a folder containing manifest.json into the modules/ directory and return to this page.”

Validation
- At least one module required to proceed.

Errors
- discovery_failed: “Could not read module manifests. Hint: Check manifest schema against docs/specs/module_manifest_schema.json. See artifacts\\logs.”

Copy (examples)
- Title: “Choose your modules”
- Subtitle: “Modules run fully offline and can be added or removed at any time.”
- Continue disabled text: “Select at least one module to continue.”

Site 2 — Model Selection & Ops (per selected module)
Purpose: Map exactly one compatible model per module; provide three paths: new NN→model, new model from existing NN, choose existing model.

Layout
- Left: Checklist of selected modules with status chips (Not started, In progress, Ready)
- Right: Panel with three tabs per module: 1) New Neural Network, 2) New Model from Existing NN, 3) Choose Existing Model
- Footer: Back | Proceed to Workspace (enabled only when all selected modules are Ready)

Compatibility Rules (UI enforcement)
- Show only models where capability∈module.capabilities AND task==module.task AND io_schema covers module inputs/outputs AND resources fit.
- If none eligible: show callouts with reasons and actions: “No compatible models. Create one (paths 1 or 2) or Import.”

Path 1 — Create New Neural Network (Wizard)
- Step 1: Architecture
  - Fields: Architecture (select from neural_networks.yaml ids), Layers (int), Hidden size (int), Seed (int)
  - Validation: required; seed defaults to 1337; ranges guarded.
  - Tooltip Architecture: “Pick a topology for your new NN.”
- Step 2: Config & Notes
  - Fields: Dropout, Learning rate (for default trainer), Notes
  - Validation: numeric ranges; optional Notes.
- Step 3: Create Model from NN
  - Prompt: “Create a model from this NN now?”
  - Buttons: Create Model → (goes to Path 2 prefilled), Skip (cannot map until a model exists; explain why)

Path 2 — Create New Model from Existing NN (Wizard)
- Step 1: Choose NN
  - List NNs filtered by compatible architecture/task. Empty state: “No NNs yet. Create a new NN first.”
- Step 2: Dataset & HParams
  - Fields: Dataset (pick existing or Generate Synthetic), Train/Dev/Test split, Epochs, Batch size, Seed
  - Tooltips: “Synthetic generators produce deterministic data from a fixed seed.”
- Step 3: Train & Evaluate
  - Show progress; allow cancel. After completion, show metrics summary with links to artifacts.
- Step 4: Select This Model
  - Button: “Use this model for <module>” → sets module status to Ready.

Path 3 — Choose Existing Model
- Table columns: Name, Version, Capability, Task, Dataset(s), Metrics (key value), Tag (candidate/staging/production)
- Filter: Compatibility only (default ON) with toggle to show all (disabled entries explain mismatch).
- Action: “Select” → marks module Ready.

Errors & Guidance
- nn_required: “You must create or select a model derived from a neural network. Hint: Use Path 1 or 2.”
- incompatible_model: “This model does not match the module’s IO or task.”

Site 3 — AI Workspace (Offline Run)
Purpose: Run modules offline; inject module UI panels; provide Guardrails and Metrics; include Model Lab tab.

Layout
- Main: Chat panel docked when chat capability mapped; additional windows for other capabilities (dockable/resizable).
- Right Sidebar (collapsible): Metrics and Guardrails tabs.
- Tabs: Runtime | Model Lab

Runtime Tab
- Chat Panel (if chat selected):
  - Input box with max tokens counter; Send button.
  - Provenance toggle: “Show sources (synset IDs / dataset rows).”
- Vision/Speech/Predictor Panels: dynamically injected based on module ui_panels.
- Smoke Test Button: “Run quick test” (uses module test_kits).

Guardrails Panel (Admin)
- Controls: Max tokens (slider), PII filter (on/off), Blocked categories (multi-select), Allowed file types (tags)
- Copy: “Guardrails apply immediately to all outputs. Blocks are logged under artifacts\\traces.”

Metrics Panel
- Latency: p50/p95 chart (line) per capability; “Tokens/s” or “Items/s” when applicable.
- Task metrics: chat (perplexity, grounding_score), predictor (MAE/RMSE/MAPE), vision/speech (task-specific).
- Buttons: Export chart as image; Export latest report JSON.

Model Lab (Tab within Site 3)
- Panels:
  - Learning Curves: loss/accuracy/MAE/RMSE vs epochs.
  - Latency & Throughput: p50/p95 and items/s.
  - Confusion/PR/ROC (for classifiers).
  - Forecast Viewer (predictor): predictions vs actuals with 80/95% bands.
  - Promotion Timeline: version bumps, tags, metric deltas; Rollback button.
  - Artifact Browser: quick links to logs, checkpoints, reports.
- Interactions: Compare two models; Filter by tag and hardware profile; Export charts and metrics JSON.

Copy Snippets
- Empty Chat: “Ask something. This chat uses an offline lexicon and optional local model.”
- Readiness Blocked: “Some assets are missing. See Readiness Check for remediation.”
- Learning in Progress: “Outputs may be rudimentary while local models are training.”

Validation Rules (selected)
- Proceed to Workspace requires every selected module to be Ready (exactly one model mapped).
- Guardrails max_tokens must be ≥1; PII regex cannot be empty when PII filter is ON.

Error Messages (format)
- {error_code, human_message, hint, where_to_find_logs}
Examples:
- readiness_missing_artifact: “Missing model checkpoint for <model_id>. Hint: Re-run training or import artifacts. Logs: artifacts\\logs.”
- json_parse_error: “Invalid token near ‘…’. Fix the character at position <n>. Logs: artifacts\\logs.”

Tooltips (examples)
- “Compatibility only” — “Hide models that don’t meet this module’s IO and resource constraints.”
- “Provenance” — “Show source synsets or dataset rows used to generate this answer.”

Determinism Notes
- All synthetic data gens and evaluations accept --seed and record the value in metrics reports and registry entries.
