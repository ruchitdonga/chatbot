"""Joint intent classification and slot tagging on one shared multilingual encoder."""
import json
from pathlib import Path

from safetensors.torch import load_file, save_file
from torch import nn
from transformers import AutoConfig, AutoModel


class JointModel(nn.Module):
    def __init__(self, encoder, n_intents, n_slot_tags, dropout=0.1, slot_loss_weight=1.0):
        super().__init__()
        self.encoder = encoder
        hidden = encoder.config.hidden_size
        self.dropout = nn.Dropout(dropout)
        self.intent_head = nn.Linear(hidden, n_intents)
        self.slot_head = nn.Linear(hidden, n_slot_tags)
        self.slot_loss_weight = slot_loss_weight

    def forward(self, input_ids, attention_mask, intent_labels=None, slot_labels=None):
        hidden = self.dropout(self.encoder(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state)
        # First-token state rather than the pooler: XLM-R's pooler was never trained.
        out = {"intent_logits": self.intent_head(hidden[:, 0]), "slot_logits": self.slot_head(hidden)}
        if intent_labels is not None:
            slot_logits = out["slot_logits"]
            out["loss"] = nn.functional.cross_entropy(out["intent_logits"], intent_labels) + (
                self.slot_loss_weight * nn.functional.cross_entropy(
                    slot_logits.reshape(-1, slot_logits.size(-1)), slot_labels.reshape(-1), ignore_index=-100))
        return out


def build(encoder_name, labels, dropout, slot_loss_weight):
    encoder = AutoModel.from_pretrained(encoder_name, add_pooling_layer=False)
    return JointModel(encoder, len(labels["intents"]), len(labels["slot_tags"]), dropout, slot_loss_weight)


def save(model, path, meta):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    save_file({k: v.contiguous() for k, v in model.state_dict().items()}, path / "model.safetensors")
    (path / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def load(path, device="cpu"):
    """Load a checkpoint written by save(); returns (model in eval mode, meta)."""
    path = Path(path)
    meta = json.loads((path / "meta.json").read_text(encoding="utf-8"))
    encoder = AutoModel.from_config(AutoConfig.from_pretrained(meta["encoder"]), add_pooling_layer=False)
    model = JointModel(encoder, len(meta["labels"]["intents"]), len(meta["labels"]["slot_tags"]))
    model.load_state_dict(load_file(path / "model.safetensors", device=str(device)))
    return model.to(device).eval(), meta
