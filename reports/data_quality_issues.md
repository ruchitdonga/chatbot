# Data-Quality Issues and Remediation

Analysis of the ten configured MASSIVE 1.1 locales (2026-11-16). Counts come from `python -m src.data.eda` (see `reports/dataset_report.md`) and one follow-up check of train/test text overlap. Nothing is removed from the official splits; each issue is handled by reporting, not by silent filtering.

## Checks that passed

- 16,521 utterances per locale, 165,210 in total; 11,514 train / 2,033 dev / 2,974 test in every locale.
- 60 intents and 55 slot types, the same set in every locale.
- Every ID appears in all ten locales and sits in the same partition in each, so training on some locales and testing on others (Run A) does not leak test items.
- No missing values, duplicate IDs, malformed slot markup or empty slot values. Removing the markup from `annot_utt` reproduces `utt` in every record (ignoring whitespace).

## Issue 1: Some test utterances also appear in training

After normalising whitespace and case, a share of test utterances have an exact text match in train, and some texts carry different intents in different records.

| Locale | Test utterances also in train | Share of test | Texts with conflicting intents |
|---|---|---|---|
| en-US | 21 | 0.7% | 7 |
| es-ES | 136 | 4.6% | 29 |
| de-DE | 115 | 3.9% | 28 |
| fr-FR | 150 | 5.0% | 25 |
| ja-JP | 207 | 7.0% | 33 |
| hi-IN | 133 | 4.5% | 33 |
| ar-SA | 237 | 8.0% | 83 |
| sw-KE | 170 | 5.7% | 29 |
| am-ET | 105 | 3.5% | 32 |
| ta-IN | 146 | 4.9% | 31 |

In ar-SA and ja-JP the overlapping utterances are shorter than typical test utterances (median 12 vs 25 characters, and 9 vs 14), mostly weather, time and lighting requests whose translations converge on the same words. In en-US the 21 overlaps are of normal length. The overlap makes test scores slightly optimistic, most for ar-SA and ja-JP.

Remediation: keep the official splits, since the spec requires them and published MASSIVE results use them. Phase 3 records the overlapping test IDs. Phase 6 reports test metrics twice, on the full test split (headline) and on the unseen subset, so the effect is visible per locale. Texts with conflicting intents are listed for the error analysis.

## Issue 2: Annotator-flagged label problems vary strongly by locale

Each non-English utterance was judged by several annotators. The share where most judged the intent wrong, the slots wrong, or the text not in the target language:

| Locale | Intent judged wrong | Slots judged wrong | Not target language |
|---|---|---|---|
| es-ES | 0.0% | 0.4% | 0.0% |
| de-DE | 1.8% | 2.7% | 0.0% |
| fr-FR | 0.3% | 5.4% | 0.0% |
| ja-JP | 0.3% | 0.6% | 0.0% |
| hi-IN | 1.7% | 0.6% | 0.1% |
| ar-SA | **12.3%** | 2.0% | **3.5%** |
| sw-KE | 0.1% | 1.5% | 0.0% |
| am-ET | 0.2% | 1.4% | 0.0% |
| ta-IN | **5.5%** | 0.3% | 0.0% |

In ar-SA the flags concentrate in the `play`, `transport` and `calendar` scenarios, and 3.5% of utterances were judged mostly English or another language. In ta-IN they concentrate in `play` and `email`.

This matters for fairness: if ar-SA or ta-IN score lower, part of the gap may be label noise rather than model weakness, and the fairness audit must not blame one for the other.

Remediation: keep these records, because removing them would also remove genuinely hard examples. In Phase 6, report per-locale metrics on the full test split (headline) and on a "judge-clean" test subset that excludes majority-flagged records, as a sensitivity check. Record the flag rates in the data card and model card.

## Issue 3: Extreme class imbalance, identical in every locale

Training examples per intent range from 4 to 810 (a 202x ratio) in every locale, because the data is parallel. `cooking_query` has only 6 utterances in total, and some slot types are nearly absent (`music_album` and `game_type` appear twice each in en-US).

Overall accuracy will hide failures on these rare classes, and per-class scores for them will rest on one or two test examples.

Remediation: report intent macro-F1 and per-class precision, recall and F1 alongside accuracy. Mark any class with fewer than 10 test examples as a low-confidence estimate. In Phase 5, try a class-weighted loss and keep it only if it improves dev macro-F1 without lowering dev accuracy.

## Note for Phase 3: Japanese has no word spaces

The median ja-JP utterance has one whitespace-separated "word" (14 characters), so word-level BIO tagging by whitespace will not work for ja-JP. The annotations add spaces around slots that the raw text lacks. Phase 3 derives slot labels from character spans, as the guide already plans.

## Note for Run B: locales are already equal-sized

Every locale has exactly 11,514 training utterances, so "language-balanced sampling" adds nothing on its own. The Run B mitigation is training on the target languages themselves (Run A trains only on the high-resource five). If a locale is still more than 10 pp below the mean after Run B, the next step is upsampling or augmenting that locale.
