# Project Status

## Current phase

Phase 0 (setup and requirements): **done**, pending team confirmation of the decisions below.
Phase 1 (data acquisition and EDA): **done.**
Phase 2 (ethics audit and privacy design): **done**, AI-disclosure translations awaiting native-speaker review.
Phase 3 (NLU data pipeline): **done.**
Phase 4 (baselines and MLflow): **done.**
Phase 5 (joint model): **in progress.** XLM-R is the deployed model (Amharic decision below).

## Phase 5 evidence (so far)

| Command | Outcome |
|---|---|
| PyTorch install | First two attempts installed the CPU build (uv gives `--extra-index-url` priority over `--index-url`). Fixed with `--index https://download.pytorch.org/whl/cu130`: torch 2.14.1+cu130, CUDA available on the RTX 4060, bf16 supported. Pinned in `requirements.txt` |
| `pytest -q` | 26 passed (adds joint-model forward/loss, padding and span-decoding tests) |
| `python -m src.models.train --model xlm-roberta-base --run A --smoke` | Full pipeline works on GPU (400 examples, 1 epoch, 46 s); checkpoint loads in `python -m src.models.inference`. Each run writes a 1.1 GB `best/` and a 2–3 GB `last.pt` |
| mBERT Run A, epochs 1–2 (11:33–11:53) | 8.8 and 10.4 min per epoch; dev mean intent accuracy 0.550 → 0.579, slot F1 0.373 → 0.435 (Run A trains on 5 locales only, so 5 dev locales are zero-shot) |
| Interruption | The background job died during epoch 3 when the session restarted (no Python process left; MLflow run left as RUNNING). State after epoch 2 was saved in `last.pt` |
| Relaunch 17:14 | Detached from the session (`Start-Process`, unbuffered logs in `artifacts/logs/`): mBERT Run A `--resume` from epoch 3, then XLM-R Run A |

Training must not run while the laptop sleeps: keep it plugged in, lid open, and sleep disabled while plugged in.

Built during training (Phase 6, ready to run once Run A finishes): `src/models/evaluate.py` saves predictions per run and computes, from those files, per-locale intent accuracy, macro-F1, seqeval slot F1 and char-exact slot F1, the transfer gap, 10 pp fairness flags, McNemar tests vs both baselines, unseen/judge-clean test subsets, top confusions and an error sample. `tests/test_evaluate.py` (4 tests) passes; the report path was exercised on 20 smoke-model dev examples per locale into a scratch folder (real `reports/` untouched).

| mBERT Run A, epochs 3–5 (resumed) | ~3.9 min per epoch; best epoch 5: dev mean intent accuracy 0.576, slot F1 0.469, dev score 0.5225 |
| XLM-R Run A (17:27–17:53) | ~4.9 min per epoch; best epoch 5: dev mean intent accuracy 0.766, slot F1 0.620, dev score 0.6931 |
| `python -m src.models.evaluate --checkpoint <both Run A> --partition test` (once) | mBERT: intent acc 0.572, slot F1 0.459, transfer gap 68.1 pp, 5 locales >10 pp below mean. XLM-R: intent acc 0.759, slot F1 0.609, transfer gap 28.9 pp, 3 locales flagged (ar, sw, am). am-ET zero-shot: mBERT 0.028 vs XLM-R 0.557. ja-JP XLM-R slot F1 0.726 token vs 0.620 char-exact (tokenizer effect). Unseen/judge-clean subsets change accuracy by < 1 pp except XLM-R ar-SA (+3 pp judge-clean). Caveat: mBERT Run A is significantly worse than the bag-of-embeddings baseline, which trained on all ten locales; the baseline comparison belongs to Run B. Full tables: `reports/evaluation_report.md` |
| Optuna, 17:56–19:06 (detached) | 10 trials, XLM-R, Run B setup, 25% of train, dev-scored. Finished trials: 0.740, 0.641, 0.686, 0.702, 0.684, 0.698; trials 5, 7, 8, 9 pruned. Best: trial 0, learning rate 1.96e-5, 5 epochs, slot loss weight 1.60. Every 2–3 epoch trial scored lower. `reports/optuna_study.md` |
| Run B launched 19:06 (detached) | XLM-R then mBERT, both with the tuned settings; logs `artifacts/logs/xlmr-runB.log`, `mbert-runB.log` |
| XLM-R Run B (19:06–20:12) | ~9 min per epoch (epoch 4 took 28 min while Epic Games/Steam shared the GPU). Best epoch 5: dev intent accuracy 0.867, slot F1 0.741, dev score 0.8037. `artifacts/runs/xlm-roberta-base-runB/best` is the deployed model |
| `python -m src.models.fallback --checkpoint <XLM-R Run B> --device cpu` | Temperature 1.38; ECE 0.074 → 0.020. Recommended threshold 0.94: tune routing 96.4%, **held-out routing 87.3% (misses the 95% NFR-3 target)**, at the cost of handing off 35.8% of in-scope dev inputs (accuracy when answered 97.3%). Weakest held-out categories: adversarial 60%, unsupported language 67%. Dev hand-off by locale ranges from 31.7% (ja-JP) to 43.1% (ar-SA). `reports/fallback_report.md`. Threshold not yet signed off |

| Score comparison (rerun of `src.models.fallback`) | Chosen on tune + dev only: max_prob 0.94 (dev answered 64.2%, held-out 87.3%), margin 0.93 (61.2%, 89.1%), **energy 7.3 chosen** (72.0%, **held-out 89.1%**; accuracy when answered 96.3%). Unsupported-language items now 100% routed; remaining misses: adversarial 6/10 routed (explicit "let me talk to a person" requests), support out-of-domain 23/25. **NFR-3 (95%) still missed.** Recommended rule not yet signed off; `fallback.threshold` in config left unset |

| mBERT Run B (20:12–20:56) | ~7–10 min per epoch; best epoch 5: dev intent accuracy 0.779, slot F1 0.661, dev score 0.7197 |
| `python -m src.models.evaluate --checkpoint <both Run B> --partition test --device cpu` (once) | **XLM-R Run B: intent accuracy 0.863 (NFR-1 intent ≥ 0.85 met), slot F1 0.727 (≥ 0.75 missed by 2.3 pp), char-exact 0.717, transfer gap 3.3 pp, no locale > 10 pp below the mean (NFR-2 met).** mBERT Run B: 0.771 / 0.646, transfer gap 27.5 pp, am-ET 66.3 pp below the mean. `reports/evaluation_report.md` |

**Decision (user, 2026-11-16): add an out-of-scope class.**
- `data/oos_train/oos_train.json`: 200 authored sentences (20 per locale: 10 out-of-domain support, 6 human requests, 4 adversarial), deliberately avoiding the challenge set's topics and wording; `tests/test_oos.py` fails on any exact overlap. Non-English unreviewed.
- `train.py --oos` adds an `out_of_scope` intent (61 intents) and repeats the 200 items 5× (1,000 vs 115,140 MASSIVE examples). `fallback.py` sends any predicted `out_of_scope` straight to handoff, then applies the score threshold.
- CPU smoke test passed (61 intents saved; checkpoint loads). 14 related tests pass.
- The first `--oos` run (authored data only) was stopped at the user's request after the decisions below.

**Decisions (user, 2026-11-16):**
- The demo supports a fictional food-delivery business, **FeastFleet** (`configs/business.yaml`): it answers ordering and order-status requests (`takeaway_order`, `takeaway_query`) plus greetings, time and weather; other MASSIVE intents get "I can't help with that here"; out-of-scope or low-confidence messages go to a human.
- Out-of-scope data enlarged: `data/oos_train/food_delivery.json` (30 authored food-delivery support sentences per locale) plus 1,000 English messages from OrSabbach/food-delivery-support-tickets (MIT, synthetic; no real food-delivery chat data is public). `late_delivery` excluded; 363 external messages opening like a challenge item removed. Details: `data/oos_train/README.md`. 12 tests pass.
- XLM-R Run B with `--oos` (21:09–22:00): dev intent accuracy 0.866, slot F1 0.741, dev score 0.8032 (same as without the class).
- Fallback (`reports/fallback_report.md`): energy < 7.036 chosen on tune + dev; **held-out routing 90.9%** (was 89.1%), 50.9% of held-out items routed by the predicted `out_of_scope` intent alone; dev answered 77.9% (was 72.0%), accuracy when answered 95.2%; adversarial 70% (was 60%). **NFR-3 (95%) still missed.**
- All 5 held-out misses are predicted `general_quirky` (MASSIVE's catch-all): two "charged twice" requests (fr, hi) and three "you are useless, let me talk to a real person" (en, de, hi). Swahili, Amharic, Tamil, Arabic, Japanese and Spanish routed 100% (4–6 items each, so per-language figures are noisy). Translating the external data was therefore not done: the misses are not in low-resource languages.
- Test split (once): intent accuracy 0.860, slot F1 0.729, no locale > 10 pp below the mean; 25 of 29,740 in-scope test messages predicted `out_of_scope` (0.08%). Macro-F1 0.812 vs 0.829 mainly because the extra label enters the macro average.
- **Now the deployed model** (`models.deployed_checkpoint` in config). The energy threshold still needs human sign-off before it goes into `fallback.threshold`.
- I stopped iterating on the challenge set: the misses were seen on the held-out half, so further changes targeted at them would no longer give a fair held-out number.
- **Decision (user, 2026-11-16):** when the model predicts `general_quirky`, FeastFleet offers a human ("I can't help with that here, shall I connect you to an agent?") instead of a bare refusal (`offer_handoff_intents` in `configs/business.yaml`). Because this rule was chosen after seeing held-out misses, the model-level NFR-3 result stays reported as **90.9% (missed)**, and the system-level safe-handling rate will be reported separately with that caveat.

Phase 7 status: **done**. Threshold (energy < 7.036, temperature 1.3928) signed off by the user on 2026-11-16 and written to `fallback` in `configs/project.yaml`.

## Phase 8 (serving): in progress

| Step | Outcome |
|---|---|
| Language ID (`src/serving/language_id.py`) | Unicode script for am/ta/hi/ar/ja, fastText `lid.176.bin` (126 MB, CC BY-SA 3.0) for the rest. MASSIVE dev accuracy: en 99.6%, es 97.3%, de 97.7%, fr 98.5%, ja 99.9%, hi 100%, ar 96.8%, am 100%, ta 99.9%, **sw 66.8%** (short Swahili utterances look English). All 6 unsupported-language challenge items flagged. Mitigation: the client's language hint overrides detection. Two fastText quirks handled: NumPy 2 breaks `predict()`, and the native call needs a trailing newline |
| ONNX export (`src/models/export_onnx.py`) | fp32 1,111 MB, matches PyTorch exactly (max intent-logit difference 3e-5, 100% argmax agreement). Default INT8 (278 MB) agreed only 90.5% (intent) / 92.3% (slot); on test it scored intent 0.854, slot F1 0.707 (−0.6 / −2.2 pp vs PyTorch). Re-exporting with per-channel INT8 on MatMul only, heads excluded |
| FastAPI (`src/serving/app.py`, `create_app` factory) | `/predict` with language hint, empty/unsupported handoff, energy rule, allow-list event log (`handoff`, `handoff_reason` added to allowed fields). `tests/test_serving.py` (3 tests) proves no raw text or slot values reach the log |
| Latency (`src/serving/benchmark.py`) | Written; runs after the re-export |

Docker Desktop installed by the user (2026-11-16); laptop restart pending.

Built during training (Phase 7, ready to run on the deployed model):
- `data/challenge_set/challenge_set.jsonl`: 110 authored out-of-scope inputs (50 support requests outside MASSIVE's domains, 20 adversarial, 20 mixed-language across all ten languages; plus gibberish, empty, symbols, very long, and 6 unsupported languages), split 55 tune / 55 held-out within each category. Chit-chat excluded because MASSIVE has chit-chat intents. Non-English items unreviewed. `tests/test_challenge_set.py` (3 tests).
- `src/models/fallback.py`: temperature scaling on dev, ECE and reliability diagram, threshold chosen on dev + tune half (highest dev coverage among thresholds routing ≥ 95%), held-out routing per category, dev fallback rate per locale. The threshold is written as a recommendation for human sign-off. `tests/test_fallback.py` (4 tests). Not yet run end to end (needs the deployed model).

## Phase 4 evidence

| Command | Outcome |
|---|---|
| `uv pip install mlflow scikit-learn safetensors` | mlflow 3.18.0, scikit-learn 1.7.2, safetensors 0.8.0 (pinned) |
| `python -m src.models.baselines --only majority` | Logged to MLflow (`mlruns/mlflow.db`, experiment `baselines`). Test accuracy 0.070 and macro-F1 0.002 in every locale (dev mean 0.064): one intent for all inputs; identical across locales because the data is parallel |
| `pytest -q` | 23 passed (adds majority, mean-pooling and per-locale mean tests) |
| mBERT `model.safetensors` download (user approved, 714 MB) | Cached in the Hugging Face cache (`~/.cache/huggingface`) |
| `python -m src.models.baselines` (first run) | **Failed** after training: MLflow rejects `=` in parameter names. Exit code was hidden by a shell pipe. Fixed the name; the failed run stays in MLflow marked FAILED |
| `python -m src.models.baselines` (rerun, 10:32–10:50, 18 min) | bag-of-embeddings: test mean accuracy **0.630**, macro-F1 0.592 (dev 0.637); C = 0.1 chosen on dev (0.6375 vs 0.6307 for C=1, 0.6261 for C=10). sklearn warned that lbfgs did not fully converge in 1,000 iterations, and the best C is at the edge of the grid, so this baseline is not fully tuned |

Per-locale bag-of-embeddings test accuracy: en-US 0.763, es-ES 0.725, ja-JP 0.724, fr-FR 0.719, de-DE 0.707, hi-IN 0.676, sw-KE 0.652, ta-IN 0.632, ar-SA 0.626, **am-ET 0.075** (no better than the majority baseline).

**Finding: mBERT cannot read Amharic.** `python -m src.data.check_alignment` now reports unknown-token rates: mBERT maps **97.2%** of am-ET tokens to `[UNK]` (Amharic is not among mBERT's pretraining languages, and its vocabulary lacks the Ethiopic script). Every other locale is at most 0.3% for mBERT, and XLM-R is 0.0% for all ten. A fine-tuned mBERT will fail on am-ET for the same reason, so NFR-2 cannot be met with mBERT if am-ET stays in the language set.

Design: the bag-of-embeddings baseline averages mBERT's static word-piece embeddings (no extra model download beyond the mBERT weights Phase 5 needs) and trains logistic regression on all ten locales' train split, with C chosen on dev.

## Phase 3 evidence

| Command | Outcome |
|---|---|
| `python -m src.data.prepare` (run twice) | 60 intents, 111 slot tags (O + B/I for 55 types); 0 malformed records in any locale; identical checksums on both runs |
| `pytest -q` | 20 passed: span extraction (incl. ja-JP), BIO alignment on synthetic offsets, lost/ragged-span counts, PII scrub of a synthetic conversation (no leaks), checksum match against `data/splits/checksums.json` |
| `uv pip install transformers` + tokenizers for both models (user approved, ~18 MB) | transformers 5.20.2, tokenizers 0.23.3; both load as fast tokenizers with character offsets |
| `python -m src.data.check_alignment` | All 165,210 examples align for both tokenizers. Lost/ragged slots are 0 everywhere except ja-JP (mBERT 3.53% ragged; XLM-R 13.97% ragged, 0.12% lost) and 1 sw-KE slot. Max length 149 tokens (mBERT) / 113 (XLM-R) → `training.max_length: 160` |

Evaluation decision from this: headline slot F1 = seqeval entity-level on token tags; character-exact F1 and per-tokenizer ceilings reported as secondary (`evaluation` in config), so XLM-R is not penalised for its Japanese tokenizer.

Design decisions:
- Slot labels come from character spans in `utt`, then each subword token is tagged by its start offset (B-/I-/O, -100 for special tokens). Word-based labelling cannot work for ja-JP, which has no spaces.
- Test subsets saved in `data/splits/test_subsets.json`: test IDs seen in train (21–237 per locale) and judge-flagged test IDs (0–373 per locale), for the Phase 6 sensitivity checks.
- PII scrubber: predicted personal-data slots plus regex. spaCy NER dropped (no trained pipelines for sw, am, ta); policy and guide updated.

## Phase 2 evidence

| Command / file | Outcome |
|---|---|
| `python -m src.privacy.pii_audit` | `reports/pii_audit.md`: ~18% of utterances per locale contain a personal-data slot (mostly `person`, `place_name`); 0 emails in `name@domain` form and 0 runs of 6+ digits in any locale |
| `reports/data_minimisation_policy.md` | Names every stored field; raw text and slot values never stored; scrubber is defence in depth; Rasa must use the in-memory tracker store and no DEBUG logging |
| `configs/disclosure.yaml` | AI disclosure in all ten languages; nine are machine-written and marked `unreviewed` |
| `reports/data_card.md` | Draft: subset, representation, domain limitation, personal data, retained fields |
| `pytest -q` | 9 passed (adds PII-audit pattern tests and disclosure coverage) |

Key finding: MASSIVE is virtual-assistant data (alarms, music, weather...), not customer-support traffic. Recorded as a limitation in the data card; results must not be presented as real support performance.

## Phase 1 evidence

| Command | Outcome |
|---|---|
| `curl` download of `amazon-massive-dataset-1.1.tar.gz` (user approved) | 40,251,390 bytes, SHA-256 `4cba5faa…0491577`, recorded in config |
| `python -m src.data.download` | Checksum verified; extracted with the safe `data` filter to `data/raw/1.1/` (52 locale files, LICENSE = CC BY 4.0) |
| `python -m src.data.eda` | 165,210 utterances, 60 intents, 55 slot types; writes `reports/dataset_report.md`, `reports/dataset_stats.json`, `reports/figures/utterance_length.png` |
| `pytest -q` | 6 passed (Phase 0 checks + slot-markup parser tests) |

Findings (details in `reports/data_quality_issues.md`):
- Every locale: 11,514 / 2,033 / 2,974; IDs and partitions identical across all ten locales; no malformed markup or missing values.
- Issue 1: 0.7% (en-US) to 8.0% (ar-SA) of test utterances also appear verbatim in train; kept, reported as a sensitivity metric.
- Issue 2: annotators flagged 12.3% of ar-SA and 5.5% of ta-IN intents as wrong; fairness results must separate label noise from model weakness.
- Issue 3: intents range from 4 to 810 training examples (202x) in every locale.
- Plan corrections: Run B needs no language rebalancing (locales already equal-sized); guide Phase 3 leakage step and Phase 6 sensitivity step updated.

## Environment (recorded 2026-11-16)

| Item | Value |
|---|---|
| OS | Windows 11 Home Single Language |
| CPU | Intel Core i9-13980HX, 24 cores / 32 threads |
| RAM | 15.6 GB |
| GPU | NVIDIA GeForce RTX 4060 Laptop, 8 GB |
| Free disk (C:) | 570 GB |
| Project Python | 3.10.22 (installed with uv, venv in `.venv/`) |
| Git | 2.56.0 |
| Docker | **Not installed** |
| Internet | Available; MASSIVE 1.1 archive URL returns HTTP 200 |

Notes:
- The local RTX 4060 can likely train mBERT/XLM-R base without Colab; Colab/Kaggle stay as backup. Confirm memory use in the Phase 5 smoke run.
- This laptop is much stronger than the spec's 4-core reference. Latency (NFR-4) must be measured with ONNX Runtime limited to 4 threads, or the result will flatter the model.

## Phase 0 evidence

| Command | Outcome |
|---|---|
| `python -m pip install --user uv` then `python -m uv python install 3.10` | uv 0.13.8; CPython 3.10.22 installed (uv printed a harmless error about a minor-version link; the interpreter runs) |
| `git init -b main` | Empty repository created |
| `python -m uv venv --python <3.10 path> .venv` | Python 3.10.22 venv |
| `uv pip install pyyaml pytest pandas numpy matplotlib seaborn` | Installed; exact versions pinned in `requirements.txt` |
| `.venv/Scripts/python.exe -m pytest -q` | 2 passed (ten unique locales; every OBJ/FR/NFR/ETH ID traced in `reports/requirements.md`) |
| Fresh venv in a temp folder, `uv pip install -r requirements.txt`, `pytest` | Installs with one command; 2 passed |

## Files created

Phase 0: `.gitignore`, `README.md`, `requirements.txt`, `configs/project.yaml`, `reports/requirements.md`, `tests/test_phase0.py`, `PROJECT_STATUS.md`.
Phase 4: `src/models/baselines.py`, `tests/test_baselines.py`, `reports/baselines.md`, `artifacts/predictions/` (git-ignored), `mlruns/mlflow.db` (git-ignored); unknown-token column added to `reports/alignment_report.md`.
Phase 3: `src/data/prepare.py`, `src/data/check_alignment.py`, `src/privacy/pii_scrubber.py`, `tests/test_prepare.py`, `tests/test_pii_scrubber.py`, `tests/test_splits.py`, `data/splits/labels.json`, `data/splits/checksums.json`, `data/splits/test_subsets.json`, `reports/alignment_report.md`; `training` and `evaluation` sections in config; `data/processed/` git-ignored.
Phase 2: `src/privacy/pii_audit.py`, `tests/test_pii_audit.py`, `tests/test_disclosure.py`, `configs/disclosure.yaml`, `reports/pii_audit.md`, `reports/data_minimisation_policy.md`, `reports/data_card.md`; `privacy.pii_slot_types` added to `configs/project.yaml`.
Phase 1: `pytest.ini`, `src/data/load.py`, `src/data/download.py`, `src/data/eda.py`, `tests/test_load.py`, `data/README.md`, `reports/dataset_report.md`, `reports/dataset_stats.json`, `reports/figures/utterance_length.png`, `reports/data_quality_issues.md`.

Nothing is committed yet.

## Decisions needing team confirmation

| Decision | Proposed | Status |
|---|---|---|
| Ten locales | en-US, es-ES, de-DE, fr-FR, ja-JP / hi-IN, ar-SA / sw-KE, am-ET, ta-IN | Proposed (`languages.status: proposed` in config) |
| Training design | Run A on high-resource locales; Run B on all ten (already equal-sized) | Proposed |
| Rasa | Rasa Open Source 3.6.21 in Docker (`rasa/rasa:3.6.21-full`), action server `rasa/rasa-sdk:3.6.2` | Proposed |
| Rasa integration | Custom component calling the FastAPI NLU service | Proposed |
| Language ID | fastText `lid.176.ftz` | Proposed |
| CI gates | Gate on committed `reports/metrics.json`; CI smoke fine-tune only checks the pipeline | Proposed |
| Amharic vs mBERT | Keep am-ET; deploy XLM-R; mBERT still trained and evaluated (Run A and Run B) | **Decided by user, 2026-11-16** (`models.deployed` in config). Report must state the deviation from EO-3 ("Rasa + mBERT NLU") |

## Blockers

| Blocker | Needed by | Action |
|---|---|---|
| Disclosure translations unreviewed | Phase 9 demo | A fluent speaker per language checks `configs/disclosure.yaml` and sets `review_status` to `native-reviewed` |
| Docker Desktop not installed | Rasa spike (week 8), Phase 10 | Team member installs Docker Desktop (with WSL 2) before week 8. Until then Phases 1–8 are unaffected. |

## Changelog

- 2026-11-16: Phase 0 completed. Python 3.10.22 chosen to match Rasa 3.6's limit (`>=3.8,<3.11`).
- 2026-11-16: Phase 4 completed. Found mBERT cannot tokenise Amharic (97.2% `[UNK]`). User decided: keep am-ET, deploy XLM-R, keep training mBERT for comparison.
- 2026-11-16: Phase 1 completed. Official splits kept despite text overlap; overlap and annotator-flag effects will be reported as sensitivity checks, not filtered out.
