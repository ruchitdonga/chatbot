"""Load MASSIVE records for the configured locales and read the inline slot markup."""
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]

# MASSIVE marks slots inline as "[label : value]".
SLOT_RE = re.compile(r"\[\s*([^\[\]:]+?)\s*:\s*([^\[\]]*?)\s*\]")


def load_config(path=ROOT / "configs" / "project.yaml"):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def configured_locales(cfg):
    langs = cfg["languages"]
    return langs["high_resource"] + langs["mid_resource"] + langs["low_resource"]


def locale_file(cfg, locale):
    ds = cfg["dataset"]
    return ROOT / ds["raw_dir"] / ds["version"] / "data" / f"{locale}.jsonl"


def load_locale(cfg, locale):
    with open(locale_file(cfg, locale), encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def parse_slots(annot_utt):
    """Return [(label, value), ...] from the markup, or None if any bracket is left unmatched."""
    leftover = SLOT_RE.sub("", annot_utt)
    if "[" in leftover or "]" in leftover:
        return None
    return SLOT_RE.findall(annot_utt)


def strip_markup(annot_utt):
    """Replace each "[label : value]" with its value."""
    return SLOT_RE.sub(lambda m: m.group(2), annot_utt)
