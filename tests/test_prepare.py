from src.data.prepare import bio_labels, lost_spans, ragged_spans, spans_in_utt

TAGS = ["O", "B-date", "I-date", "B-time", "I-time"]
TAG2ID = {t: i for i, t in enumerate(TAGS)}


def test_spans_english():
    utt = "wake me up at five am this week"
    spans = spans_in_utt(utt, "wake me up at [time : five am] [date : this week]")
    assert spans == [[14, 21, "time"], [22, 31, "date"]]
    assert [utt[s:e] for s, e, _ in spans] == ["five am", "this week"]


def test_spans_japanese_ignores_annotation_spaces():
    utt = "今週は午前五時に起こして"
    spans = spans_in_utt(utt, "[date : 今週] は [time : 午前五時] に起こして")
    assert [utt[s:e] for s, e, _ in spans] == ["今週", "午前五時"]
    assert [label for _, _, label in spans] == ["date", "time"]


def test_spans_reject_mismatch_and_malformed():
    assert spans_in_utt("wake me at five", "wake me at [time : six]") is None
    assert spans_in_utt("wake me at five", "wake me at [time : five") is None


def test_bio_labels_from_offsets():
    # [CLS] wake me up at five am this week [SEP], word-level tokens for clarity.
    offsets = [(0, 0), (0, 4), (5, 7), (8, 10), (11, 13), (14, 18), (19, 21), (22, 26), (27, 31), (0, 0)]
    spans = [[14, 21, "time"], [22, 31, "date"]]
    tags = [TAGS[i] if i != -100 else None for i in bio_labels(offsets, spans, TAG2ID)]
    assert tags == [None, "O", "O", "O", "O", "B-time", "I-time", "B-date", "I-date", None]


def test_subword_tokens_continue_with_inside_tag():
    offsets = [(0, 2), (2, 4), (4, 5)]  # one slot split into two subwords, then one outside token
    assert bio_labels(offsets, [[0, 4, "date"]], TAG2ID) == [TAG2ID["B-date"], TAG2ID["I-date"], TAG2ID["O"]]


def test_lost_span_when_no_token_starts_inside():
    offsets = [(0, 3), (3, 6)]
    assert lost_spans(offsets, [[1, 3, "date"]]) == 1  # slot begins mid-token
    assert lost_spans(offsets, [[3, 6, "date"]]) == 0


def test_ragged_span_when_slot_ends_mid_token():
    # XLM-R tokenises 午前|五|時に, so the slot 午前五時 (chars 3-7) ends inside the token 時に (6-8).
    offsets = [(0, 0), (3, 5), (5, 6), (6, 8), (0, 0)]
    assert ragged_spans(offsets, [[3, 7, "time"]]) == 1
    assert ragged_spans(offsets, [[3, 6, "time"]]) == 0
