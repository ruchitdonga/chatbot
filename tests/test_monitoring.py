"""Phase 11: PSI and retraining triggers on synthetic counts (no model or data needed)."""
from collections import Counter

from src.monitoring.drift_report import profile, psi, triggers

CFG = {"psi_threshold": 0.25, "min_utterances": 1000, "fallback_rate_multiplier": 2.0}


def rows(locales, intent="takeaway_order", handoff=False):
    return [{"locale": loc, "intent": intent, "slot_labels": ["food_type"], "handoff": handoff} for loc in locales]


def test_psi():
    even = Counter({"en-US": 500, "sw-KE": 500})
    assert psi(even, even) == 0
    assert psi(even, Counter({"en-US": 100, "sw-KE": 900})) > 0.25  # surge
    assert psi(even, Counter({"en-US": 480, "sw-KE": 520})) < 0.01  # noise
    assert psi(even, Counter({"en-US": 500, "sw-KE": 400, "ru": 100})) > 0  # unseen category, no division by zero


def test_triggers():
    ref = profile(rows(["en-US", "sw-KE"] * 1000))
    normal = triggers(ref, profile(rows(["en-US", "sw-KE"] * 600)), 0.1, CFG)
    assert normal["fired"] == [] and normal["enough_data"]
    surge = triggers(ref, profile(rows(["sw-KE"] * 1100 + ["en-US"] * 100, handoff=True)), 0.1, CFG)
    assert surge["fired"] == ["PSI locale > 0.25", "fallback rate >= 2.0x baseline"]
    small = triggers(ref, profile(rows(["sw-KE"] * 50, handoff=True)), 0.1, CFG)
    assert not small["enough_data"] and small["fired"] == []  # too few utterances to decide
