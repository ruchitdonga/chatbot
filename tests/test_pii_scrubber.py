"""NFR-5 / ETH-3: no personal data survives scrubbing of a synthetic PII-bearing conversation."""
from src.data.load import load_config
from src.privacy.pii_scrubber import pii_slot_set, scrub

PII_SLOTS = pii_slot_set(load_config())

# Synthetic turns with the slot spans an NLU model would predict. All values are invented.
CONVERSATION = [
    ("hi my name is Priya Sharma", [(14, 26, "person")]),
    ("email me at priya.sharma@example.com", []),
    ("call +91 98765 43210 about order ORD-48213", []),
    ("ship it to 221 Baker Street in London", [(31, 37, "place_name")]),
    ("remind my mother", [(10, 16, "relation")]),
    ("set an alarm for seven am", [(17, 25, "time")]),
]
SECRETS = ["Priya", "Sharma", "priya.sharma@example.com", "98765", "43210", "48213", "221 Baker", "London", "mother"]


def test_no_personal_data_survives():
    scrubbed = " | ".join(scrub(text, slots, PII_SLOTS) for text, slots in CONVERSATION)
    leaked = [s for s in SECRETS if s in scrubbed]
    assert not leaked, f"leaked: {leaked}"


def test_non_personal_text_and_slots_untouched():
    assert scrub("set an alarm for seven am", [(17, 25, "time")], PII_SLOTS) == "set an alarm for seven am"
    assert scrub("wake me at 7 on day 12") == "wake me at 7 on day 12"


def test_mask_tokens():
    assert scrub("hi my name is Priya Sharma", [(14, 26, "person")], PII_SLOTS) == "hi my name is [PERSON]"
    assert scrub("mail a.b@example.org") == "mail [EMAIL_ADDRESS]"
    assert scrub("order ORD-48213 please") == "order [ORDER_ID] please"
    assert scrub("ship to 221 Baker Street") == "ship to [ADDRESS]"
