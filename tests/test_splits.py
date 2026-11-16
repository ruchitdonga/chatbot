"""NFR-6: the frozen splits match their committed checksums. Skipped where the raw data is absent (e.g. CI)."""
import json

import pytest

from src.data.load import configured_locales, load_config, locale_file
from src.data.prepare import SPLITS_DIR, build, checksum

CFG = load_config()
RAW_PRESENT = all(locale_file(CFG, loc).exists() for loc in configured_locales(CFG))


@pytest.mark.skipif(not RAW_PRESENT, reason="raw MASSIVE files not downloaded")
def test_splits_match_committed_checksums():
    committed = json.loads((SPLITS_DIR / "checksums.json").read_text(encoding="utf-8"))
    data, excluded, _ = build(CFG)
    assert not any(excluded.values()), f"malformed annotations: {excluded}"
    for loc, examples in data.items():
        for part in CFG["dataset"]["partitions"]:
            subset = [ex for ex in examples if ex["partition"] == part]
            assert checksum(subset) == committed[f"{loc}/{part}"], f"{loc}/{part} changed"
