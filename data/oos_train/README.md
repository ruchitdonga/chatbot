# Out-of-Scope Training Data

Training data for the extra `out_of_scope` intent, so the bot hands off requests MASSIVE has no intent for. Used only with `python -m src.models.train --oos`. The chatbot supports a fictional food-delivery business, FeastFleet (`configs/business.yaml`).

| Source | Languages | Items | Used in training |
|---|---|---|---|
| `oos_train.json` (authored) | all 10 | 20 per language: 10 general support requests, 6 requests for a human, 4 adversarial | each repeated 5× |
| `food_delivery.json` (authored) | all 10 | 30 per language: missing items, wrong order, food quality, rider behaviour, money back, payment problems, cancellations, account and address, allergies and food safety, complaints (3 each, in that order) | each repeated 5× |
| OrSabbach/food-delivery-support-tickets | English | 1,000 sampled from 10,153 | once each |

That is 2,500 authored examples plus 1,000 external ones, against MASSIVE's 115,140.

## Authored files

Written for this project by an AI assistant. Non-English sentences are unreviewed until a fluent speaker checks them. Format: `{"<locale>": [sentences]}`.

## External dataset

- Source: https://huggingface.co/datasets/OrSabbach/food-delivery-support-tickets, file `data/dataset.parquet` (1,166,289 bytes, SHA-256 `91bfb7d949dfdc64780db41c73498e1f144a7b2cad7fa67b78c75c647f661775`), downloaded 2026-11-16. Licence MIT.
- Stored at `data/raw/oos_external/food_delivery_support_tickets.parquet` (git-ignored). Only `customer_message` and `category` are used.
- It is **synthetic**: the dataset card says it was generated with Qwen2.5-3B-Instruct and is "not real customers", and that its sentiment and urgency labels are unreliable. No public dataset of real food-delivery support chats was found.
- Excluded: the `late_delivery` category, because "where is my order?" is answered by the bot (`takeaway_query`). 1,000 messages are sampled with the project seed.

## Kept separate from the challenge set

The challenge set (`data/challenge_set/`) measures routing, so it must never be trained on.

- The authored sentences avoid its topics and wording, and `tests/test_oos.py` fails on any exact overlap.
- External messages whose first four words match a challenge item are removed before sampling (363 of 10,153; mostly "I want a refund for …").
- The English half of the challenge set still shares topics (refunds, payments) with the external data, so English routing results may be optimistic. Report routing per language as well as overall.
