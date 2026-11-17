# Scripted conversation evaluation (Phase 9)

FeastFleet is a FICTIONAL business; orders are mock. Conversations authored before running (`data/dialogue_eval/scripted_conversations.yaml`); non-English sentences unreviewed.

A conversation is completed when every turn gives exactly the scripted replies, in the expected language, with the AI disclosure first.

| Measure | Result |
|---|---|
| Task completion (order / order-status conversations) | 32/35 (91%) |
| All conversations completed | 57/64 (89%) |
| Turns correct | 82/89 (92%) |
| Disclosure first | 64/64 (100%) |

## By language

| Locale | Completed | Task completion |
|---|---|---|
| en-US | 9/10 (90%) | 4/5 (80%) |
| es-ES | 6/6 (100%) | 4/4 (100%) |
| de-DE | 5/6 (83%) | 3/3 (100%) |
| fr-FR | 5/6 (83%) | 4/4 (100%) |
| ja-JP | 5/6 (83%) | 3/3 (100%) |
| hi-IN | 6/6 (100%) | 3/3 (100%) |
| ar-SA | 6/6 (100%) | 3/3 (100%) |
| sw-KE | 4/6 (67%) | 2/4 (50%) |
| am-ET | 5/5 (100%) | 3/3 (100%) |
| ta-IN | 4/5 (80%) | 3/3 (100%) |
| unsupported | 2/2 (100%) | – |

## By goal

| Goal | Completed |
|---|---|
| order | 22/24 (92%) |
| status | 10/11 (91%) |
| handoff | 13/13 (100%) |
| cant_help | 6/10 (60%) |
| info | 6/6 (100%) |

## Failed turns (7)

| Category | Turns |
|---|---|
| handoff instead of answer | 5 |
| misroute | 1 |
| wrong language detected | 1 |

| Conversation | Turn | User | Expected | Got | NLU intent | Language | Category |
|---|---|---|---|---|---|---|---|
| en-order-full | 1 | can i get a large pepperoni pizza delivered | added_to_cart | ask_order_id | takeaway_query | en-US | misroute |
| de-unsupported | 1 | spiel mein lieblingslied | cant_help | handoff | nlu_fallback | de-DE | handoff instead of answer |
| fr-unsupported | 1 | allume la lumière du salon | cant_help | handoff | nlu_fallback | fr-FR | handoff instead of answer |
| ja-unsupported | 1 | 音楽をかけて | cant_help | handoff | nlu_fallback | ja-JP | handoff instead of answer |
| sw-status | 1 | oda yangu iko wapi | ask_order_id | handoff | nlu_fallback | sw-KE | handoff instead of answer |
| sw-order-nohint | 1 | nataka kuagiza wali na nyama | added_to_cart | added_to_cart | takeaway_order | en-US | wrong language detected |
| ta-unsupported | 1 | பாட்டு போடு | cant_help | handoff | nlu_fallback | ta-IN | handoff instead of answer |
