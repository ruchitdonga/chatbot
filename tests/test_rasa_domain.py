"""Phase 9: every Rasa reply exists in all ten languages, and the disclosure matches configs/disclosure.yaml (ETH-4)."""
import yaml

from src.data.load import ROOT, configured_locales, load_config

DOMAIN = yaml.safe_load((ROOT / "rasa" / "domain.yml").read_text(encoding="utf-8"))


def variants(name):
    """locale -> text; the unconditioned variation is en-US."""
    out = {}
    for v in DOMAIN["responses"][name]:
        locale = v["condition"][0]["value"] if "condition" in v else "en-US"
        assert locale not in out, f"{name}: two variations for {locale}"
        out[locale] = v["text"]
    return out


def test_every_response_covers_all_locales():
    locales = set(configured_locales(load_config()))
    for name in DOMAIN["responses"]:
        assert set(variants(name)) == locales, name


def test_disclosure_matches_config():
    disclosure = yaml.safe_load((ROOT / "configs" / "disclosure.yaml").read_text(encoding="utf-8"))["message"]
    assert variants("utter_disclosure") == disclosure


def test_placeholders_identical_across_locales():
    for name in DOMAIN["responses"]:
        texts = variants(name)
        expected = sorted(p.split("}")[0] for p in texts["en-US"].split("{")[1:])
        for locale, text in texts.items():
            assert sorted(p.split("}")[0] for p in text.split("{")[1:]) == expected, (name, locale)
