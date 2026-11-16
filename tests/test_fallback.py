import numpy as np
import pytest

from src.models.fallback import choose_threshold, ece, fit_temperature, score_methods, softmax


def test_fit_temperature_recovers_overconfidence():
    rng = np.random.default_rng(0)
    base = rng.normal(size=(4000, 5)) * 2
    gold = np.array([rng.choice(5, p=p) for p in softmax(base)])
    # Logits three times too sharp should be cooled by a temperature near 3.
    assert fit_temperature(base * 3, gold) == pytest.approx(3.0, rel=0.15)


def test_ece_zero_when_confidence_matches_accuracy():
    probs = np.array([[0.75, 0.25]] * 4)
    gold = np.array([0, 0, 0, 1])  # 75% correct at 75% confidence
    assert ece(probs, gold)[0] == pytest.approx(0.0)


def test_choose_threshold_prefers_coverage_among_safe_thresholds():
    dev_conf = np.array([0.9, 0.8, 0.7, 0.6])
    oos_conf = np.array([0.1, 0.2, 0.3, 0.5])
    (t, routed, answered), _ = choose_threshold(dev_conf, oos_conf, target=0.95)
    assert routed == 1.0  # all out-of-scope inputs fall below t
    assert t == pytest.approx(0.51) and answered == 1.0  # lowest safe threshold keeps every dev input answered


def test_score_methods_rank_a_peaked_input_above_a_flat_one():
    logits = np.array([[8.0, 0.0, 0.0], [1.0, 1.0, 1.0]])  # confident vs. completely unsure
    s = score_methods(logits, temperature=1.0)
    assert s["max_prob"][0] > s["max_prob"][1]
    assert s["margin"][0] > s["margin"][1] and s["margin"][1] == pytest.approx(0.0)
    assert s["energy"][1] == pytest.approx(1.0 + np.log(3))  # logsumexp of three equal logits


def test_choose_threshold_falls_back_to_best_routing_when_target_unreachable():
    (t, routed, _), _ = choose_threshold(np.array([0.9]), np.array([0.99]), target=0.95)
    assert routed == 0.0 and t == pytest.approx(0.05)  # nothing routes; ties broken by coverage
