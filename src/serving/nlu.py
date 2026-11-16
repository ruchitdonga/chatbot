"""ONNX Runtime NLU for serving: intent, calibrated confidence, energy, slots and the handoff decision.

Torch-free, so the serving image does not need PyTorch.
"""
import json
from pathlib import Path

import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer

from src.models.spans import decode_spans

OOS_LABEL = "out_of_scope"


class OnnxNLU:
    def __init__(self, model_dir, threads=None, quantized=True):
        model_dir = Path(model_dir)
        self.meta = json.loads((model_dir / "meta.json").read_text(encoding="utf-8"))
        # Saved next to the model by export_onnx (offline container); older exports fall back to the hub name.
        local = (model_dir / "tokenizer.json").exists()
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir if local else self.meta["encoder"])
        opts = ort.SessionOptions()
        if threads:
            opts.intra_op_num_threads = threads
            opts.inter_op_num_threads = 1
        name = "model.quant.onnx" if quantized else "model.onnx"
        self.session = ort.InferenceSession(str(model_dir / name), opts, providers=["CPUExecutionProvider"])

    def logits(self, texts):
        """(intent logits, slot logits, padded offsets) for a batch of texts."""
        enc = self.tokenizer(texts, truncation=True, max_length=self.meta["max_length"], padding=True,
                             return_offsets_mapping=True, return_tensors="np")
        intent, slots = self.session.run(None, {"input_ids": enc["input_ids"].astype(np.int64),
                                                "attention_mask": enc["attention_mask"].astype(np.int64)})
        return intent, slots, enc["offset_mapping"].tolist()

    def predict(self, text, temperature, threshold):
        """One utterance -> intent, calibrated confidence, energy, slots, and whether to hand off and why."""
        intent_logits, slot_logits, offsets = self.logits([text])
        z = intent_logits[0] / temperature
        zmax = z.max()
        energy = float(zmax + np.log(np.exp(z - zmax).sum()))
        probs = np.exp(z - zmax) / np.exp(z - zmax).sum()
        k = int(probs.argmax())
        intent = self.meta["labels"]["intents"][k]
        tags = [self.meta["labels"]["slot_tags"][t] for t in slot_logits[0].argmax(-1)]
        spans = decode_spans(tags, offsets[0])
        reason = "out_of_scope" if intent == OOS_LABEL else ("low_confidence" if energy < threshold else None)
        return {"intent": intent, "confidence": round(float(probs[k]), 4), "energy": round(energy, 3),
                "slots": [{"label": lab, "value": text[s:e], "start": s, "end": e} for s, e, lab in spans],
                "handoff": reason is not None, "handoff_reason": reason}
