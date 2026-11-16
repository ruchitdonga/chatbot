"""Serving API: language hint, empty and unsupported input, and logs that hold no personal data (NFR-5)."""
import json

from fastapi.testclient import TestClient

from src.data.load import load_config
from src.serving.app import create_app


class FakeNLU:
    def __init__(self):
        self.calls = 0

    def predict(self, text, temperature, threshold):
        self.calls += 1
        start = text.find("Priya")
        slots = [{"label": "person", "value": text[start:start + 12], "start": start, "end": start + 12}] if start >= 0 else []
        return {"intent": "takeaway_order", "confidence": 0.9, "energy": 9.0, "slots": slots,
                "handoff": False, "handoff_reason": None}


class FakeLID:
    def detect(self, text):
        if not text.strip():
            return None, False
        return (None, False) if text.startswith("Я") else ("en-US", True)


def client(tmp_path):
    cfg = load_config()
    cfg["serving"]["event_log"] = str(tmp_path / "events.jsonl")
    nlu = FakeNLU()
    return TestClient(create_app(nlu=nlu, lid=FakeLID(), cfg=cfg)), nlu, tmp_path / "events.jsonl"


def test_language_hint_overrides_detection(tmp_path):
    c, _, _ = client(tmp_path)
    body = c.post("/predict", json={"text": "nataka pizza", "language": "sw-KE"}).json()
    assert body["locale"] == "sw-KE" and body["language_source"] == "hint"


def test_empty_and_unsupported_inputs_go_to_handoff_without_the_model(tmp_path):
    c, nlu, _ = client(tmp_path)
    assert c.post("/predict", json={"text": "   "}).json()["handoff_reason"] == "empty"
    assert c.post("/predict", json={"text": "Я хочу вернуть деньги"}).json()["handoff_reason"] == "unsupported_language"
    assert nlu.calls == 0


def test_log_holds_only_allowed_fields_and_no_personal_data(tmp_path):
    c, _, log = client(tmp_path)
    text = "order a pizza for Priya Sharma at priya@example.com"
    body = c.post("/predict", json={"text": text}).json()
    assert body["slots"][0]["value"] == "Priya Sharma"  # the caller still gets the slot value
    line = log.read_text(encoding="utf-8")
    event = json.loads(line)
    assert set(event) == set(load_config()["logging"]["allowed_fields"])
    assert event["slot_labels"] == ["person"]
    assert "Priya" not in line and "example.com" not in line and "pizza" not in line
