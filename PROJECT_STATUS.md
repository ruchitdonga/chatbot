# Project Status

## Current phase

Phase 0 (setup and requirements): **done**, pending team confirmation of the decisions below.
Phase 1 (data acquisition and EDA): **done.**
Phase 2 (ethics audit and privacy design): **done**, AI-disclosure translations awaiting native-speaker review.
Phase 3 (NLU data pipeline): **done.**
Phase 4 (baselines and MLflow): **done.**
Phase 5 (joint model): **in progress.** XLM-R is the deployed model (Amharic decision below).
Phases 6–10: **done** (Docker Hub push pending). Phase 11: **done** (CI green on main). Phase 12: not started.

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
| Gentler INT8 (per-channel, MatMul only, heads fp32) | 856 MB; test intent 0.855, slot F1 0.713 (−0.5 / −1.6 pp). Still a real loss |
| Latency (`python -m src.serving.benchmark`, 4 threads, 300 test utterances) | INT8: 6.0 ms median. **fp32: 14.6 ms median (model), 17.2 ms (full /predict); NFR-4 (≤ 300 ms) met** |
| Decision | Serve **fp32 ONNX** (`serving.quantized: false`): no accuracy loss and still ~20× under the latency target. Quantisation results kept in the reports |
| Live smoke test (real model + language ID) | en/sw (hint)/ja food orders → `takeaway_order` with correct food slots; English and Hindi delivery complaints → `out_of_scope` handoff; Russian → unsupported-language handoff; empty → handoff. Log lines contain only allowed fields |
| `pytest -q` | 45 passed |

**Phase 8: done.**

Docker: the engine first failed because WSL was registered but broken (`wsl --version` timed out). The user reinstalled WSL (`winget install --id Microsoft.WSL`, version 3.0.5) and restarted. Docker engine 29.9.3 now runs (linux/amd64, 8 GB for containers). Pulling `rasa/rasa:3.6.21-full` and `rasa/rasa-sdk:3.6.2` for Phase 9.

## Phase 9 (Rasa dialogue for FeastFleet): in progress

Rasa 3.6.21 and the action server (rasa-sdk 3.6.2) run in Docker (`docker-compose.yml`, REST on `127.0.0.1:5005` only); the NLU service still runs on the host until Phase 10 adds it as a container.

| Step | Outcome |
|---|---|
| Custom NLU component (`rasa/components/feastfleet_nlu.py`, `GraphComponent` registered with `DefaultV1Recipe.register`) | Calls `POST /predict` (optional `metadata.language` hint passed through). Maps service handoff `out_of_scope` → `out_of_scope`; any other handoff (energy rule, empty, unsupported language) → `nlu_fallback`; `configs/business.yaml` intents unchanged; every other MASSIVE intent → `unsupported_request`. Service down or bad response → `nlu_fallback` (hand off, never guess). Only `food_type` enters the tracker, so `person`/`place_name` values are never stored. In-container self-check passes |
| **Deviation: no `FallbackClassifier`** | The signed-off Phase 7 rule is energy-based and already applied in the service; a probability threshold in Rasa would be a second, unvalidated rule. Recorded in `rasa/config.yml` |
| Language slot | Detected locale passed as parse field `feastfleet_locale`; custom slot mapping (`action_validate_slot_mappings`) keeps the **first** detected language, because short follow-ups ("pizza", "FF-1001") are often misdetected |
| Forms (FR-2) | `takeaway_order_form` (asks `food_type`), `takeaway_query_form` (asks `order_id`). Short answers fill the slot even when low-confidence; an explicit `out_of_scope` message leaves the form and hands off |
| Mock backend (`rasa/actions/actions.py`) | In-memory dict, two demo orders (FF-1001, FF-1002) plus orders placed while running; labelled mock in code and in every reply. Order-number parsing accepts `ff 1001` and Arabic-Indic digits (self-check passes) |
| AI disclosure (ETH-4) | First bot message, in the detected language: one `conversation_start` rule per entry intent (RulePolicy picks the longest matching rule; `rasa train` found no contradictions) |
| Replies (FR-4) | 14 responses × 10 languages as conditional variations on `language` (English = default, also used for unsupported languages). Non-English replies machine-written by an AI assistant, **unreviewed**. `tests/test_rasa_domain.py` (3 tests): all ten locales per response, disclosure identical to `configs/disclosure.yaml`, same placeholders in every language |
| `rasa test core --e2e --stories tests` | **20/20 stories, 85/85 actions** in en, es, de, hi (successful task, missing slot, unknown intent, fallback/out of scope, complaint inside a form, disclosure only once). Run end to end: 35 calls reached the live NLU service. Test sentences were checked against the model before writing, so this tests dialogue wiring, not model accuracy. (Without `--e2e`, `rasa test core` never calls NLU and uses the annotated intents.) |
| Live REST conversations | es, sw (with hint), hi, ja, de, en, ru: disclosure first in the right language, slot asked and filled, mock order placed and looked up, mid-form complaint handed off (de), Russian handed off as unsupported. No user text in Rasa or action-server logs (INFO level) |
| `pytest -q` | 48 passed |

Findings:
- **Greetings were handed off.** "hello", "hi there", "good morning", "bonjour", "buenos días", "guten morgen" are all predicted `general_greet` (0.66–0.85) but fall below the signed-off energy threshold, so the bot said "connecting you to a human" to a plain greeting.
  **Decision (user, 2026-11-16): exempt `general_greet`.** `low_confidence_exempt_intents: [general_greet]` in `configs/business.yaml`; the component answers a predicted `general_greet` even when the service's reason is `low_confidence` (never for `out_of_scope`, empty or unsupported language). Dialogue-level rule like the `general_quirky` offer: the threshold and the model-level NFR-3 figure (90.9%) are unchanged. Risk: a non-greeting misread as a low-confidence greeting now gets a greeting ("I can help you order food…") instead of a human. Retested: `rasa test core --e2e` **23/23 stories, 94/94 actions** (adds greeting stories in en, es, de).
- Swahili without a client hint is detected as English ("nataka kuagiza pizza" → en-US): replies come in English. The REST `metadata.language` hint fixes it.
- `affirm`/`deny` exist only as buttons on the "shall I connect you?" offer: MASSIVE has no yes/no intent, so a typed "yes" is not understood.
- Mock backend has no ownership check: any conversation can look up any order number (a Japanese test conversation looked up the Spanish one's order). A real backend must scope orders to the user.
- The service returns HTTP 500 on text with lone UTF-16 surrogates (fastText rejects it); the component turns this into a handoff.

### Scripted conversation evaluation (`python -m src.dialogue.evaluate`, 2026-11-16)

64 conversations / 89 turns in all ten languages plus two unsupported ones (`data/dialogue_eval/scripted_conversations.yaml`), **authored before running and not tuned afterwards**; non-English unreviewed. Replies are scored by response name from the Rasa tracker (`rasa run --enable-api`, localhost only, evaluation only). A conversation counts as completed only if every turn matches, in the right language, with the disclosure first. `tests/test_dialogue_eval.py` (2 tests). Full tables: `reports/dialogue_eval.md`.

| Measure | Result |
|---|---|
| **Task completion** (order / order-status) | **27/35 (77%)** |
| All conversations completed | 51/64 (80%) |
| Turns correct | 72/89 (81%) |
| Disclosure first | 64/64 (100%) |
| By language (completed) | es, ar, am, unsupported 100%; de, hi 83%; ta 80%; en 70%; fr, sw 67%; **ja 50%** |

Failed-turn analysis: **17 failed turns, fewer than the guide's 20.** All 17 are analysed below. No conversations were added to reach 20, because adding them after seeing results would no longer be blind. Model predictions were looked up afterwards for each failed text:
- **Correct intent, handed off by the energy rule: 12 turns** (`takeaway_order` ×7 in en, fr, ja, hi; `play_music` ×3 in de, ja, ta; `iot_hue_lighton` fr). Energies 5.9–7.0 against the 7.036 threshold. This is the signed-off threshold's coverage cost (dev answered 77.9%) seen in dialogue: safe, but it hands off orders it understood. Japanese is hit hardest (3 of 3 order turns).
- **Cascade: 4 turns** (en, fr, ja order turn 2; sw status turn 2). The first turn was already handed off, so no form was active and the bare answer ("chicken biryani", "FF-1001") was itself low-confidence. Not independent errors.
- **Wrong intent: 2 turns.** "can i get a large pepperoni pizza delivered" → `takeaway_query` (asked for an order number instead of placing the order). Swahili "oda yangu iko wapi" (with hint) → `email_querycontact`.
- **Dialogue bug: 1 turn, the most serious.** In the middle of an order, "actually let me talk to a real person" was low-confidence `general_quirky` → `nlu_fallback`. The form's `from_text` mapping took it as the food and **placed an order for "actually let me talk to a real person"** instead of handing off. Cause: short slot answers are also `nlu_fallback`, so the form accepts any `nlu_fallback` text. Not fixed yet (needs a decision).
- **Wrong language: 1 turn.** Swahili without a hint was detected as English; the order itself completed (known; client hint fixes it).
- No slot-fill loops occurred; every unsupported-language message was handed off.

**Fix (user, 2026-11-16): the order form no longer accepts free text.** `food_type` is filled only from a tagged `food_type` entity (any intent except `out_of_scope` while the form asks); a low-confidence answer without a tagged food leaves the form and hands off (new rule in `rasa/data/rules.yml`). Regression story added: `rasa test core --e2e` **24/24 stories, 100/100 actions**.

Rerun of the scripted evaluation after the fix (the set is no longer blind for this change, so the first run above stays the headline):

| Measure | Before fix | After fix |
|---|---|---|
| Task completion | 27/35 (77%) | **24/35 (69%)** |
| Turns correct | 72/89 (81%) | 70/89 (79%) |

The bug is gone ("let me talk to a real person" now hands off). The cost: three bare food answers the slot tagger did not tag as food, "döner" (de), "बिरयानी" (hi), "شاورما" (ar), are now handed off instead of ordered. Every failure after the fix is a handoff to a human; no conversation now produces a wrong action. Trade-off accepted for now: a missed order reaches a person, while a wrongly placed order does not.

Phase 9: **done.**

## Phase 11 (monitoring, retraining policy, CI): **done** (CI green on main, 2026-11-17)

| Step | Outcome |
|---|---|
| Reference profile (`src/monitoring/drift_report.py` → `reports/monitoring/reference_profile.json`) | Train split (115,140 utterances) with the deployed model's predictions: locale, predicted intent, predicted slot labels, length. Fallback-rate baseline from **dev (22.1%)**, not train (14.5%): the model is over-confident on its own training data, so a train baseline would fire the "fallback doubled" trigger on normal traffic. `OnnxNLU.predict_batch` added (identical output to `predict`; `predict` now calls it) |
| Batches | Normal: 5,000 random test utterances. Drift: **SYNTHETIC** Swahili surge (50% sw-KE), labelled synthetic everywhere |
| Results (`reports/drift_report.md`) | **Normal: PSI locale 0.0007, intent 0.028, fallback 22.0%, Evidently 0/4 columns drifted, no trigger. Swahili surge: PSI locale 0.88 → trigger fired, Evidently 1/4 (locale).** Fallback rate in the surge 22.9%: Swahili is not handed off more often, so only the PSI trigger fires. Live event log: 562 events → "not enough data" (< 1,000), as designed |
| Evidently | 0.7.23 installed and pinned (user approved). `DataDriftPreset` HTML reports `reports/monitoring/evidently_{normal,drift}.html` (3.8 MB each) |
| `reports/retraining_policy.md` | Triggers (PSI > 0.25 on locale/intent over ≥ 1,000 utterances, fallback ≥ 2× dev baseline), what a retrain may use (no live text, by design), 7 promotion gates ending in human approval, versioning via `models.deployed_checkpoint`/`model_version`, rollback without retraining |
| CI gates (`tests/test_metrics_gates.py`, 6 tests) | Decision (user, 2026-11-17): **pass on recorded misses**. Known misses recorded with real values in `configs/project.yaml` `targets.known_misses` (slot F1 0.7292, safe fallback 0.9090), not in `metrics.json` because `evaluate.py` rewrites it. A miss passes only if recorded and not below the recorded value; a recorded miss that is now met fails. Fairness gate recomputed from per-locale numbers. Verified: removing the recorded misses makes both gates fail |
| `.github/workflows/ci.yml` | CPU PyTorch 2.14.1, gates first, MASSIVE download (SHA-256 checked) + prepare, PII/fallback/logging tests, full pytest, smoke fine-tune with a tiny random-weight XLM-R (`optimum-intel-internal-testing/tiny-random-xlm-roberta`, 9 MB; 84 s locally, proves the pipeline only) |
| `pytest -q` | 63 passed (adds monitoring, gates, shop tests) |
| Remote | `origin` = private GitHub repo `ruchitdonga/chatbot` (user supplied, 2026-11-17) |

## Phase 10 (Docker deployment): done except the Docker Hub push

`docker compose up --build` starts the whole stack: `nlu` (FastAPI + ONNX Runtime + fastText), `actions` (mock backend), `rasa`. All ports bound to `127.0.0.1` (no service has authentication).

| Step | Outcome |
|---|---|
| `docker/Dockerfile.nlu` | `python:3.10-slim`, pinned `docker/requirements-nlu.txt`, no PyTorch, non-root user. **678 MB.** Model files mounted read-only at runtime (`artifacts/onnx`, `artifacts/models`), `logs/` mounted for the allow-listed event log. `.dockerignore` is an allow-list (code and configs only): build context 121 kB |
| Offline tokenizer | `export_onnx` now saves the tokenizer next to the ONNX model and `OnnxNLU` loads it from there (falls back to the hub name for older exports), so the container needs no Hugging Face download. Saved for the deployed model; output identical to the hub tokenizer on en/ja/am samples |
| `docker/Dockerfile.actions` | `rasa/rasa-sdk:3.6.2` + `rasa/actions` (mock backend). 344 MB |
| Rasa | Official `rasa/rasa:3.6.21-full`, project mounted; trains on start (trained models are git-ignored; no-op when unchanged), waits for the `nlu` health check. Pipeline URL now `http://nlu:8000/predict` |
| `requirements.txt` | Serving packages were never pinned: added onnx, onnxruntime, fastapi, uvicorn, fasttext-wheel, httpx at the verified versions |
| Smoke test in containers | `/predict` returns correct JSON (es pizza order → `takeaway_order`, `food_type` = pizza); es and sw scripted conversations complete; `rasa test core --e2e`: **24/24 stories, 100/100 actions**; event log has only allowed fields; no user text in any container log |
| **End-to-end turn time** (REST round trip through Rasa → NLU → actions, all 89 scripted turns, 4 NLU threads, this laptop) | **median 66 ms, p95 106 ms, max 119 ms; target ≤ 1 s met** |
| Clean-start simulation | Trained Rasa models moved away, images rebuilt with `--no-cache`, `docker compose up`: working German conversation **80 s** after the build started (includes Rasa training) |
| `pytest -q` | 50 passed |

On a truly clean machine the model files must exist first (git-ignored, 1.2 GB): run the training/export steps, or copy `artifacts/onnx/xlm-roberta-base-runB-oos/` and `artifacts/models/lid.176.bin`. Not tested on a second machine.

Not done: **pushing images to Docker Hub** publishes them, which needs team confirmation (guide step). The images contain code and configs only, no model or data.

### FeastFleet website with ordering (2026-11-17, user request; not in the guide)

Upgraded from the first demo page to a working storefront at `http://localhost:8080`:
- **Orders API** (`src/shop/app.py`, compose service `shop`, same image as `nlu`): menu (14 dishes, EUR cents), checkout, tracking. Orders in memory only, never logged; restarting `shop` clears them. Seeded FF-1001/FF-1002 keep the order-status flow working. `tests/test_shop.py` (5 tests): totals and free delivery over €30, cash on delivery, card, declined test card, validation, tracking never returns contact details, unpriced chat orders have no fee-only total.
- **Website** (`demo/app.js`, `chat.js`): menu with category filters, cart drawer (kept in localStorage), checkout with delivery or pickup, contact details, and payment by **card** or **cash on delivery / pay at pickup**, order confirmation with a status timeline (confirmed → preparing → on the way → delivered, simulated from order age), track-order page. Customer-facing "demo/mock" wording removed. Two markers stay on purpose: a footer line "FeastFleet is a fictional brand" and a **Test mode** badge on the card form (test card 4242…, decline card …0002). **Card data never leaves the page**: the number, expiry and CVC are validated in the browser (Luhn, expiry, CVC length) and only brand + last four digits are sent; card inputs have autocomplete off so browsers neither fill nor save real cards.
- **Assistant uses the same orders**: `action_place_order` creates a chat order (cash on delivery) and `action_check_order` reads the real status, so an order placed at checkout can be tracked in chat (verified: German chat tracked a pickup order placed on the site, "about 14 minutes"). If the API is unreachable the assistant hands off. Replies no longer say "demo" in any language; new reply `utter_order_delivered` (10 languages); the fake weather reply became "I can't check the weather here" (honest). All AI-written translations still unreviewed.
- Tested in the browser: add to cart, free-delivery threshold, declined card (message shown and scrolled into view), card payment → confirmation, pickup + pay at pickup, chat tracking. `rasa test core --e2e` 24/24, `pytest` 63 passed.

**Redesign (2026-11-17, user request):** the user found the site AI-generated-looking and rejected themed directions (signboard, railway, ticket wallet, tiffin) from an Impeccable direction round; decision: **"make it swiggy zomato"**, i.e. the Indian food-delivery app standard, recorded in `PRODUCT.md` (new: product truth for design work). Now: prices in **INR** (orders API in paise; ₹40 delivery, free above ₹499), Indian-first menu of 20 dishes with **veg/non-veg markers**, header search, category chips, dish rows with an emoji tile and an ADD/quantity control, an always-visible cart panel on desktop and a sticky "items · total · View cart" bar on phones, bill details (Item total, Delivery fee, To pay) in cart and checkout, +91 phone format. Emoji kept as dish pictures (user choice); all interface icons are drawn SVG. Checked in the browser at 1440 px and 375 px, no console errors; Impeccable detector: one false positive (CSS triangle used for the non-veg marker) suppressed for `demo/styles.css`; `pytest` 63 passed. Not run: Impeccable's finish-reviewer and documenter agents (no DESIGN.md yet).

**Assistant ordering and tracking fixed (2026-11-17, user request "a and check other commands too"):**
- Ordering in chat no longer creates unpriced cash-on-delivery orders with no address. `action_add_to_cart` matches the dish to the menu (`GET /api/menu/match`, aliases in Latin, Devanagari, Tamil, Arabic, Japanese and Ethiopic scripts, longest alias wins) and the website chat widget adds it to the real cart with a "View cart and check out" button; checkout takes address and card or cash on delivery. A dish not on the menu gets "Sorry, X isn't on our menu" (new replies `utter_added_to_cart`, `utter_not_on_menu`, ten languages, unreviewed). `/api/chat-orders` removed.
- Tracking: any message containing an order number (`FF-2016`, "मेरा ऑर्डर FF-1001 कहाँ है") becomes a tracking request with the number filled in (NLU component, `order_id` entity), except complaints, which still go to a person. Fixes the earlier "number typed again is handed off".
- Checked: component and actions self-checks; `rasa test core --e2e` **26/26 stories, 108/108 actions** (two new tracking stories); live chats through the website for every command (order named / asked / not on menu, Swahili with hint, tracking alone / inside a question / website order / unknown / repeated, greeting, time, weather, unsupported request, complaint with and without a number, person mid-order, Russian, "are you a robot" → Yes/No offer): all correct except a not-on-menu cheeseburger, handed off by the energy rule.
- Scripted evaluation (expectations remapped mechanically through the menu matcher; evaluator now ignores data-only bot messages): **task completion 24/35 (69%), turns 71/89 (80%)**, disclosure 64/64. The 16 remaining failures are the energy rule handing off messages the model understood.
- **Decision (user, 2026-11-17): `takeaway_order` and `takeaway_query` exempt from low-confidence handoff** (like `general_greet`; `configs/business.yaml`). Measured before adopting: none of the 55 held-out out-of-scope challenge items changes (still 50/55 routed, 90.9%; the model-level NFR-3 figure is unchanged). After: scripted **task completion 29/35 (83%), turns 79/89 (89%), conversations 54/64 (84%)**; three test-story turns ("pizza" as a short answer) now arrive as `takeaway_order` and were relabelled; `rasa test core --e2e` 26/26; `pytest` 64 passed. A not-on-menu burger now gets "not on our menu" in English and Hindi. Remaining misses include model errors, e.g. Hindi "मुझे बिरयानी चाहिए" predicted `weather_query` at 0.98.

**Store questions added; time and weather removed (2026-11-17, user request):**
- `datetime_query` and `weather_query` are no longer answered (not a food-delivery job): they get "I can't help with that here" like other MASSIVE intents. Rules, replies and `action_tell_time` removed; the four scripted weather/time conversations now expect `cant_help`.
- New store questions, detected by keyword in ten languages (`configs/faq.yaml`, AI-written, unreviewed) because the MASSIVE model has no intents for them: delivery fee, delivery time, payment methods (`utter_faq_*`), menu categories, vegetarian dishes and the price of a named dish (`action_menu_info`, live from the orders API). Order numbers still win (tracking).
- Complaints stay with a person: any message with a complaint word (76 words: refund, failed, deducted, wrong, late, allergy, person, … in several languages) is never turned into a store question. Store questions **do** override the model's `out_of_scope`, because the out-of-scope training data covered payment and allergy problems and the model sent plain "how can I pay?" to a person in 7 of 10 languages tested. Measured before adopting: **0 of the 110 challenge-set items** would be answered as a store question.
- Chat widget: fourth suggestion "How much is delivery?" in every language.
- Checked: component and actions self-checks; `rasa test core --e2e` **29/29 stories, 117/117 actions** (new: Hindi fee, English menu, Spanish payment, fee then order); 25 live questions through the website all correct (fees in en/hi/es/ja, payment in en/hi/ar/sw/de, time, menu in en/hi/ja, vegetarian, prices in en/hi/ja, weather/time now declined, three payment complaints still handed off); scripted evaluation unchanged (83% / 89%); `pytest` 64 passed.

**Hinglish and dish detection (2026-11-17, user request):**
- Romanised Hindi keywords for price, fees, time, payment, menu and veg (`configs/faq.yaml`), plus Hinglish tracking ("mera order kahan hai") and ordering ("mujhe biryani chahiye", "order karna hai"; also Devanagari "चाहिए"/"मंगवाना" and Tamil "வேண்டும்"). Ordering by keyword only fires when a menu dish is named ("mujhe help chahiye" still goes to a person). Hinglish complaint words added (paise wapas, galat, thanda, nahi mila, …).
- Replies in English for Hinglish: with no language chosen, a Latin-script message with two or more Hinglish marker words gets `language = en-US` (fastText read "samosa kitne ka hai" as Spanish). A language chosen in the chat always wins.
- The NLU component asks the orders API for the dish named in a message (`/api/menu/match` now returns the matched words) and marks it as `food_type` when the model's slot tagger missed it, for orders and short form answers; the add-to-cart action retries on the whole message when the tagged words name no dish ("butter masala" → Paneer butter masala).
- Checked: self-checks; `rasa test core --e2e` 29/29; live Hinglish/Hindi/Tamil checks (prices, cart, fees, payment, menu, veg, tracking, time, complaints and "I need help" to a person); with the NLU container down every message was handed off (safe fallback seen live); keyword topics answer **0 of 110** challenge-set items; scripted evaluation **task completion 32/35 (91%), turns 82/89 (92%), conversations 57/64 (89%)** (this set has now been run many times during development, so it is no longer a blind measure); `pytest` 64 passed.

**Human agent handoff (2026-11-17, user request "how is human supposed to answer the chat"):**
- When the assistant hands off (`utter_handoff`, `utter_order_not_found`; marked with `custom: {handoff: true}` in all 20 variations), the widget opens a chat in the orders API (`POST /api/handoffs`, with the widget transcript) and shows "Waiting for a person"; it switches to "Connected to a person" when an agent replies. Customer messages then go to the agent, not to Rasa.
- Support inbox at **http://localhost:8080/agent**: open chats with language, age and "Needs reply"; full thread (customer, assistant, agent); reply box; Close chat. Polls every 2-3 s.
- Close (by the agent, or the customer restarting/changing language) deletes the messages; the customer is told and goes back to the AI assistant with a new conversation. Text held in memory only, never logged; max 50 open chats; no agent login (localhost only). Policy: `reports/data_minimisation_policy.md`.
- Checked: `pytest` 66 passed (2 new handoff tests); live through the website: complaint → handoff → agent reply shown in the widget → customer reply shown in the inbox → agent closes → widget back to the assistant.

**Several dishes, typos and price wording (2026-11-17, user reports "whats the price for veg ulao" and "butter naan and ppav bhaji"):**
- Bugs found: dish names matched inside other words ("p**rice**" -> rice, German "P**reis**" -> reis); "what's the price for" was not a price phrase; only the longest dish name in a message was added to the cart.
- Fixes: English-letter dish names must be whole words; more price phrasings (`price for`, `the price`, `prices`, `cost of`, `how much for`); `/api/menu/match?all=true` returns every dish named and the add-to-cart and price actions use it; `typos=true` accepts a close spelling of a dish's own menu name ("ulao" -> pulao, "birynai"), used only once the message is known to be an order or price question.
- Measured: the first typo rule named a dish in 400 of 14,585 non-food MASSIVE test sentences (en/es/de/fr/sw), e.g. French "nouvelles" -> noodles; the adopted rule (dish names only, cutoff 0.85, no cut-off endings) names **0**. Store-question keywords still answer **0 of 110** challenge items.
- Checked: `pytest` 67 passed; `rasa test core --e2e` 29/29 stories, 117/117 actions; live: both reported messages, two-dish price, typos, burger (not on menu, shows categories), complaint still handed off.
- Follow-up (user: "fix it"): quantities written before a dish go to the cart ("2 dosa", "two butter naan", "3x lassi", Devanagari "२"; 1-20, one word allowed between, else 1) and the reply says "2 × Masala dosa". Swahili "wali" (rice) no longer counts in a message with Hinglish marker words ("spicy wali biryani"); a language-based rule was tried first and dropped because language ID reads "Nataka wali" as English. English order phrases ("i want", "i'd like", "can i get", "give me"; with a menu dish named, never with a complaint word) now count as orders: "I'd like 2 biryani please" had gone to a person (model: low confidence). Measured: **4 of 17,502** non-food MASSIVE test sentences (6 languages) become orders, all food-related (recipes, a bread price; 2 of them from the existing Hindi "चाहिए"); challenge set still **0 of 110**. Checked: `pytest` 67 passed; self-checks; `rasa test core --e2e` 29/29, 117/117; live: quantities in English and Hindi, wali in Swahili and Hinglish, refund still handed off, burger not on menu.

**Orders in every language (2026-11-17, user report: French and German two-dish orders lost quantities and variants, "its like this for all languages"):**
- Causes: plurals stopped matching after the whole-word fix ("Pizzen", "biryanis"); hyphens split names ("Chicken-Tikka-Pizzen"); the variant word was apart from the dish ("pizzas de pollo tikka", "Lamm-Biryanis", "biryani ya mbuzi") so a plain pizza or chicken biryani was added; quantities were read only right before the dish, in English words only.
- Fix (`src/shop/app.py`): ASCII names allow an `s`/`es` plural; hyphens count as spaces; variant words (chicken, pollo, poulet, Hähnchen, kuku, دجاج, チキン, …; lamb, Lamm, agneau, cordero, mbuzi, لحم, マトン) turn an adjacent pizza or biryani into the tikka pizza or mutton biryani, not across "and" in any of the languages, and name no dish alone; a number up to three words before the dish, in digits of any script or number words in en/fr/de/es/sw/hi, or after it where the language puts it there ("x2", Swahili "pizza tatu", Japanese "ピザを3枚"); Hindi "दो" after a dish is "give", so it is not read as 2.
- New test `test_orders_in_every_language`: 18 orders across all ten languages and Hinglish, written before the fix (2/18 passed then, 18/18 now). AI-written, not reviewed by native speakers.
- Measured: unchanged on 17,502 non-food MASSIVE sentences (95 name a dish before and after, 4 become orders, 0 typo-only dishes) and the challenge set (0 of 110). Checked: `pytest` 68 passed; `rasa test core --e2e` 29/29, 117/117; live in ten languages; the German order put 3 tikka pizzas and 2 mutton biryanis in the website cart.

**Every language checked (2026-11-18, user: "do it for every language, check every language"; started from a screenshot of "Nataka kuagiza Vada Pav" answered in English):**
- Language detection, all 29,740 MASSIVE test sentences with no language chosen. Before: Swahili **34.5% wrong** (603 read as English; 102 "unsupported", which hands the chat to a person), Arabic 3.5% (97 are English sentences inside the Arabic data), Spanish 2.4%, German 2.0%, French 1.5%, English 0.9%, Japanese 0.3% (kanji-only text such as "七百" was "unsupported"), Hindi 0.3%, Tamil and Amharic 0%.
- Fix in the detector (`src/serving/language_id.py`, before fastText): Swahili marker words (`configs/swahili_words.txt`, 691 words built by `python -m src.serving.swahili_words`: in at least 10 Swahili training sentences, in none of the other nine languages, not a Hinglish marker word) and short kanji-only text (up to 6 characters) as Japanese; longer kanji-only text is still left to fastText, since Chinese is not supported. After: Swahili **2.1%**, Japanese 0.1%, every other language unchanged (no new errors).
- Live chat, every language, with Auto-detect and with the language chosen (140 conversations: the four suggested phrases, a refund naming a dish, a biryani price and "2 biryani and a lassi"). First run 112/120: German "Wo ist meine Bestellung?" (a suggested phrase) and the two-dish orders in Japanese, Swahili and Amharic went to a person. Fixes in `configs/faq.yaml`: German tracking phrases; "I want / please" order words in every language (quiero, ich möchte, je veux, ください, أريد, nataka, እፈልጋለሁ; counted only with a menu dish named); complaint words for cold food, refunds and complaints in every language (the new order words had made "ich will mein Geld zurück für die Pizza" an order); Japanese and Amharic names for lassi. Final run **140/140**; every reply in the customer's language (6 price replies flagged by the detector are correct, e.g. "… biryani cuesta ₹289", read as English because of the dish name).
- Measured: challenge set still **0 of 110**; non-food MASSIVE test sentences turned into orders or tracking 7 of 29,170 (was 4; all food-related, e.g. recipes and bread prices).
- Also kept from earlier today: Swahili tracking keywords (oda yangu iko, …) and Swahili complaint words; "Oda yangu iko wapi?" (a suggested phrase) had gone to a person even with Swahili chosen.
- Checked: `pytest` 70 passed (new `tests/test_language_id.py`); `rasa test core --e2e` 29/29, 117/117. Word lists and test phrases are AI-written and not reviewed by native speakers.

**Gaps closed after "did you check everything?" (2026-11-18):**
- Scripted dialogue evaluation (first run since 2026-11-16): task completion **35/35 (100%)** (was 32/35), conversations 60/64 (94%), turns 85/89 (96%), disclosure 64/64. The 4 misses are off-topic requests ("play my favourite song") handed to a person instead of "I can't help", the safe direction. A rerun once showed 25/35: the demo orders FF-1001/FF-1002 aged with the orders service's uptime and read "delivered" after ~45 minutes; they now always read as 10 minutes old when looked up (`src/shop/app.py`, real orders unchanged).
- Second live check, every language with Auto-detect and with the language chosen, plus Hinglish (151 conversations: tracking with a number, an unknown number, tracking in two turns, menu, vegetarian, payment, delivery time). First run 131/151 after fixing the checker; fixed in `configs/faq.yaml` and the NLU component: tracking phrases ("where is my order") in every language, matched with the order number removed ("Oda yangu FF-1001 iko wapi"), so a complaint quoting its number still goes to a person; French/Arabic payment phrasings; Japanese/Swahili/Amharic delivery-time phrasings. Final **151/151**; the first check still **140/140**. New keywords change 0 of 29,170 non-food answers.
- Found and fixed: the payment keyword "upi" matched Swahili "upi" ("which"), so 14 Swahili test sentences ("wimbo unaocheza sasa ni upi") got the payment answer; now only UPI phrases ("pay by upi", "upi se", …).
- Browser, end to end: a Hindi chat order put 2 biryani + lassi in the cart, checkout with cash on delivery placed FF-2001, the Hindi chat tracked FF-2001; a test card (4242…) placed FF-2002 and the declined test card (…0002) showed the decline message; the checkout sends only card brand and last 4 digits (`demo/app.js`). Arabic handoff: complaint → inbox (detected language shown) → agent reply in Arabic, right-to-left → close → back to the assistant.
- Found and fixed: the chat widget's own texts (status line, queue/busy/closed/error notices, "View cart and check out", placeholders, suggestions) were English in every language. Now in all ten languages (AI-written, unreviewed), following the chosen language or, in Auto-detect, the conversation's language, which the assistant's first reply now carries (`custom: {lang}` on each `utter_disclosure` variation).
- Found and fixed: browsers kept an old `chat.js` after an update; nginx now sends `Cache-Control: no-cache` (files are rechecked, 304 when unchanged).
- Phone (375 px): store, chat, checkout, order page and support inbox have no sideways scrolling; the chat fills the screen; Arabic chat right-to-left with Arabic interface texts.
- Checked: `pytest` 70 passed; component self-check; `rasa test core --e2e` 29/29, 117/117.
- Still not covered: the store pages (menu, cart, checkout) are English only; no native-speaker review of any language; the second live check ran before the demo-order change (it only affects how old FF-1001 looks).

**Store in ten languages; translation review set up (2026-11-18, user: "the store pages ... are English only, and no native speaker has reviewed any of the languages. fix it"):**
- The whole store is translated: header, menu (categories and the 20 dish descriptions; dish names stay as product names), cart, checkout (labels, the 7 form errors, test-mode notice), the server's messages (card declined, address required), order page and timeline, tracking page, footer. A language picker in the header; the choice is remembered in the browser, else the browser's language is used. Arabic switches the page to right-to-left (layout rules moved to start/end properties; the cart opens from the left).
- One source for all page texts: `demo/i18n.json` (161 texts keyed by the English text, nine translations each, loaded by `demo/i18n.js`); the chat widget's texts moved there too, and the chat starts in the store's language until a conversation's language is known. `tests/test_i18n.py`: every text in every language with the same placeholders, and every text the page code asks for exists.
- Checked in the browser: Hindi menu, cart, checkout, all form errors, the declined-card message and order page; Arabic right-to-left at desktop and 375 px; Tamil at 375 px; no page scrolls sideways (one bug found and fixed: the hidden skip link made Arabic pages scroll sideways).
- **Native-speaker review: not done, and it cannot be done by an AI.** What is in place: `python -m src.i18n.review_sheets export` writes one sheet per language (`reports/translation_review/<locale>.csv`, 185 rows each: the assistant's replies, store and chat texts, suggested phrases) with approved / correction / note columns, and `apply` writes reviewers' corrections back into `rasa/domain.yml`, `demo/i18n.json` and `demo/chat.js` (skipping any text changed since export). Instructions in `reports/translation_review/README.md`; the round trip is tested. Review status: all nine languages not yet reviewed.
- `pytest` 73 passed.

### First demo page (2026-11-16, superseded by the website above)

A FeastFleet storefront (`demo/`) with a chat widget, served by a fourth service `web` (`nginx:1.27-alpine`, `docker/nginx.conf`).
- Chat widget: language picker (auto-detect + ten languages; sent as the `metadata.language` hint, so Swahili works), three suggested phrases per language, Yes/No buttons for the human-agent offer, per-message right-to-left text (Arabic), "Order" on each menu card sends an order sentence in the chosen language. Changing language starts a new conversation (the bot keeps the first language). Bot replies rendered as text only (no HTML injection).
- nginx proxies only `/webhooks/rest/webhook` to Rasa (same origin, no CORS); Rasa's tracker/model API returns 404 through the site. Strict Content-Security-Policy (self only), system fonts, nothing loaded from outside localhost, no access log, nothing stored in the browser.
- Tested in the browser pane: Spanish two-turn order, Arabic order tracking (FF-1002) right-to-left, menu-card order on a phone-size screen (chat goes full-screen); no console errors. Suggested phrases are AI-written and unreviewed, like the bot replies.

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
| Docker | 29.9.3 (Docker Desktop, WSL 3.0.5), installed later the same day |
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
| ~~Docker Desktop not installed~~ | — | Resolved 2026-11-16: Docker 29.9.3 running after WSL reinstall |

## Changelog

- 2026-11-16: Phase 0 completed. Python 3.10.22 chosen to match Rasa 3.6's limit (`>=3.8,<3.11`).
- 2026-11-16: Phase 4 completed. Found mBERT cannot tokenise Amharic (97.2% `[UNK]`). User decided: keep am-ET, deploy XLM-R, keep training mBERT for comparison.
- 2026-11-16: Phase 1 completed. Official splits kept despite text overlap; overlap and annotator-flag effects will be reported as sensitivity checks, not filtered out.
- 2026-11-17: Human agent handoff: support inbox at `/agent`, chats held in memory only while open.
