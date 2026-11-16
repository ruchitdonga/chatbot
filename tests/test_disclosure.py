"""ETH-4: every configured locale has an AI-disclosure message and a review status."""
import yaml

from src.data.load import ROOT, configured_locales, load_config


def test_disclosure_covers_every_locale():
    disclosure = yaml.safe_load((ROOT / "configs" / "disclosure.yaml").read_text(encoding="utf-8"))
    for locale in configured_locales(load_config()):
        assert disclosure["message"].get(locale, "").strip(), f"missing disclosure for {locale}"
        assert disclosure["review_status"].get(locale), f"missing review status for {locale}"
