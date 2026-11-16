"""Language identification for the configured locales (FR-4).

Unicode script settles Amharic, Tamil, Hindi, Arabic and Japanese (kana); fastText lid.176 decides the rest,
restricted to the configured locales. Text whose top fastText language is outside them, with enough
probability, is reported as unsupported. fastText's Python predict() breaks on NumPy 2, so the underlying
model call (f.predict) is used directly.
"""
import re

import fasttext

SCRIPT_RULES = [("am-ET", r"[ሀ-፿]"), ("ta-IN", r"[஀-௿]"), ("hi-IN", r"[ऀ-ॿ]"),
                ("ar-SA", r"[؀-ۿ]"), ("ja-JP", r"[぀-ヿ]")]


class LanguageId:
    def __init__(self, model_path, locales, unsupported_min_prob):
        self.model = fasttext.load_model(str(model_path))
        self.locales = list(locales)
        self.code_to_locale = {loc.split("-")[0]: loc for loc in self.locales}
        self.unsupported_min_prob = unsupported_min_prob

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
        for locale, pattern in SCRIPT_RULES:
            if locale in self.locales and re.search(pattern, clean):
                return locale, True
        scores = self.scores(clean)
        if not scores:
            return None, False
        top = max(scores, key=scores.get)
        if top not in self.code_to_locale and scores[top] >= self.unsupported_min_prob:
            return None, False
        best = max(self.code_to_locale, key=lambda code: scores.get(code, 0.0))
        return self.code_to_locale[best], True
