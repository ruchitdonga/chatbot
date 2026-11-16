import torch
from transformers import BertConfig, BertModel

from src.models.inference import decode_spans
from src.models.joint_model import JointModel
from src.models.train import collate


def test_forward_shapes_and_loss():
    torch.manual_seed(0)
    encoder = BertModel(BertConfig(vocab_size=50, hidden_size=16, num_hidden_layers=1, num_attention_heads=2,
                                   intermediate_size=32), add_pooling_layer=False)
    model = JointModel(encoder, n_intents=3, n_slot_tags=5)
    ids = torch.randint(1, 50, (2, 6))
    mask = torch.ones_like(ids)
    slot_labels = torch.tensor([[-100, 0, 1, 2, 0, -100], [-100, 3, 4, 0, -100, -100]])
    out = model(ids, mask, intent_labels=torch.tensor([0, 2]), slot_labels=slot_labels)
    assert out["intent_logits"].shape == (2, 3)
    assert out["slot_logits"].shape == (2, 6, 5)
    assert torch.isfinite(out["loss"])


def test_collate_pads_labels_with_ignore_index():
    batch = collate(pad_id=0)([
        {"input_ids": [5, 6, 7], "slot_labels": [-100, 1, -100], "intent": 2},
        {"input_ids": [5, 7], "slot_labels": [-100, -100], "intent": 0},
    ])
    assert batch["input_ids"].tolist() == [[5, 6, 7], [5, 7, 0]]
    assert batch["attention_mask"].tolist() == [[1, 1, 1], [1, 1, 0]]
    assert batch["slot_labels"].tolist() == [[-100, 1, -100], [-100, -100, -100]]


def test_decode_spans():
    offsets = [(0, 0), (0, 4), (5, 7), (8, 12), (13, 16), (16, 19), (0, 0)]
    tags = ["O", "O", "B-time", "I-time", "I-date", "I-date", "O"]
    # I-date after a time span starts a new span (lenient), then continues.
    assert decode_spans(tags, offsets) == [[5, 12, "time"], [13, 19, "date"]]
