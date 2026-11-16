"""The out-of-scope challenge set keeps its structure: unique ids, both splits per category, all ten languages."""
import json
from collections import Counter

from src.data.load import ROOT, configured_locales, load_config

ITEMS = [json.loads(line) for line in
         (ROOT / "data" / "challenge_set" / "challenge_set.jsonl").read_text(encoding="utf-8").splitlines() if line]
CATEGORIES = {"support_out_of_domain", "adversarial", "mixed_language", "gibberish", "empty", "symbols",
              "very_long", "unsupported_language"}


def test_fields_and_unique_ids():
    assert len({i["id"] for i in ITEMS}) == len(ITEMS)
    for item in ITEMS:
        assert item["category"] in CATEGORIES
        assert item["expected"] == "handoff" and item["source"] == "authored"
        assert item["split"] in ("tune", "heldout")


def test_every_category_has_both_splits_and_halves_are_balanced():
    splits = Counter(i["split"] for i in ITEMS)
    assert abs(splits["tune"] - splits["heldout"]) <= 1
    for category in CATEGORIES:
        assert {i["split"] for i in ITEMS if i["category"] == category} == {"tune", "heldout"}


def test_all_configured_languages_covered():
    covered = {i["language"] for i in ITEMS}
    assert set(configured_locales(load_config())) <= covered
