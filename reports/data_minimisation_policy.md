# Data-Minimisation Policy

Applies to the NLU service, the Rasa dialogue layer, logs, monitoring data and evaluation artefacts of this student prototype. It implements OBJ-5, FR-5, FR-6, NFR-5 and ETH-3. It describes controls; it is not a legal assessment and does not claim GDPR compliance.

## Why it is needed

The PII audit (`reports/pii_audit.md`) finds that about 18% of utterances in every locale contain a slot that can hold personal data: person names (1,134–1,188 utterances per locale), place names (1,402–1,451), relations, personal-info references and email addresses. No utterance contains an email in `name@domain` form or a run of 6+ digits; MASSIVE writes these out in words. A regex scrubber alone would therefore miss most personal data, so the primary control is to never store text at all. MASSIVE is assistant-style data, but the policy is applied as if it were real customer support text (spec 5.3).

## What may be stored

Only these fields, per conversation turn (`logging.allowed_fields` in `configs/project.yaml`):

| Field | Example | Why it is needed |
|---|---|---|
| `intent` | `alarm_set` | Intent-distribution drift (FR-6) |
| `slot_labels` | `[time, date]`, labels only | Slot-frequency drift |
| `locale` | `sw-KE` | Language-distribution drift, per-language fallback rate |
| `confidence` | `0.83` | Fallback-rate monitoring |
| `latency_ms` | `41` | NFR-4 |
| `model_version` | `xlm-roberta-base-runB-oos` | Traceability and rollback |
| `handoff`, `handoff_reason` | `true`, `low_confidence` | Fallback-rate monitoring and retraining triggers (added in Phase 8; no personal data) |

## What is never stored

- Raw utterance text (`logging.log_raw_text: false`).
- Slot values, such as the name, place or time a user typed.
- Any user identifier. Conversation IDs are random per session and never linked to a person.
- Bot replies that echo slot values.

## Human handoff chats (added 2026-11-17)

When the assistant hands a conversation to a person, the website opens a chat in the orders service (`/api/handoffs`) so an agent can reply from the support inbox (`/agent`).
- What it holds: up to the last 50 widget messages as the transcript, then the customer's and agent's messages (at most 200 per chat, 1,000 characters each), the language and the time opened. An agent has to read the words to help, so this is the one place message text is kept.
- Where: process memory only. It is never written to disk and never logged. A service restart deletes it.
- How long: until the chat is closed by the agent or the customer (restart, language change). Closing deletes the messages immediately; only the closed status stays, so the widget can see that the chat ended.
- Limits: at most 50 open chats; more get "all agents are busy".
- Not production-ready: the inbox has **no login**. That is acceptable only because every service is bound to localhost. A real deployment needs agent authentication, TLS, and a retention rule agreed with the data owner.

## Personal-data slot types

Defined once in `privacy.pii_slot_types` in `configs/project.yaml`:

| Group | Slot types | Handling |
|---|---|---|
| Direct identifier | `person`, `email_address` | Value never stored; masked as `[PERSON]` / `[EMAIL_ADDRESS]` wherever text must be shown |
| Location | `place_name` | Value never stored; masked as `[PLACE_NAME]` |
| Personal context | `personal_info`, `relation` | Value never stored; masked as `[PERSONAL_INFO]` / `[RELATION]` |

## Scrubbing (defence in depth)

Text should never reach a log, but error messages and debug output can leak it. Any free text that could be written anywhere passes through `src/privacy/pii_scrubber.py` (Phase 3), which:

1. Masks the values of predicted personal-data slots, using the NLU model's own slot predictions.
2. Masks email addresses, order-style IDs (e.g. `ORD-48213`), phone and other long numbers (6+ digits) and street addresses by regex. The address pattern only knows English street words.

spaCy NER is not used: spaCy has no trained pipelines for Swahili, Amharic or Tamil, while the slot masking in step 1 uses this project's own model, trained on all ten languages.

## Rasa settings (Phase 9)

- Use Rasa's in-memory tracker store only. A persistent tracker store would save every conversation's text, so none is configured.
- Run Rasa at log level INFO or higher; DEBUG logging prints user messages.
- Confirm both by inspecting the logs after a scripted conversation.

## Retention

- Raw text: not retained anywhere, except open human-handoff chats, held in memory until the chat closes (see above).
- Turn-level allowed fields: kept locally for the project's duration, then deleted.
- Evaluation predictions contain MASSIVE test utterances. These are public CC BY 4.0 data, not user data, and are stored under `artifacts/`, which Git ignores.

## Demo users

The demo tells users it is a student prototype and asks them not to enter real personal information. The AI disclosure (`configs/disclosure.yaml`) opens every conversation (ETH-4).

## Verification

| Check | Phase |
|---|---|
| PII-scrub unit test on a synthetic PII-bearing conversation (NFR-5) | 3 |
| Test that the serving log line contains only the allowed fields | 8 |
| Inspection of Rasa logs and tracker store after a scripted conversation | 9 |
| PII-scrub test enforced in CI (ETH-3) | 11 |

## Not verified yet

All controls above are design until their phase's test passes. Scrubbing quality is limited for languages without a spaCy NER model, and slot-based masking depends on the model detecting the slot.
