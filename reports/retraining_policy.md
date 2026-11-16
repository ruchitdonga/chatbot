# Retraining policy (Phase 11)

Applies to the FeastFleet demo NLU (FeastFleet is fictional). It describes how a production team would govern this
model. Nothing here retrains automatically: retraining is triggered by monitoring, and promotion is a human decision.

## What is monitored

`python -m src.monitoring.drift_report --log logs/nlu_events.jsonl` compares live traffic with the reference profile
(`reports/monitoring/reference_profile.json`: the training split with the deployed model's predictions).

| Signal | Source | Why |
|---|---|---|
| Locale distribution (PSI) | event log `locale` | A language surge, e.g. a new market, moves traffic towards weaker locales |
| Predicted-intent distribution (PSI) | event log `intent` | New request types, seasonal shifts, or a model starting to collapse onto one intent |
| Predicted slot-label frequency (PSI) | event log `slot_labels` | Reported, not a trigger: moves with the intent mix |
| Fallback (handoff) rate | event log `handoff` | Rising handoffs mean the model is less sure, or traffic left its domain |
| Evidently data-drift report | offline batches | Per-column drift tests, including utterance length (not in the live log) |

The event log holds only the allow-listed fields (`logging.allowed_fields`): no message text and no slot values.
Utterance length is not logged; adding a character count to the allow-list would be a data-minimisation policy
change and needs a separate decision.

Recommended cadence: weekly, and after any release or marketing change that could move traffic.

## Triggers (`configs/project.yaml` → `retraining`)

A retraining review starts when, over **at least 1,000 utterances**:

1. PSI of the locale distribution **> 0.25**, or
2. PSI of the predicted-intent distribution **> 0.25**, or
3. the fallback rate is **≥ 2×** the baseline (the held-out dev fallback rate of the deployed model, not the training
   rate, because the model is over-confident on its own training data).

Below 1,000 utterances the report says "not enough data" and nothing fires. A trigger starts a review; it does not
start training by itself. The review checks whether the cause is a real distribution change, a bug (for example a
broken language hint), or an expected event.

## What a retrain uses

- The frozen MASSIVE splits (`data/splits/checksums.json`) and the authored out-of-scope data, as now.
- New data only from a documented, consented and reviewed collection. Conversations are not stored (in-memory
  tracker, no text in logs), so live traffic cannot become training data, by design.
- Hyper-parameters from `reports/optuna_study.md` unless the review justifies a new study.

## Promotion gates (all required)

1. Full per-locale evaluation on the test split (`python -m src.models.evaluate`), with results in
   `reports/metrics.json`.
2. Fairness re-audit: no locale more than 10 pp below the mean (NFR-2), compared with the current model locale by
   locale.
3. Calibration and fallback rerun (`python -m src.models.fallback`); the new energy threshold is signed off by a
   person before it goes into `fallback.threshold`.
4. Every CI gate green (`.github/workflows/ci.yml`), including `tests/test_metrics_gates.py`. A target the old model
   missed may stay in `targets.known_misses` only with the new real value; a drop below the recorded value fails.
5. The scripted conversations (`python -m src.dialogue.evaluate`) do not lose task completion.
6. ONNX export matches PyTorch (`python -m src.models.export_onnx`) and the latency benchmark stays under 300 ms.
7. **Human approval**, recorded in `PROJECT_STATUS.md` with the date and the numbers above.

## Versioning

- Each training run has its own name and folder (`artifacts/runs/<run>/best`, `artifacts/onnx/<run>/`) and its MLflow
  run.
- `models.deployed_checkpoint` in `configs/project.yaml` names the deployed run. The serving logs and the `/health`
  endpoint report it as `model_version`, so every logged event can be traced to the model that produced it.
- A promotion is a git commit that changes `models.deployed_checkpoint`, the fallback threshold and the recorded
  results together, tagged `model-<run>`.

## Rollback

- Keep the previous run's `artifacts/onnx/<run>/` until the new model has run for at least one monitoring period.
- To roll back: set `models.deployed_checkpoint` (and `fallback.threshold`/`temperature`) back to the previous
  commit's values, and restart the NLU service (`docker compose up -d nlu`). No retraining is needed.
- Roll back if, after promotion, the fallback rate doubles, a locale falls more than 10 pp below the mean on the next
  evaluation, or the scripted conversations lose task completion.
