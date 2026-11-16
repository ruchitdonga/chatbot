# Data Card (draft)

Draft from Phase 2; finalised in Phase 12.

## Dataset

MASSIVE 1.1 (Amazon, 2022), CC BY 4.0. Created by professionally translating and localising the English SLURP dataset. Citation and download details: `data/README.md`.

## Subset used

| Tier | Locales | Utterances |
|---|---|---|
| High resource | en-US, es-ES, de-DE, fr-FR, ja-JP | 82,605 |
| Mid resource | hi-IN, ar-SA | 33,042 |
| Low resource | sw-KE, am-ET, ta-IN | 49,563 |
| Total | 10 locales | 165,210 |

Each locale has 11,514 train / 2,033 dev / 2,974 test utterances, using MASSIVE's official partitions, which are identical across locales. Labels: 60 intents (`scenario_intent`) and 55 slot types.

## Representation

- Equal size per locale, so no language is under-represented in volume. The tier labels reflect how much these languages appear in the encoders' pretraining data, not in MASSIVE.
- The data is parallel: every locale contains translations of the same English utterances. Topics, intents and slot distributions are therefore the same in every language and reflect the English source, not how speakers of each language actually phrase support requests.
- Class balance is identical across locales and highly skewed: 4 to 810 training examples per intent.
- Annotation quality varies by locale. Annotators judged 12.3% of ar-SA and 5.5% of ta-IN intents wrong, against at most 1.8% elsewhere (`reports/data_quality_issues.md`).
- Script and length differ: ja-JP has no word spaces; median utterance length ranges from 14 characters (ja-JP) to 40 (fr-FR).

## Domain limitation

MASSIVE contains virtual-assistant requests (alarms, music, weather, calendar, smart home, email, transport, takeaway orders), not customer-support conversations. The chatbot therefore demonstrates multilingual intent and slot handling on assistant-style tasks. Results do not show how it would perform on a real company's support traffic.

## Personal data

About 18% of utterances per locale contain a slot that can hold personal data, mostly person names and place names (`reports/pii_audit.md`). Values are synthetic assistant requests, not real customer data, but are handled under `reports/data_minimisation_policy.md`.

Retained operational log fields: `intent`, `slot_labels`, `locale`, `confidence`, `latency_ms`, `model_version`. No raw text or slot values.

## Known issues

See `reports/data_quality_issues.md`: train/test text overlap (0.7–8.0% of test), locale-dependent annotation quality, extreme class imbalance.

## Intended use

Training and evaluating a student prototype for multilingual intent classification and slot extraction, including a per-language fairness audit. Not for production customer support.
