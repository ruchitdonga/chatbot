# Requirements and Scope

Source: Project 15 specification (Multi-Lingual Customer Support Chatbot with Intent Classification and Entity Extraction). Targets below are acceptance criteria to validate, not results.

## Objectives

| ID | Objective | Phase |
|---|---|---|
| OBJ-1 | Fine-tune mBERT jointly for intent classification and slot extraction on MASSIVE; mean intent accuracy ≥ 0.85 and mean slot micro-F1 ≥ 0.75 across ten languages; significantly beat a per-language majority-intent baseline and a bag-of-embeddings baseline | 4, 5, 6 |
| OBJ-2 | Compare mBERT with XLM-R under identical training; measure the cross-lingual transfer gap between high- and low-resource languages | 5, 6 |
| OBJ-3 | Integrate the NLU model into Rasa Open Source with slot-filling forms and a confidence-gated human-handoff fallback | 7, 9 |
| OBJ-4 | Per-language fairness audit; no language more than 10 pp below the mean, with targeted data balancing where needed | 6 |
| OBJ-5 | Documented PII data-minimisation policy, PII scrubbed from logs, verified by tests | 2, 3 |
| OBJ-6 | Dockerised chatbot, MLflow/Optuna lineage, Evidently drift monitoring, CI/CD gates, Responsible AI report, model card, data card | 4, 5, 10, 11, 12 |

## Functional requirements

| ID | Requirement | Phase |
|---|---|---|
| FR-1 | Accept an utterance in any of the ten languages; return the intent with confidence and the slots with labels and spans | 8 |
| FR-2 | Fill required slots via forms, ask for missing slots, complete the task against a mock backend | 9 |
| FR-3 | Route to human handoff when confidence is below threshold or the intent is out of scope | 7, 9 |
| FR-4 | Detect the input language (or accept a hint) and reply in the same language with templated responses | 8, 9 |
| FR-5 | Scrub PII (names, addresses, order IDs, emails) from stored logs | 3, 8 |
| FR-6 | Log intent/slot statistics and language distribution, not raw text, for drift monitoring | 8, 11 |

## Non-functional requirements

| ID | Category | Acceptance criterion | Phase |
|---|---|---|---|
| NFR-1 | Accuracy | Mean intent accuracy ≥ 0.85, mean slot micro-F1 ≥ 0.75 across ten languages; significant gain over baselines | 6 |
| NFR-2 | Linguistic fairness | No language's intent accuracy more than 10 pp below the ten-language mean after mitigation; per-language table published | 6 |
| NFR-3 | Safe fallback | ≥ 95% of out-of-scope/low-confidence inputs in a held-out challenge set routed to human handoff | 7 |
| NFR-4 | Latency | ≤ 300 ms median NLU inference on a 4-core CPU (quantised ONNX mBERT); end-to-end turn ≤ 1 s excluding backend | 8, 10 |
| NFR-5 | Privacy | Zero PII persisted in logs, verified by a PII-scrub unit test on a synthetic conversation | 3, 8 |
| NFR-6 | Reproducibility | Splits frozen with checksums; pinned seeds and dependencies; README reproduction in under 1 hour | 3, 12 |

## Ethical requirements

| ID | Requirement | Acceptance criterion | Phase |
|---|---|---|---|
| ETH-1 | Linguistic fairness | Pre- and post-mitigation per-language tables in the evaluation report | 6 |
| ETH-2 | Safe handoff | Fallback-routing test on the challenge set meets NFR-3 | 7, 9 |
| ETH-3 | PII minimisation | PII-scrub unit test passes in CI; data card lists retained fields | 2, 3, 11 |
| ETH-4 | Transparency | AI disclosure at conversation start, present in the Rasa flow and checked in the demo | 2, 9 |

## Scope

In scope: joint intent + slot extraction on MASSIVE for ten languages; mBERT vs XLM-R; transfer-gap measurement and fairness audit with mitigation; Rasa dialogue with forms and confidence-gated handoff; PII minimisation with log scrubbing; drift monitoring; Dockerised deployment with a multilingual demo.

Out of scope: open-domain or LLM-generated responses; voice; live CRM/ticketing integration (a mock backend is used); languages or dialects beyond the ten.

## Stakeholders

| Stakeholder | Role / interest | Influence | Main concern |
|---|---|---|---|
| Customers (all languages) | Submit queries, expect resolution | High | Mis-routing, especially in low-resource languages |
| Support agents | Handle escalations | Medium | Trusting the bot's confidence signals |
| Business owners | Fund cost savings | High | Reputational risk from a biased or wrong bot |
| Regulators (GDPR / EU AI Act) | Compliance oversight | High | PII retention, missing AI disclosure |
| Low-resource-language communities | Affected, under-served users | Medium | Systematic under-service |

## Lifecycle mapping (CRISP-DM)

CRISP-DM is the primary lifecycle, with TDSP's customer-acceptance stage folded in as the NFR/ETH gates and Google's ML pipeline view used to separate automated from human decisions.

| CRISP-DM stage | Phases |
|---|---|
| Business understanding | 0 |
| Data understanding | 1, 2 |
| Data preparation | 3 |
| Modelling | 4, 5 |
| Evaluation | 6, 7 |
| Deployment | 8, 9, 10, 11, 12 |

Automated: tokenisation, splits, fine-tuning, metric logging, CI gates, drift detection. Human judgement: language selection, fallback threshold sign-off, fairness mitigations, retrain approvals.

## Milestones

| Weeks | Milestone | Phases |
|---|---|---|
| 1–3 | Scope, requirements, setup | 0 |
| 4 | Data acquisition and EDA | 1 |
| 5 | Ethics audit, privacy policy, data card draft | 2 |
| 6 | Tested NLU pipeline, frozen splits, PII scrubber | 3 |
| 7–9 | Baselines, mBERT, XLM-R, Optuna, evaluation, fairness, calibration (Rasa spike from week 8) | 4, 5, 6, 7 |
| 10 | Serving, Rasa dialogue, Docker | 8, 9, 10 |
| 11–12 | Drift monitoring, retraining policy, CI | 11 |
| 13–15 | Responsible AI report, cards, README, demo | 12 |
