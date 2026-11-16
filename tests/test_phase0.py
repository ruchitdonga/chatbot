"""Phase 0 checks: the config defines ten locales and every spec requirement is traced."""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_config():
    return yaml.safe_load((ROOT / "configs" / "project.yaml").read_text(encoding="utf-8"))


def test_ten_unique_locales():
    langs = load_config()["languages"]
    locales = langs["high_resource"] + langs["mid_resource"] + langs["low_resource"]
    assert len(locales) == 10
    assert len(set(locales)) == 10


def test_every_requirement_id_is_traced():
    text = (ROOT / "reports" / "requirements.md").read_text(encoding="utf-8")
    expected = (
        [f"OBJ-{i}" for i in range(1, 7)]
        + [f"FR-{i}" for i in range(1, 7)]
        + [f"NFR-{i}" for i in range(1, 7)]
        + [f"ETH-{i}" for i in range(1, 5)]
    )
    missing = [i for i in expected if not re.search(rf"\b{re.escape(i)}\b", text)]
    assert not missing, f"untraced requirement IDs: {missing}"
