# Translation review (native speakers)

Every non-English text in FeastFleet was written by an AI and has **not yet been reviewed by a native speaker**. One
sheet per language lists all of them, so a reviewer can check them without reading code:

| File | Language | Rows |
|---|---|---|
| `es-ES.csv` | Español | 185 |
| `de-DE.csv` | Deutsch | 185 |
| `fr-FR.csv` | Français | 185 |
| `ja-JP.csv` | 日本語 | 185 |
| `hi-IN.csv` | हिन्दी | 185 |
| `ar-SA.csv` | العربية | 185 |
| `sw-KE.csv` | Kiswahili | 185 |
| `am-ET.csv` | አማርኛ | 185 |
| `ta-IN.csv` | தமிழ் | 185 |

Each sheet has the assistant's 20 replies, the store and chat-window texts (161, including the menu descriptions) and
the chat's 4 suggested phrases.

## For the reviewer

Open your language's file in Excel, Google Sheets or LibreOffice. For each row, read `english` and `translation`:

- **approved**: write `yes` if the translation is natural and correct, `no` if not.
- **correction**: if it is wrong or unnatural, write the better wording. Keep anything in curly brackets exactly as it
  is (`{name}`, `{amount}`, `{id}`): the site fills these in.
- **note**: anything else (tone, a word customers would actually use, a cultural issue).

Do not change the other columns. Save as CSV (UTF-8).

## For the developer

```bash
python -m src.i18n.review_sheets apply    # writes every correction into domain.yml, i18n.json and chat.js
python -m pytest -q                       # placeholders still match, nothing missing
python -m src.i18n.review_sheets export   # fresh sheets that show the corrected text
```

A correction whose source text changed after the sheet was exported is skipped and listed, never overwritten. If the
AI disclosure (`utter_disclosure`) is corrected, copy the same wording into `configs/disclosure.yaml` (a test checks
they match). Record who reviewed which language, and when, in `PROJECT_STATUS.md`.

Not in the sheets: the keyword lists in `configs/faq.yaml` and `configs/swahili_words.txt`. They are search terms, not
translations, and are checked by measurements on real sentences instead.

## Review status

| Language | Reviewed by | Date | Result |
|---|---|---|---|
| all nine | not yet reviewed | | |
