"""Mask personal data in free text before it can reach a log.

Policy: reports/data_minimisation_policy.md. Raw text is never logged by design; this is the
defence in depth for text that leaks into error messages or debug output.
"""
import re

# Applied in order: emails first, addresses before bare numbers, order IDs before phone numbers.
PATTERNS = [
    ("[EMAIL_ADDRESS]", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
    # shortcut: English street words only; other languages rely on slot masking.
    ("[ADDRESS]", re.compile(
        r"\b\d{1,5}\s+(?:[^\W\d_]+\s+){0,3}(?:street|st|road|rd|avenue|ave|lane|ln|drive|dr|boulevard|blvd)\b",
        re.IGNORECASE)),
    ("[ORDER_ID]", re.compile(r"\b[A-Za-z]{2,5}-?\d{4,}\b")),
    ("[NUMBER]", re.compile(r"\+?\d(?:[\s().-]*\d){5,}")),
]


def pii_slot_set(cfg):
    """Flatten privacy.pii_slot_types from the config into one set of slot labels."""
    return {slot for group in cfg["privacy"]["pii_slot_types"].values() for slot in group}


def scrub(text, slots=(), pii_slots=frozenset()):
    """Mask predicted personal-data slots, then regex patterns.

    slots: (start, end, label) character spans predicted by the NLU model for this text.
    """
    for start, end, label in sorted(slots, reverse=True):  # right to left keeps offsets valid
        if label in pii_slots:
            text = text[:start] + f"[{label.upper()}]" + text[end:]
    for token, pattern in PATTERNS:
        text = pattern.sub(token, text)
    return text
