# Evaluation Policy & Promotion Rules (Deterministic, Offline)

Version: 1

Purpose: Define smoke tests and evaluation suites per capability; standardize report keys; enforce pass/fail rules; set promotion thresholds and rollback procedures. All evaluations must be reproducible with fixed seeds and local data.

General
- Seeds: All runs accept --seed and record the integer seed in reports.
- Reports: JSON files under artifacts\metrics\<capability>\<model_id>.json.
- Timing: latency_ms.p50 and latency_ms.p95 recorded for each suite.
- Environment: include env (cpu,gpu,ram_mb,vram_mb) in reports.

Capabilities

1) Chat (chat-core, WordNet bootstrap)
- Smoke Test
  - Input: "Define 'bank'" with retrieval index present.
  - Expectation: Non-empty answer with at least one synset provenance id.
  - Pass: answer_tokens ≤ guardrails.max_tokens; provenance length ≥1.
- Evaluation Suite
  - Dataset: artifacts\datasets\wordnet_synth_<seed>.jsonl (dev split)
  - Metrics:
    - grounding_score (0..1): average path similarity to relevant synsets
    - perplexity (optional if LM trained): lower is better
    - latency_ms: {p50, p95}
  - Report keys (chat): {model_id, capability, seed, latency_ms, grounding_score, perplexity, env, timestamp, checksums}
- Thresholds
  - Pass: grounding_score ≥ 0.6 AND latency_ms.p95 ≤ 250ms on low CPU profile.
  - Promotion: beats baseline grounding_score by ≥ 0.03 OR reduces p95 by ≥ 20%.

2) Vision (detector/classifier)
- Smoke Test
  - Input: 1 small local image from a bundled sample; run forward.
  - Pass: non-empty outputs and latency_ms.p95 < 500ms (CPU), or 150ms (GPU) for a tiny classifier.
- Evaluation Suite
  - Dataset: locally registered image folder with labels.
  - Metrics: accuracy (classifier) or mAP@0.5 (detector), latency_ms.
  - Report keys (vision): {model_id, capability, seed, latency_ms, accuracy|map50, env, timestamp}
- Thresholds: accuracy ≥ 0.80 (tiny set) or mAP@0.5 ≥ 0.20 for demo; p95 within budget.

3) Speech (ASR/TTS)
- Smoke Test
  - Input: short audio clip (≤5s) from local samples.
  - Pass: transcript non-empty (ASR) OR waveform rendered (TTS) within p95 budget.
- Evaluation Suite (ASR)
  - Dataset: local clips + references.
  - Metrics: WER, CER, latency_ms.
  - Report keys (speech): {model_id, capability, seed, latency_ms, wer, cer, env, timestamp}
- Thresholds: WER ≤ 0.40 on demo; p95 within budget.

4) Predictor (time-series forecasts)
- Smoke Test
  - Input: 64-step synthetic OHLCV slice (seeded) → forecast 8 steps.
  - Pass: predictions array length==horizon and finite values.
- Evaluation Suite
  - Dataset: artifacts\datasets\ohlcv_synth_<seed>.jsonl (dev/test split)
  - Metrics: MAE, RMSE, MAPE, latency_ms.
  - Report keys (predictor): {model_id, capability, seed, latency_ms, mae, rmse, mape, horizon, env, timestamp}
- Thresholds
  - Pass: mape ≤ 0.10 on synthetic; p95 ≤ 300ms.
  - Promotion: MAE improved by ≥ 5% vs current production OR p95 reduced by ≥ 25%.

Promotion Workflow
1. Candidate: new model after train+eval. Tag: candidate; write report and append to promotion_history.
2. Staging: auto-promote if it beats baseline thresholds above and has no failing smoke tests.
3. Production: promote from staging after N=3 repeated evaluation runs (seeds: 41, 42, 43) show stable metrics (stddev ≤ 10% of mean) and no regressions.

Rollback Procedure
- Trigger: user-initiated from Model Lab timeline or automatic on repeated failures.
- Action: set workspace mapping alias back to previous production model; append promotion_history entry with tag: production_rollback and include reason.

Determinism & Checksums
- Every report includes checksums.report of itself and checksums.source listing any dataset file checksums.
- Re-running with same seed and artifacts must produce identical metrics within numerical tolerance (1e-6) for deterministic algorithms.

Example Predictor Report
{
  "model_id": "model_pred_mlp_0007",
  "capability": "predictor",
  "seed": 42,
  "latency_ms": {"p50": 8.1, "p95": 22.9},
  "mae": 0.92,
  "rmse": 1.24,
  "mape": 0.031,
  "horizon": 8,
  "env": {"cpu": "x86_64", "gpu": "none"},
  "timestamp": "2025-08-28T16:40:00+02:00",
  "checksums": {"report": "SHA256:de34...", "source": ["SHA256:1a2b..."]}
}
