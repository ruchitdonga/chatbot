"""Phase 3: turn MASSIVE records into model-ready examples with character-level slot spans.

Outputs, all regenerable (run from the repo root: python -m src.data.prepare):
- data/processed/<locale>.<partition>.jsonl  examples with slot spans in `utt` coordinates (git-ignored)
- data/splits/labels.json                   intent list and BIO slot tags, shared by all locales
- data/splits/checksums.json                SHA-256 per locale/partition; changes mean the data changed
- data/splits/test_subsets.json             test IDs seen in train, and IDs most annotators flagged
"""
import hashlib
import json

from src.data.eda import majority
from src.data.load import ROOT, SLOT_RE, configured_locales, load_config, load_locale, parse_slots, strip_markup

SPLITS_DIR = ROOT / "data" / "splits"
PROCESSED_DIR = ROOT / "data" / "processed"


def load_processed(locale, partition):
    with open(PROCESSED_DIR / f"{locale}.{partition}.jsonl", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def spans_in_utt(utt, annot_utt):
    """Return [[start, end, label], ...] character spans of each slot inside `utt`, or None if malformed.

    Only non-whitespace characters are matched, because annotations add spaces that `utt`
    lacks (ja-JP writes "[date : 今週] は ..." for "今週は...").
    """
    if parse_slots(annot_utt) is None:
        return None
    if "".join(strip_markup(annot_utt).split()) != "".join(utt.split()):
        return None
    positions = [i for i, ch in enumerate(utt) if not ch.isspace()]
    spans, consumed, last = [], 0, 0
    for m in SLOT_RE.finditer(annot_utt):
        consumed += len("".join(annot_utt[last:m.start()].split()))
        value_len = len("".join(m.group(2).split()))
        if value_len == 0:
            return None
        spans.append([positions[consumed], positions[consumed + value_len - 1] + 1, m.group(1)])
        consumed += value_len
        last = m.end()
    return spans


def bio_labels(offsets, spans, tag2id):
    """BIO tag id per token from (start, end) character offsets; (0, 0) marks special tokens.

    A token belongs to a slot if it starts inside the slot's span: the first such token gets B-,
    later ones I-. Special tokens get -100 so the loss ignores them.
    """
    labels, begun = [], set()
    for start, end in offsets:
        if start == end:
            labels.append(-100)
            continue
        tag = "O"
        for i, (s, e, label) in enumerate(spans):
            if s <= start < e:
                tag = ("I-" if i in begun else "B-") + label
                begun.add(i)
                break
        labels.append(tag2id[tag])
    return labels


def lost_spans(offsets, spans):
    """Number of slots that no token starts inside, i.e. slots the BIO labels cannot represent."""
    starts = [s for s, e in offsets if s != e]
    return sum(not any(s <= t < e for t in starts) for s, e, _ in spans)


def ragged_spans(offsets, spans):
    """Number of slots whose start or end falls inside a token, so a perfect tagging still mis-sizes the span."""
    starts = {s for s, e in offsets if s != e}
    ends = {e for s, e in offsets if s != e}
    return sum(s not in starts or e not in ends for s, e, _ in spans)


def checksum(examples):
    lines = (json.dumps(ex, ensure_ascii=False, sort_keys=True) for ex in sorted(examples, key=lambda x: int(x["id"])))
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def build(cfg):
    """Process every configured locale. Returns (examples by locale, excluded counts, test subsets)."""
    data, excluded = {}, {}
    subsets = {"seen_in_train": {}, "judge_flagged": {}}
    for loc in configured_locales(cfg):
        records = load_locale(cfg, loc)
        ids = [r["id"] for r in records]
        if len(ids) != len(set(ids)):
            raise ValueError(f"{loc}: an id appears more than once, so it could sit in two partitions")
        examples, bad = [], 0
        for r in records:
            spans = spans_in_utt(r["utt"], r["annot_utt"])
            if spans is None:
                bad += 1  # reported by main(), never dropped silently
                continue
            examples.append({"id": r["id"], "locale": loc, "partition": r["partition"],
                             "intent": r["intent"], "utt": r["utt"], "spans": spans})
        data[loc], excluded[loc] = examples, bad

        norm = lambda r: " ".join(r["utt"].split()).casefold()  # noqa: E731
        train_texts = {norm(r) for r in records if r["partition"] == "train"}
        subsets["seen_in_train"][loc] = sorted(
            (r["id"] for r in records if r["partition"] == "test" and norm(r) in train_texts), key=int)
        subsets["judge_flagged"][loc] = sorted(
            (r["id"] for r in records if r["partition"] == "test" and (
                majority(r.get("judgments", []), lambda j: j.get("intent_score") == 0)
                or majority(r.get("judgments", []), lambda j: j.get("slots_score") == 0)
                or majority(r.get("judgments", []), lambda j: "target" not in str(j.get("language_identification", "")))
            )), key=int)
    return data, excluded, subsets


def label_maps(data):
    train = [ex for examples in data.values() for ex in examples if ex["partition"] == "train"]
    intents = sorted({ex["intent"] for ex in train})
    slot_types = sorted({label for examples in data.values() for ex in examples for _, _, label in ex["spans"]})
    return {"intents": intents, "slot_tags": ["O"] + [f"{p}-{t}" for t in slot_types for p in ("B", "I")]}


def main():
    cfg = load_config()
    data, excluded, subsets = build(cfg)
    labels = label_maps(data)

    SPLITS_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    sums = {}
    for loc, examples in data.items():
        for part in cfg["dataset"]["partitions"]:
            subset = [ex for ex in examples if ex["partition"] == part]
            sums[f"{loc}/{part}"] = checksum(subset)
            with open(PROCESSED_DIR / f"{loc}.{part}.jsonl", "w", encoding="utf-8") as f:
                for ex in subset:
                    f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    write = lambda name, obj: (SPLITS_DIR / name).write_text(  # noqa: E731
        json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write("labels.json", labels)
    write("checksums.json", sums)
    write("test_subsets.json", subsets)

    print(f"{len(labels['intents'])} intents, {len(labels['slot_tags'])} slot tags")
    for loc, examples in data.items():
        print(f"{loc}: {len(examples)} examples, {excluded[loc]} excluded as malformed, "
              f"{len(subsets['seen_in_train'][loc])} test seen in train, "
              f"{len(subsets['judge_flagged'][loc])} test judge-flagged")


if __name__ == "__main__":
    main()
