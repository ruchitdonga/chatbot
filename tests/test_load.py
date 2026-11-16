from src.data.load import parse_slots, strip_markup


def test_parse_slots_reads_labels_and_values():
    assert parse_slots("wake me up at [time : five am] [date : this week]") == [
        ("time", "five am"),
        ("date", "this week"),
    ]


def test_parse_slots_without_slots():
    assert parse_slots("quiet") == []


def test_parse_slots_flags_unmatched_bracket():
    assert parse_slots("wake me up at [time : five am") is None


def test_strip_markup_keeps_values_only():
    # Japanese annotations add spaces around slots that the raw utterance does not have.
    assert strip_markup("[date : 今週] は [time : 午前五時] に起こして") == "今週 は 午前五時 に起こして"
