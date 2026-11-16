import numpy as np

from src.models.baselines import majority_predictions, mean_pool, scores


def ex(locale, intent):
    return {"locale": locale, "intent": intent}


def test_majority_is_per_locale():
    train = [ex("en-US", "a"), ex("en-US", "a"), ex("en-US", "b"), ex("sw-KE", "b"), ex("sw-KE", "b")]
    assert majority_predictions(train, [ex("en-US", "x"), ex("sw-KE", "x")]) == ["a", "b"]


def test_mean_pool():
    matrix = np.array([[0.0, 0.0], [2.0, 4.0], [4.0, 8.0]], dtype=np.float32)
    out = mean_pool([[1, 2], []], matrix)
    assert out.tolist() == [[3.0, 6.0], [0.0, 0.0]]


def test_scores_mean_is_unweighted_over_locales():
    examples = [ex("en-US", "a"), ex("en-US", "a"), ex("en-US", "a"), ex("en-US", "a"), ex("sw-KE", "a")]
    preds = ["a", "a", "a", "a", "b"]  # en-US 4/4 correct, sw-KE 0/1
    by_loc, mean = scores(examples, preds)
    assert by_loc["en-US"]["accuracy"] == 1.0 and by_loc["sw-KE"]["accuracy"] == 0.0
    assert mean["accuracy"] == 0.5  # not 0.8, which pooling examples would give
