"""Out-of-scope training data: complete for every locale and never overlapping the challenge set."""
import json

import pandas as pd

from src.data.load import configured_locales, load_config
from src.models.train import CHALLENGE_PATH, OOS_LABEL, OOS_PATHS, external_oos_examples, first_words, oos_examples

FILES = {path.stem: json.loads(path.read_text(encoding="utf-8")) for path in OOS_PATHS}
CHALLENGE = [json.loads(line)["text"] for line in CHALLENGE_PATH.read_text(encoding="utf-8").splitlines() if line]


def test_every_configured_locale_is_complete():
    sizes = {"oos_train": 20, "food_delivery": 30}
    for name, data in FILES.items():
        for loc in configured_locales(load_config()):
            assert len(data[loc]) == sizes[name] and len(set(data[loc])) == sizes[name], (name, loc)


def test_no_authored_sentence_appears_in_the_challenge_set():
    norm = lambda s: " ".join(s.split()).casefold()  # noqa: E731
    challenge = {norm(t) for t in CHALLENGE}
    assert not [t for data in FILES.values() for texts in data.values() for t in texts if norm(t) in challenge]


def test_oos_examples_expand_with_upsampling():
    examples = oos_examples(OOS_PATHS, ["en-US", "sw-KE"], upsample=3)
    assert len(examples) == 2 * (20 + 30) * 3
    assert {ex["intent"] for ex in examples} == {OOS_LABEL}
    assert all(ex["spans"] == [] and ex["partition"] == "train" for ex in examples)


def test_external_examples_drop_excluded_categories_and_challenge_lookalikes(tmp_path):
    path = tmp_path / "tickets.parquet"
    pd.DataFrame({
        "id": [1, 2, 3, 4],
        "customer_message": ["My fries were missing from the bag", "Where is my order, it is late",
                             "I want a refund for my cold pizza", "The courier was rude to me"],
        "category": ["missing_item", "late_delivery", "refund_request", "courier_problem"],
    }).to_parquet(path)
    examples = external_oos_examples(path, n=10, seed=0, challenge_texts=["I want a refund for my last order", ""])
    kept = sorted(ex["utt"] for ex in examples)
    assert kept == ["My fries were missing from the bag", "The courier was rude to me"]
    assert all(ex["locale"] == "en-US" and ex["intent"] == OOS_LABEL for ex in examples)
    assert first_words("I  Want a REFUND for x") == "i want a refund"
