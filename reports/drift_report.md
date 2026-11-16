# Drift report (Phase 11)

FeastFleet is a FICTIONAL demo. Reference: TRAIN split with the deployed model's predictions (115,140 utterances). Fallback-rate baseline: DEV split (22.1%), because the model is over-confident on its own training data. The drift batch is **SYNTHETIC**.

Triggers (`configs/project.yaml` → `retraining`): PSI > 0.25 on locale or intent over at least 1,000 utterances, or a fallback rate ≥ 2.0× the baseline. Slot-label PSI is reported but is not a trigger.

| Batch | n | PSI locale | PSI intent | PSI slot labels | Fallback rate | Evidently drifted columns | Triggers fired |
|---|---|---|---|---|---|---|---|
| normal (test sample) | 5,000 | 0.0007 | 0.0278 | 0.0211 | 22.0% | 0/4 | none |
| drift (SYNTHETIC Swahili surge) | 5,000 | 0.8831 | 0.0268 | 0.0157 | 22.9% | 1/4 | PSI locale > 0.25 |

## Live event log

`logs/nlu_events.jsonl`: 567 events; PSI locale 0.7163, intent 6.2383, slot labels 5.2514; fallback rate 50.1%. **Not enough data** for a decision (fewer than 1,000 events; the log so far holds only test and demo traffic).

Evidently HTML reports: `reports/monitoring/evidently_*.html` (columns: locale, predicted intent, characters, predicted slot count). The live log has no utterance length: length is computed offline from the splits only.
