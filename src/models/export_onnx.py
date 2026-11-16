"""Phase 8: export the deployed checkpoint to ONNX, quantise it to INT8 and check it.

Writes <serving.onnx_dir>/<run>/model.onnx, model.quant.onnx and meta.json, compares fp32 and INT8 outputs
with PyTorch on dev sentences, and with --evaluate saves INT8 test predictions as run "<run>-int8" so
`python -m src.models.evaluate --partition test` reports the accuracy change.
Run from the repo root: python -m src.models.export_onnx [--evaluate]
"""
import argparse
import json
import shutil
from pathlib import Path

import numpy as np
import onnx
import torch
from onnxruntime.quantization import QuantType, quantize_dynamic
from transformers import AutoTokenizer

from src.data.load import ROOT, configured_locales, load_config
from src.data.prepare import load_processed
from src.models import joint_model
from src.models.evaluate import build_records
from src.models.train import encode
from src.serving.nlu import OnnxNLU


class LogitsOnly(torch.nn.Module):
    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(self, input_ids, attention_mask):
        out = self.model(input_ids, attention_mask)
        return out["intent_logits"], out["slot_logits"]


def export(checkpoint, out_dir):
    model, _ = joint_model.load(checkpoint, "cpu")
    out_dir.mkdir(parents=True, exist_ok=True)
    ids = torch.ones((2, 8), dtype=torch.long)
    torch.onnx.export(
        LogitsOnly(model).eval(), (ids, torch.ones_like(ids)), str(out_dir / "model.onnx"),
        input_names=["input_ids", "attention_mask"], output_names=["intent_logits", "slot_logits"],
        dynamic_axes={"input_ids": {0: "batch", 1: "seq"}, "attention_mask": {0: "batch", 1: "seq"},
                      "intent_logits": {0: "batch"}, "slot_logits": {0: "batch", 1: "seq"}},
        opset_version=17, dynamo=False)
    # Quantising every op cost ~10% intent agreement with PyTorch; keep embeddings and both heads in fp32.
    graph = onnx.load(str(out_dir / "model.onnx")).graph
    heads = [n.name for n in graph.node if "intent_head" in n.name or "slot_head" in n.name]
    quantize_dynamic(str(out_dir / "model.onnx"), str(out_dir / "model.quant.onnx"), weight_type=QuantType.QInt8,
                     per_channel=True, op_types_to_quantize=["MatMul"], nodes_to_exclude=heads)
    shutil.copy(Path(checkpoint) / "meta.json", out_dir / "meta.json")
    # Tokenizer next to the model so the serving container needs no Hugging Face download or cache (Phase 10).
    encoder = json.loads((out_dir / "meta.json").read_text(encoding="utf-8"))["encoder"]
    AutoTokenizer.from_pretrained(encoder).save_pretrained(out_dir)
    return model


@torch.no_grad()
def compare(model, out_dir, texts):
    """Max |logit difference| and argmax agreement of fp32 and INT8 ONNX against PyTorch."""
    report = {}
    for name, quantized in (("fp32", False), ("int8", True)):
        nlu = OnnxNLU(out_dir, quantized=quantized)
        enc = nlu.tokenizer(texts, truncation=True, max_length=nlu.meta["max_length"], padding=True, return_tensors="pt")
        ref = model(enc["input_ids"], enc["attention_mask"])
        intent, slots, _ = nlu.logits(texts)
        mask = enc["attention_mask"].numpy().astype(bool)
        report[name] = {
            "max_abs_intent_diff": float(np.abs(intent - ref["intent_logits"].numpy()).max()),
            "intent_argmax_agreement": float((intent.argmax(-1) == ref["intent_logits"].numpy().argmax(-1)).mean()),
            "slot_argmax_agreement": float((slots.argmax(-1) == ref["slot_logits"].numpy().argmax(-1))[mask].mean()),
        }
    return report


def predict_test(out_dir, cfg, batch_size=64):
    nlu = OnnxNLU(out_dir, quantized=True)
    labels = nlu.meta["labels"]
    examples = [ex for loc in configured_locales(cfg) for ex in load_processed(loc, "test")]
    items = encode(nlu.tokenizer, examples, labels, nlu.meta["max_length"])
    best, tag_ids, offsets = [], [], []
    for i in range(0, len(examples), batch_size):
        intent, slots, off = nlu.logits([ex["utt"] for ex in examples[i:i + batch_size]])
        probs = np.exp(intent - intent.max(-1, keepdims=True))
        probs /= probs.sum(-1, keepdims=True)
        best += list(zip(probs.max(-1).tolist(), probs.argmax(-1).tolist()))
        tag_ids += slots.argmax(-1).tolist()
        offsets += off
    return build_records(examples, items, offsets, best, tag_ids, labels)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluate", action="store_true", help="save INT8 test predictions as run <run>-int8")
    args = parser.parse_args()
    cfg = load_config()
    checkpoint = ROOT / cfg["models"]["deployed_checkpoint"]
    run = checkpoint.parent.name
    out_dir = ROOT / cfg["serving"]["onnx_dir"] / run
    model = export(checkpoint, out_dir)
    for f in ("model.onnx", "model.quant.onnx"):
        print(f"{f}: {(out_dir / f).stat().st_size / 1e6:.0f} MB")
    dev = [ex["utt"] for loc in configured_locales(cfg) for ex in load_processed(loc, "dev")[:20]]
    print(json.dumps(compare(model, out_dir, dev), indent=2))
    if args.evaluate:
        pred_dir = ROOT / cfg["paths"]["artifacts"] / "predictions" / f"{run}-int8"
        pred_dir.mkdir(parents=True, exist_ok=True)
        with open(pred_dir / "test.jsonl", "w", encoding="utf-8") as f:
            for r in predict_test(out_dir, cfg):
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"INT8 test predictions written to {pred_dir}; run `python -m src.models.evaluate --partition test`")


if __name__ == "__main__":
    main()
