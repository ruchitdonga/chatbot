"""Language rules applied before fastText: script, short kanji, Swahili marker words (no fastText model needed)."""
from src.data.load import ROOT
from src.serving.language_id import read_words, rule_locale

LOCALES = ["en-US", "es-ES", "de-DE", "fr-FR", "ja-JP", "hi-IN", "ar-SA", "sw-KE", "am-ET", "ta-IN"]
SWAHILI = read_words(ROOT / "configs" / "swahili_words.txt")


def test_rules():
    assert rule_locale("寿司", LOCALES) == "ja-JP" and rule_locale("七百", LOCALES) == "ja-JP"  # kanji only
    assert rule_locale("这是一个很长的中文句子我们不支持", LOCALES) is None  # long kanji-only text: fastText decides
    assert rule_locale("ピザ", LOCALES) == "ja-JP" and rule_locale("बिरयानी", LOCALES) == "hi-IN"
    assert rule_locale("Nataka kuagiza Vada Pav", LOCALES, SWAHILI) == "sw-KE"
    assert rule_locale("Oda yangu iko wapi?", LOCALES, SWAHILI) == "sw-KE"
    for text in ["I want a vada pav", "quiero una pizza", "ich möchte eine pizza", "je veux une pizza",
                 "mujhe biryani chahiye", "samosa kitne ka hai"]:
        assert rule_locale(text, LOCALES, SWAHILI) is None, text  # fastText (and the Hinglish rule) decide these


def test_swahili_words_file():
    assert len(SWAHILI) > 300 and "nataka" in SWAHILI
    assert not SWAHILI & {"hai", "kya", "mujhe", "chahiye", "the", "and", "pizza", "biryani"}
