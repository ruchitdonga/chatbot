# Out-of-Scope Challenge Set

110 inputs the chatbot must route to human handoff rather than answer (NFR-3, ETH-2). Every item was written for this project by an AI assistant; none comes from MASSIVE. Non-English items are marked `unreviewed` until a fluent speaker checks them.

## What counts as out of scope

MASSIVE already contains chit-chat intents (`general_quirky`, `general_joke`, `general_greet`), so small talk is in scope and not included here. These inputs are clearly outside what the bot can handle:

| Category | Items | What it tests |
|---|---|---|
| `support_out_of_domain` | 50 (5 × 10 languages) | Real support requests MASSIVE has no intent for: refunds, damaged orders, double charges, account deletion, warranty claims |
| `adversarial` | 20 (2 × 10 languages) | Instruction-override attempts and explicit requests for a human |
| `mixed_language` | 20 (2 × 10 languages) | Out-of-scope requests mixing the target language with English (or Spanish, for en-US) |
| `gibberish` | 6 | Keyboard mashing |
| `empty` | 3 | Empty or whitespace-only input |
| `symbols` | 3 | Emoji, punctuation, bare numbers |
| `very_long` | 2 | Long rambling complaints (English, Spanish) |
| `unsupported_language` | 6 | Requests in pt, ru, ko, it, tr, pl, outside the ten languages |

## Splits

`split` alternates within each category: 55 `tune` items (used with dev data to choose the fallback threshold) and 55 `heldout` items (used once, for the reported routing rate). Do not move items between splits after looking at results.

## Format

One JSON object per line: `id`, `category`, `language` (`none` for language-independent items), `text`, `expected` (always `handoff`), `split`, `source` (`authored`), `review_status`.
