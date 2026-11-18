"""Language identification for the configured locales (FR-4).

Unicode script settles Amharic, Tamil, Hindi, Arabic and Japanese (kana, or a short kanji-only text such as "寿司");
Swahili marker words (configs/swahili_words.txt) settle Swahili, which fastText misreads as English when short;
fastText lid.176 decides the rest, restricted to the configured locales. Text whose top fastText language is outside
them, with enough probability, is reported as unsupported. fastText's Python predict() breaks on NumPy 2, so the
underlying model call (f.predict) is used directly.
"""
import re

SCRIPT_RULES = [("am-ET", r"[ሀ-፿]"), ("ta-IN", r"[஀-௿]"), ("hi-IN", r"[ऀ-ॿ]"),
                ("ar-SA", r"[؀-ۿ]"), ("ja-JP", r"[぀-ヿ]")]
# Kanji alone is Chinese or Japanese; Chinese is not supported, so only short words ("寿司", "七百") count as Japanese.
SHORT_KANJI = re.compile(r"[一-鿿々]{1,6}")


def rule_locale(clean, locales, swahili_words=frozenset()):
    """The locale settled without fastText (script, short kanji, Swahili words), or None."""
    for locale, pattern in SCRIPT_RULES:
        if locale in locales and re.search(pattern, clean):
            return locale
    if "ja-JP" in locales and SHORT_KANJI.fullmatch(clean.replace(" ", "")):
        return "ja-JP"
    if "sw-KE" in locales and set(re.findall(r"[a-z]+", clean.casefold())) & swahili_words:
        return "sw-KE"
    return None


def read_words(path):
    """One word per line; lines starting with # are comments."""
    return frozenset(w for w in path.read_text(encoding="utf-8").split("\n") if w and not w.startswith("#"))


class LanguageId:
    def __init__(self, model_path, locales, unsupported_min_prob, swahili_words=frozenset()):
        import fasttext  # here, so rule_locale can be used and tested without the fastText package
        self.model = fasttext.load_model(str(model_path))
        self.locales = list(locales)
        self.code_to_locale = {loc.split("-")[0]: loc for loc in self.locales}
        self.unsupported_min_prob = unsupported_min_prob
        self.swahili_words = frozenset(swahili_words)

    def scores(self, text):
        """fastText probability per language code, e.g. {"en": 0.97, ...}."""
        # The native call needs the trailing newline that fastText's Python wrapper would normally add.
        return {label.replace("__label__", ""): prob
                for prob, label in self.model.f.predict(text + "\n", -1, 0.0, "strict")}

    def detect(self, text):
        """Return (locale, supported). locale is None when the text is empty or the language unsupported."""
        clean = " ".join(text.split())
        if not clean:
            return None, False
        settled = rule_locale(clean, self.locales, self.swahili_words)
        if settled:
            return settled, True
        scores = self.scores(clean)
        if not scores:
            return None, False
        top = max(scores, key=scores.get)
        if top not in self.code_to_locale and scores[top] >= self.unsupported_min_prob:
            return None, False
        best = max(self.code_to_locale, key=lambda code: scores.get(code, 0.0))
        return self.code_to_locale[best], True
