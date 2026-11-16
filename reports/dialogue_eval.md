# Scripted conversation evaluation (Phase 9)

FeastFleet is a FICTIONAL business; orders are mock. Conversations authored before running (`data/dialogue_eval/scripted_conversations.yaml`); non-English sentences unreviewed.

A conversation is completed when every turn gives exactly the scripted replies, in the expected language, with the AI disclosure first.

| Measure | Result |
|---|---|
| Task completion (order / order-status conversations) | 24/35 (69%) |
| All conversations completed | 49/64 (77%) |
| Turns correct | 70/89 (79%) |
| Disclosure first | 64/64 (100%) |

## By language

| Locale | Completed | Task completion |
|---|---|---|
| en-US | 8/10 (80%) | 3/5 (60%) |
| es-ES | 6/6 (100%) | 4/4 (100%) |
| de-DE | 4/6 (67%) | 2/3 (67%) |
| fr-FR | 4/6 (67%) | 3/4 (75%) |
| ja-JP | 3/6 (50%) | 1/3 (33%) |
| hi-IN | 4/6 (67%) | 1/3 (33%) |
| ar-SA | 5/6 (83%) | 2/3 (67%) |
| sw-KE | 4/6 (67%) | 2/4 (50%) |
| am-ET | 5/5 (100%) | 3/3 (100%) |
| ta-IN | 4/5 (80%) | 3/3 (100%) |
| unsupported | 2/2 (100%) | – |

## By goal

| Goal | Completed |
|---|---|
| order | 14/24 (58%) |
| status | 10/11 (91%) |
| handoff | 13/13 (100%) |
| cant_help | 6/10 (60%) |
| info | 6/6 (100%) |

## Failed turns (19)

| Category | Turns |
|---|---|
| handoff instead of answer | 17 |
| misroute | 1 |
| wrong language detected | 1 |

| Conversation | Turn | User | Expected | Got | NLU intent | Language | Category |
|---|---|---|---|---|---|---|---|
| en-order-full | 1 | can i get a large pepperoni pizza delivered | order_placed | ask_order_id | takeaway_query | en-US | misroute |
| en-order-ask | 1 | i'd like to place an order | ask_food_type | handoff | nlu_fallback | en-US | handoff instead of answer |
| en-order-ask | 2 | chicken biryani | order_placed | handoff | nlu_fallback | en-US | handoff instead of answer |
| de-order-ask | 2 | döner | order_placed | handoff | nlu_fallback | de-DE | handoff instead of answer |
| de-unsupported | 1 | spiel mein lieblingslied | cant_help | handoff | nlu_fallback | de-DE | handoff instead of answer |
| fr-order-ask | 1 | je veux passer une commande | ask_food_type | handoff | nlu_fallback | fr-FR | handoff instead of answer |
| fr-order-ask | 2 | un burger | order_placed | handoff | nlu_fallback | fr-FR | handoff instead of answer |
| fr-unsupported | 1 | allume la lumière du salon | cant_help | handoff | nlu_fallback | fr-FR | handoff instead of answer |
| ja-order-full | 1 | 寿司を注文したいです | order_placed | handoff | nlu_fallback | ja-JP | handoff instead of answer |
| ja-order-ask | 1 | 出前を頼みたい | ask_food_type | handoff | nlu_fallback | ja-JP | handoff instead of answer |
| ja-order-ask | 2 | ラーメン | order_placed | handoff | nlu_fallback | ja-JP | handoff instead of answer |
| ja-unsupported | 1 | 音楽をかけて | cant_help | handoff | nlu_fallback | ja-JP | handoff instead of answer |
| hi-order-full | 1 | मुझे एक बर्गर मंगवाना है | order_placed | handoff | nlu_fallback | hi-IN | handoff instead of answer |
| hi-order-ask | 2 | बिरयानी | order_placed | handoff | nlu_fallback | hi-IN | handoff instead of answer |
| ar-order-ask | 2 | شاورما | order_placed | handoff | nlu_fallback | ar-SA | handoff instead of answer |
| sw-status | 1 | oda yangu iko wapi | ask_order_id | handoff | nlu_fallback | sw-KE | handoff instead of answer |
| sw-status | 2 | FF-1001 | order_status | handoff | nlu_fallback | sw-KE | handoff instead of answer |
| sw-order-nohint | 1 | nataka kuagiza wali na nyama | order_placed | order_placed | takeaway_order | en-US | wrong language detected |
| ta-unsupported | 1 | பாட்டு போடு | cant_help | handoff | nlu_fallback | ta-IN | handoff instead of answer |
