import pytest

from src.models.evaluate import fairness, mcnemar, metrics, span_f1


def rec(locale, gold, pred, gold_tags=("B-time",), pred_tags=("B-time",), gold_spans=((0, 4, "time"),),
        pred_spans=((0, 4, "time"),)):
    return {"locale": locale, "gold_intent": gold, "pred_intent": pred, "gold_tags": list(gold_tags),
            "pred_tags": list(pred_tags), "gold_spans": [list(s) for s in gold_spans],
            "pred_spans": [list(s) for s in pred_spans]}


def test_span_f1_requires_exact_boundaries():
    exact = rec("en-US", "a", "a")
    off_by_one = rec("ja-JP", "a", "a", pred_spans=((0, 5, "time"),))
    assert span_f1([exact]) == 1.0
    assert span_f1([off_by_one]) == 0.0
    assert span_f1([exact, off_by_one]) == pytest.approx(0.5)


def test_metrics_mean_is_unweighted_over_locales():
    records = [rec("en-US", "a", "a")] * 3 + [rec("sw-KE", "a", "b")]
    result = metrics(records)
    assert result["by_locale"]["en-US"]["intent_accuracy"] == 1.0
    assert result["by_locale"]["sw-KE"]["intent_accuracy"] == 0.0
    assert result["mean"]["intent_accuracy"] == 0.5


def test_fairness_flags_locales_more_than_threshold_below_mean():
    by_loc = {"a": {"intent_accuracy": 0.90, "slot_f1": 0.8}, "b": {"intent_accuracy": 0.88, "slot_f1": 0.8},
              "c": {"intent_accuracy": 0.60, "slot_f1": 0.8}}
    out = fairness(by_loc, max_gap_pp=10)
    assert list(out["intent_accuracy"]["flagged"]) == ["c"]  # mean 0.793, c is 19.3 pp below
    assert out["slot_f1"]["flagged"] == {}


def test_mcnemar_counts_discordant_pairs():
    result = mcnemar([True, True, True, False], [False, False, True, False])
    assert (result["model_only_correct"], result["baseline_only_correct"]) == (2, 0)
    assert result["p_value"] == pytest.approx(0.5)  # 2 of 2 discordant pairs, two-sided exact test
    assert mcnemar([True], [True])["p_value"] == 1.0
