# Scripted conversation evaluation (Phase 9)

FeastFleet is a FICTIONAL business; orders are mock. Conversations authored before running (`data/dialogue_eval/scripted_conversations.yaml`); non-English sentences unreviewed.

A conversation is completed when every turn gives exactly the scripted replies, in the expected language, with the AI disclosure first.

| Measure | Result |
|---|---|
| Task completion (order / order-status conversations) | 35/35 (100%) |
| All conversations completed | 60/64 (94%) |
| Turns correct | 85/89 (96%) |
| Disclosure first | 64/64 (100%) |

## By language

| Locale | Completed | Task completion |
|---|---|---|
| en-US | 10/10 (100%) | 5/5 (100%) |
| es-ES | 6/6 (100%) | 4/4 (100%) |
| de-DE | 5/6 (83%) | 3/3 (100%) |
| fr-FR | 5/6 (83%) | 4/4 (100%) |
| ja-JP | 5/6 (83%) | 3/3 (100%) |
| hi-IN | 6/6 (100%) | 3/3 (100%) |
| ar-SA | 6/6 (100%) | 3/3 (100%) |
| sw-KE | 6/6 (100%) | 4/4 (100%) |
| am-ET | 5/5 (100%) | 3/3 (100%) |
| ta-IN | 4/5 (80%) | 3/3 (100%) |
| unsupported | 2/2 (100%) | – |

## By goal

| Goal | Completed |
|---|---|
| order | 24/24 (100%) |
| status | 11/11 (100%) |
| handoff | 13/13 (100%) |
| cant_help | 6/10 (60%) |
| info | 6/6 (100%) |

## Failed turns (4)

| Category | Turns |
|---|---|
| handoff instead of answer | 4 |

| Conversation | Turn | User | Expected | Got | NLU intent | Language | Category |
|---|---|---|---|---|---|---|---|
| de-unsupported | 1 | spiel mein lieblingslied | cant_help | handoff | nlu_fallback | de-DE | handoff instead of answer |
| fr-unsupported | 1 | allume la lumière du salon | cant_help | handoff | nlu_fallback | fr-FR | handoff instead of answer |
| ja-unsupported | 1 | 音楽をかけて | cant_help | handoff | nlu_fallback | ja-JP | handoff instead of answer |
| ta-unsupported | 1 | பாட்டு போடு | cant_help | handoff | nlu_fallback | ta-IN | handoff instead of answer |
