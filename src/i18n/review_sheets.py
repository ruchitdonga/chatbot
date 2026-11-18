"""Native-speaker review of every AI-written translation: one sheet per language, and corrections written back.

Sources: the assistant's replies (rasa/domain.yml), the store and chat-widget texts (demo/i18n.json) and the chat's
suggested phrases (CHIPS in demo/chat.js). Each row is English + the current translation, with empty columns for the
reviewer: approved (yes/no), correction, note.

  python -m src.i18n.review_sheets export   # writes reports/translation_review/<locale>.csv (Excel/Sheets-ready)
  python -m src.i18n.review_sheets apply    # applies every filled-in "correction" back to the three source files

Keyword lists (configs/faq.yaml) and the Swahili marker words are not in the sheets: they are search terms, not
translations, and are measured on data instead (PROJECT_STATUS.md).
"""
import csv
import json
import re
import sys
from pathlib import Path

import yaml

from src.data.load import ROOT, configured_locales, load_config

COLUMNS = ["area", "key", "english", "translation", "approved", "correction", "note"]


def domain_rows(domain_path, locale):
    responses = yaml.safe_load(Path(domain_path).read_text(encoding="utf-8"))["responses"]
    for name, variations in responses.items():
        by_locale = {(v["condition"][0]["value"] if "condition" in v else "en-US"): v["text"] for v in variations}
        if locale in by_locale:
            yield {"area": "assistant reply", "key": name, "english": by_locale["en-US"], "translation": by_locale[locale]}


def store_rows(i18n_path, locale):
    for english, tr in json.loads(Path(i18n_path).read_text(encoding="utf-8"))["strings"].items():
        if locale in tr:
            yield {"area": "store and chat text", "key": english[:60], "english": english, "translation": tr[locale]}


def chips(chat_path):
    """locale -> suggested phrases, from the CHIPS table in chat.js (one JSON-style array per line)."""
    block = re.search(r"const CHIPS = \{(.*?)\n  \};", Path(chat_path).read_text(encoding="utf-8"), re.S).group(1)
    return {loc: json.loads(arr) for loc, arr in re.findall(r'"([a-z]{2}-[A-Z]{2})": (\[.*\]),', block)}


def chip_rows(chat_path, locale):
    table = chips(chat_path)
    for i, (english, text) in enumerate(zip(table["en-US"], table.get(locale, []))):
        yield {"area": "suggested phrase", "key": f"chip {i + 1}", "english": english, "translation": text}


def sheet_rows(root, locale):
    return [*domain_rows(root / "rasa" / "domain.yml", locale), *store_rows(root / "demo" / "i18n.json", locale),
            *chip_rows(root / "demo" / "chat.js", locale)]


def export(root=ROOT, out_dir=None):
    out_dir = Path(out_dir or root / "reports" / "translation_review")
    out_dir.mkdir(parents=True, exist_ok=True)
    counts = {}
    for locale in configured_locales(load_config()):
        if locale == "en-US":
            continue
        rows = sheet_rows(root, locale)
        with open(out_dir / f"{locale}.csv", "w", encoding="utf-8-sig", newline="") as f:  # BOM: Excel reads UTF-8
            writer = csv.DictWriter(f, COLUMNS)
            writer.writeheader()
            writer.writerows({**r, "approved": "", "correction": "", "note": ""} for r in rows)
        counts[locale] = len(rows)
    return counts


def apply(root=ROOT, sheet_dir=None):
    """Write every filled-in correction back; returns the number applied. A row whose translation no longer matches
    the source (edited since export) is skipped and reported, never overwritten blindly."""
    sheet_dir = Path(sheet_dir or root / "reports" / "translation_review")
    domain_path, i18n_path, chat_path = root / "rasa" / "domain.yml", root / "demo" / "i18n.json", root / "demo" / "chat.js"
    domain_text = domain_path.read_text(encoding="utf-8")
    strings = json.loads(i18n_path.read_text(encoding="utf-8"))
    chat_text = chat_path.read_text(encoding="utf-8")
    applied, stale = 0, []
    for sheet in sorted(sheet_dir.glob("*.csv")):
        locale = sheet.stem
        with open(sheet, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                new, old = row["correction"].strip(), row["translation"]
                if not new or new == old:
                    continue
                in_domain = f"value: {locale}}}], text: {json.dumps(old, ensure_ascii=False)}"
                if row["area"] == "store and chat text" and strings["strings"].get(row["english"], {}).get(locale) == old:
                    strings["strings"][row["english"]][locale] = new
                elif row["area"] == "assistant reply" and in_domain in domain_text:
                    domain_text = domain_text.replace(
                        in_domain, f"value: {locale}}}], text: {json.dumps(new, ensure_ascii=False)}", 1)
                elif row["area"] == "suggested phrase" and json.dumps(old, ensure_ascii=False) in chat_text:
                    chat_text = chat_text.replace(json.dumps(old, ensure_ascii=False), json.dumps(new, ensure_ascii=False), 1)
                else:
                    stale.append(f"{locale} {row['area']} {row['key']}")
                    continue
                applied += 1
    domain_path.write_text(domain_text, encoding="utf-8")
    i18n_path.write_text(dump_i18n(strings), encoding="utf-8")
    chat_path.write_text(chat_text, encoding="utf-8")
    for s in stale:
        print(f"skipped (source changed since export): {s}")
    return applied


def dump_i18n(data):
    """i18n.json in its one-line-per-text layout, so a review shows up as a small diff."""
    lines = [f'    {json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)}' for k, v in data["strings"].items()]
    return ('{\n  "_note": ' + json.dumps(data["_note"], ensure_ascii=False) + ',\n  "strings": {\n'
            + ",\n".join(lines) + "\n  }\n}\n")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "export"
    if command == "export":
        for loc, n in export().items():
            print(f"{loc}: {n} rows -> reports/translation_review/{loc}.csv")
    elif command == "apply":
        print(f"{apply()} corrections applied; rebuild the containers and run pytest")
    else:
        sys.exit("usage: python -m src.i18n.review_sheets [export|apply]")
