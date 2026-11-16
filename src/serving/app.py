"""Phase 8: FastAPI NLU service for the FeastFleet demo (fictional business). FR-1, FR-4, FR-5, FR-6.

POST /predict {"text": "...", "language": "sw-KE"}   (language is an optional hint that overrides detection)
-> {"locale", "language_source", "intent", "confidence", "energy", "slots", "handoff", "handoff_reason",
    "latency_ms", "model_version"}

Each request appends one line to serving.event_log containing only logging.allowed_fields (an allow-list),
so raw text and slot values are never stored.
Run from the repo root: uvicorn src.serving.app:create_app --factory --port 8000
"""
import json
import time
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel

from src.data.load import ROOT, configured_locales, load_config


class PredictRequest(BaseModel):
    text: str
    language: str | None = None


def create_app(nlu=None, lid=None, cfg=None):
    cfg = cfg or load_config()
    locales = configured_locales(cfg)
    run = Path(cfg["models"]["deployed_checkpoint"]).parent.name
    if nlu is None:
        from src.serving.nlu import OnnxNLU
        nlu = OnnxNLU(ROOT / cfg["serving"]["onnx_dir"] / run, threads=cfg["serving"]["intra_op_threads"])
    if lid is None:
        from src.serving.language_id import LanguageId
        lid = LanguageId(ROOT / cfg["serving"]["language_id_model"], locales,
                         cfg["fallback"]["unsupported_language_min_prob"])
    fallback, allowed = cfg["fallback"], cfg["logging"]["allowed_fields"]
    log_path = ROOT / cfg["serving"]["event_log"]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    app = FastAPI(title="FeastFleet NLU (fictional student demo)")

    @app.get("/health")
    def health():
        return {"status": "ok", "model_version": run}

    @app.post("/predict")
    def predict(req: PredictRequest):
        started = time.perf_counter()
        if req.language in locales:
            locale, supported, source = req.language, True, "hint"
        else:
            (locale, supported), source = lid.detect(req.text), "detected"
        if not req.text.strip():
            result = {"intent": None, "confidence": 0.0, "energy": None, "slots": [], "handoff": True,
                      "handoff_reason": "empty"}
        elif not supported:
            result = {"intent": None, "confidence": 0.0, "energy": None, "slots": [], "handoff": True,
                      "handoff_reason": "unsupported_language"}
        else:
            result = nlu.predict(req.text, fallback["temperature"], fallback["threshold"])
        latency = round((time.perf_counter() - started) * 1000, 1)
        event = {"intent": result["intent"], "slot_labels": [s["label"] for s in result["slots"]], "locale": locale,
                 "confidence": result["confidence"], "latency_ms": latency, "model_version": run,
                 "handoff": result["handoff"], "handoff_reason": result["handoff_reason"]}
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({k: event[k] for k in allowed}, ensure_ascii=False) + "\n")
        return {"locale": locale, "language_source": source, **result, "latency_ms": latency, "model_version": run}

    return app
