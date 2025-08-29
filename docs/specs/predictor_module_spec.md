# Learning/Predictions Module Spec — predictor-finance (Offline, Insel Prinzip)

Version: 1

Purpose
- Provide an offline predictor module for time-series forecasting (finance OHLCV). Implements seeded synthetic datasets, baseline models, evaluation metrics (MAE/RMSE/MAPE), and UI panels for AI Workspace and Model Lab.

Manifest (example)
```json
{
  "id": "predictor-finance",
  "name": "Predictor — Finance (OHLCV)",
  "version": "0.1.0",
  "description": "Offline forecasts over OHLCV with seeded synthetic data and small baselines.",
  "capabilities": ["predictor"],
  "task": "forecast",
  "inputs": ["timeseries", "table"],
  "outputs": ["forecast"],
  "ui_panels": ["predictions_dashboard", "model_lab_forecast"],
  "model_constraints": {
    "model_type": "baseline_or_small_mlp",
    "io_schema": {"inputs": ["timeseries"], "outputs": ["forecast"]}
  },
  "datasets": [
    {
      "id": "ohlcv_samples",
      "name": "Bundled OHLCV Samples",
      "tags": ["finance", "ohlcv"]
    },
    {
      "id": "ohlcv_synth",
      "name": "Synthetic OHLCV",
      "tags": ["synthetic", "finance"],
      "synthetic_generators": [
        {"name": "ohlcv_ar1_gbm", "seed": 42, "params": {"length": 512, "horizon": 8, "volatility": 0.01}}
      ]
    }
  ],
  "pipelines": {
    "train": "modules\\predictor-finance\\pipelines\\train_baselines.py",
    "eval": "modules\\predictor-finance\\pipelines\\eval_forecast.py"
  },
  "permissions": {"filesystem": true, "camera": false, "microphone": false},
  "resources": {"cpu_hint": "low", "gpu_required": false, "vram_mb": 0, "ram_mb": 512},
  "guardrails": {"max_tokens": 256, "pii_regex": [], "blocked_categories": [], "allowed_file_types": [".csv", ".json"]},
  "artifacts": {"root": "artifacts\\predictor-finance", "metrics_dir": "artifacts\\metrics\\predictor"},
  "autotrain": false,
  "schema_version": "1"
}
```

Synthetic Dataset Generators
- Name: ohlcv_ar1_gbm
- Seed: integer (default 42). Deterministic.
- Inputs: length (default 512), horizon (default 8), volatility (default 0.01)
- Process:
  1) Generate returns r_t = phi * r_{t-1} + eps_t where eps_t ~ N(0, volatility^2), phi=0.3.
  2) Price_t = Price_{t-1} * exp(r_t). Initialize Price_0 = 100.
  3) OHLC from Price_t with small random spreads; Volume as positive noise around mean 1e6.
- Output: artifacts\datasets\ohlcv_synth_<seed>.jsonl; registry entry datasets/ohlcv_synth_<seed>.json.

Baselines & Models
- AR(1)/AR(2) with rolling forecast.
- Gradient Boosting (shallow, local implementation) over lagged features.
- Small MLP (1–2 hidden layers) on lagged windows.
- Hyperparameters accept --seed and are recorded in model registry entry.

UI Panels
1) AI Workspace — predictions_dashboard
- Controls: Dataset selector; Horizon; Run Forecast; Export Predictions (.csv/.json)
- Table: last N actuals + forecast values; error bands (±1σ) when available.
- Actions: “Run quick smoke test” (uses 64-step slice; horizon=8).

2) Model Lab — model_lab_forecast
- Chart: predictions vs actuals (test split) with MAE/RMSE/MAPE table.
- Timeline: promotion history with tags and metrics deltas.
- Controls: Compare two models; filter by tag/hardware profile; export chart/report.

Metrics & Reports
- Location: artifacts\metrics\predictor\<model_id>.json
- Keys: {model_id, capability: "predictor", seed, latency_ms: {p50,p95}, mae, rmse, mape, horizon, env, timestamp, checksums}
- Pass thresholds: mape ≤ 0.10 (synthetic), p95 ≤ 300ms. See evaluation_policy.md.

Readiness & Offline Guarantees
- If no dataset found and no generator declared → readiness blocked with remediation: “Generate synthetic OHLCV (seed=42)” or “Import CSV from local disk.”
- No internet calls; training/eval run on local CPU, small memory footprint.

Mock Artifacts (example)
- artifacts\datasets\ohlcv_synth_42.jsonl (SHA256:1a2b...)
- artifacts\metrics\predictor\model_pred_mlp_0007.json (SHA256:de34...)

Acceptance Test (paper)
- Add the manifest above under modules\predictor-finance\manifest.json → module appears on Site 1.
- Create model via Path 2 with synthetic dataset; evaluation writes metrics with seed=42; Model Lab shows curves and forecast viewer.
- Promote to staging then production when thresholds met; rollback from Model Lab timeline is recorded in promotion_history.
