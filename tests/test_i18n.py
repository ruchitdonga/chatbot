"""Store and chat-widget texts (demo/i18n.json): every text in all ten languages, same placeholders, and every text the
page code asks for (t("...") in app.js, data-i18n in index.html, chat.js) exists in the file."""
import json
import re

from src.data.load import ROOT, configured_locales, load_config

STRINGS = json.loads((ROOT / "demo" / "i18n.json").read_text(encoding="utf-8"))["strings"]
OTHERS = set(configured_locales(load_config())) - {"en-US"}


def placeholders(text):
    return sorted(re.findall(r"\{(\w+)\}", text))


def test_every_text_in_every_language():
    for english, tr in STRINGS.items():
        assert set(tr) == OTHERS, english
        for locale, text in tr.items():
            assert text.strip(), (english, locale)
            assert placeholders(text) == placeholders(english), (english, locale)


def test_page_code_only_asks_for_known_texts():
    demo = ROOT / "demo"
    used = set()
    for name in ("app.js", "chat.js"):
        used |= set(re.findall(r'\bt\("((?:[^"\\]|\\.)*)"', (demo / name).read_text(encoding="utf-8")))
    widget = re.search(r"const EN = \{(.*?)\};", (demo / "chat.js").read_text(encoding="utf-8"), re.S).group(1)
    used |= set(re.findall(r'"((?:[^"\\]|\\.)*)"', widget))  # chat.js keeps its texts in one table
    html = (demo / "index.html").read_text(encoding="utf-8")
    used |= set(re.findall(r'data-i18n="([^"]+)"', html))
    used |= {pair.split("=", 1)[1] for attr in re.findall(r'data-i18n-attr="([^"]+)"', html) for pair in attr.split(";")}
    missing = sorted(u.replace('\\"', '"') for u in used if u.replace('\\"', '"') not in STRINGS)
    assert len(used) > 120 and not missing, missing


def test_review_sheet_round_trip(tmp_path):
    """Export the sheets for a copy of the project, fill in one correction per area, apply, and find each in place."""
    import csv
    import shutil

    from src.i18n.review_sheets import apply, export

    for rel in ("rasa/domain.yml", "demo/i18n.json", "demo/chat.js"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, tmp_path / rel)
    counts = export(tmp_path, tmp_path / "sheets")
    assert set(counts) == OTHERS and min(counts.values()) > 150
    sheet = tmp_path / "sheets" / "sw-KE.csv"
    with open(sheet, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    fixes = {"assistant reply": "Habari! (imerekebishwa)", "store and chat text": "Kikapu (imerekebishwa)",
             "suggested phrase": "Nataka pizza (imerekebishwa)"}
    for area, fix in fixes.items():
        next(r for r in rows if r["area"] == area)["correction"] = fix
    with open(sheet, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    assert apply(tmp_path, tmp_path / "sheets") == 3
    for rel in ("rasa/domain.yml", "demo/i18n.json", "demo/chat.js"):
        text = (tmp_path / rel).read_text(encoding="utf-8")
        assert sum(fix in text for fix in fixes.values()) == 1, rel  # each correction landed in exactly its own file
    assert json.loads((tmp_path / "demo" / "i18n.json").read_text(encoding="utf-8"))["strings"]  # still valid JSON
