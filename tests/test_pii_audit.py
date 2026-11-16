from src.privacy.pii_audit import EMAIL_RE, LONG_NUMBER_RE, audit


def test_patterns():
    assert EMAIL_RE.search("mail jo.smith+x@example.co.uk now")
    assert not EMAIL_RE.search("jo at example dot com")
    assert LONG_NUMBER_RE.search("order 4512 3390 7")
    assert LONG_NUMBER_RE.search("call 555-012-3456")
    assert not LONG_NUMBER_RE.search("wake me at 7 on day 12")


def test_audit_counts_utterances_not_mentions():
    records = [
        {"utt": "email anna and bob", "annot_utt": "email [person : anna] and [person : bob]"},
        {"utt": "quiet", "annot_utt": "quiet"},
    ]
    result = audit(records, {"direct_identifier": ["person", "email_address"]})
    assert result["any_pii_slot"] == 1
    assert result["slots"]["person"] == 1
