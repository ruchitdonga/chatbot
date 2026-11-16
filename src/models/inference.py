"""Predict intent, confidence and slot spans with a saved joint model.

CLI: python -m src.models.inference artifacts/runs/<run_name>/best "wake me up at five am"
Confidence is the raw softmax maximum; it is not calibrated until Phase 7.
"""
import json
import sys

import torch
from transformers import AutoTokenizer

from src.models.joint_model import load
from src.models.spans import decode_spans


class Predictor:
    def __init__(self, checkpoint, device=None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model, self.meta = load(checkpoint, self.device)
        self.tokenizer = AutoTokenizer.from_pretrained(self.meta["encoder"])

    @torch.no_grad()
    def predict(self, texts):
        enc = self.tokenizer(texts, truncation=True, max_length=self.meta["max_length"], padding=True,
                             return_offsets_mapping=True, return_tensors="pt")
        offsets = enc.pop("offset_mapping").tolist()
        out = self.model(enc["input_ids"].to(self.device), enc["attention_mask"].to(self.device))
        probs = out["intent_logits"].float().softmax(-1)
        tags = out["slot_logits"].argmax(-1).tolist()
        names = self.meta["labels"]
        results = []
        for i, text in enumerate(texts):
            confidence, intent = probs[i].max(-1)
            spans = decode_spans([names["slot_tags"][t] for t in tags[i]], offsets[i])
            results.append({"intent": names["intents"][int(intent)], "confidence": round(float(confidence), 4),
                            "slots": [{"label": lab, "value": text[s:e], "start": s, "end": e} for s, e, lab in spans]})
        return results


if __name__ == "__main__":
    print(json.dumps(Predictor(sys.argv[1]).predict(sys.argv[2:]), ensure_ascii=False, indent=2))
