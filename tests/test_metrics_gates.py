"""Phase 11 CI gates on the committed results of the deployed model (reports/metrics.json, reports/fallback.json).

A target passes if met. A missed target passes only if it is recorded in targets.known_misses with its real value,
and the committed result has not dropped below that value. A recorded miss that is now met fails, so the entry is
removed rather than left stale. Targets themselves are never changed here (guide rule 5).
"""
import json
from pathlib import Path

import pytest

from src.data.load import ROOT, load_config

CFG = load_config()
TARGETS = CFG["targets"]
MISSES = TARGETS.get("known_misses", {})
RUN = Path(CFG["models"]["deployed_checkpoint"]).parent.name
TEST = json.loads((ROOT / "reports" / "metrics.json").read_text(encoding="utf-8"))["test"][RUN]
FALLBACK = json.loads((ROOT / "reports" / "fallback.json").read_text(encoding="utf-8"))


def gate(name, value):
    target = TARGETS[name]
    if value >= target:
        assert name not in MISSES, f"{name} = {value:.4f} now meets {target}: remove it from targets.known_misses"
        return
    assert name in MISSES, f"{name} = {value:.4f} misses {target} and is not recorded in targets.known_misses"
    recorded = MISSES[name]["recorded"]
    assert value >= recorded, f"{name} = {value:.4f} dropped below the recorded {recorded}"


def test_fallback_report_is_for_deployed_model():
    assert Path(FALLBACK["checkpoint"]).parent.name == RUN


def test_intent_accuracy_gate():
    gate("mean_intent_accuracy", TEST["full"]["mean"]["intent_accuracy"])


def test_slot_f1_gate():
    gate("mean_slot_micro_f1", TEST["full"]["mean"]["slot_f1"])


@pytest.mark.parametrize("metric", ["intent_accuracy", "slot_f1"])
def test_fairness_gate(metric):
    """NFR-2: no locale more than max_gap_below_mean_pp below the mean (recomputed, not read from the flags)."""
    by_locale = {loc: m[metric] for loc, m in TEST["full"]["by_locale"].items()}
    mean = TEST["full"]["mean"][metric]
    worst = min(by_locale, key=by_locale.get)
    gap_pp = (mean - by_locale[worst]) * 100
    assert gap_pp <= TARGETS["max_gap_below_mean_pp"], f"{metric}: {worst} is {gap_pp:.1f} pp below the mean"


def test_safe_fallback_gate():
    gate("safe_fallback_routing", FALLBACK["heldout_routing"])
