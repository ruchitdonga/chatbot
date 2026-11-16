"""Phase 5: train the joint intent + slot model.

Run A trains on the high-resource locales, Run B on all ten; both are validated on the dev split
of all ten locales after every epoch. The best epoch (mean of dev intent accuracy and dev slot F1)
is saved to artifacts/runs/<run_name>/best/; last.pt holds the state for --resume.
Metrics go to MLflow experiment "joint". The test split is never touched here.

Examples, from the repo root:
  python -m src.models.train --model xlm-roberta-base --run A --smoke
  python -m src.models.train --model bert-base-multilingual-cased --run A
  python -m src.models.train --model xlm-roberta-base --run B --resume
"""
import argparse
import contextlib
import json
import random
import time

import mlflow
import numpy as np
import torch
from seqeval.metrics import f1_score as seqeval_f1
from torch.utils.data import DataLoader
from transformers import AutoTokenizer, get_linear_schedule_with_warmup

from src.data.load import ROOT, configured_locales, load_config
from src.data.prepare import SPLITS_DIR, bio_labels, load_processed
from src.models import joint_model
from src.models.tracking import init_mlflow, lineage_params

SMOKE_TRAIN, SMOKE_DEV = 400, 200
OOS_LABEL = "out_of_scope"
OOS_PATHS = [ROOT / "data" / "oos_train" / "oos_train.json", ROOT / "data" / "oos_train" / "food_delivery.json"]
OOS_UPSAMPLE = 5  # shortcut: authored items repeated; replace with more real out-of-scope data when available
# Synthetic English food-delivery tickets (OrSabbach/food-delivery-support-tickets, MIT); see data/oos_train/README.md.
OOS_EXTERNAL = ROOT / "data" / "raw" / "oos_external" / "food_delivery_support_tickets.parquet"
OOS_EXTERNAL_SAMPLE = 1000
OOS_EXTERNAL_EXCLUDE = {"late_delivery"}  # "where is my order?" is answered by takeaway_query, not handed off
CHALLENGE_PATH = ROOT / "data" / "challenge_set" / "challenge_set.jsonl"


def oos_examples(paths, locales, upsample):
    """Authored out-of-scope examples (no slots) for the given locales, each repeated `upsample` times."""
    out = []
    for path in paths:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        out += [{"id": f"oos-{path.stem}-{loc}-{i}", "locale": loc, "partition": "train", "intent": OOS_LABEL,
                 "utt": text, "spans": []}
                for loc in locales for i, text in enumerate(data[loc]) for _ in range(upsample)]
    return out


def first_words(text, n=4):
    return " ".join(text.casefold().split()[:n])


def external_oos_examples(path, n, seed, challenge_texts):
    """English food-delivery support messages, minus excluded categories and any message opening like a
    challenge-set item, so the held-out routing test is never trained on near-copies."""
    import pandas as pd

    df = pd.read_parquet(path)
    blocked = {first_words(t) for t in challenge_texts if t.strip()}
    df = df[~df["category"].isin(OOS_EXTERNAL_EXCLUDE) & ~df["customer_message"].map(first_words).isin(blocked)]
    df = df.sample(n=min(n, len(df)), random_state=seed)
    return [{"id": f"oos-ext-{i}", "locale": "en-US", "partition": "train", "intent": OOS_LABEL, "utt": text,
             "spans": []} for i, text in zip(df["id"], df["customer_message"])]


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def encode(tokenizer, examples, labels, max_length):
    intent2id = {x: i for i, x in enumerate(labels["intents"])}
    tag2id = {t: i for i, t in enumerate(labels["slot_tags"])}
    enc = tokenizer([ex["utt"] for ex in examples], truncation=True, max_length=max_length,
                    return_offsets_mapping=True)
    return [{"input_ids": ids, "slot_labels": bio_labels(off, ex["spans"], tag2id), "intent": intent2id[ex["intent"]]}
            for ex, ids, off in zip(examples, enc["input_ids"], enc["offset_mapping"])]


def collate(pad_id):
    def fn(batch):
        n = max(len(b["input_ids"]) for b in batch)

        def pad(seq, value):
            return seq + [value] * (n - len(seq))

        return {"input_ids": torch.tensor([pad(b["input_ids"], pad_id) for b in batch]),
                "attention_mask": torch.tensor([pad([1] * len(b["input_ids"]), 0) for b in batch]),
                "slot_labels": torch.tensor([pad(b["slot_labels"], -100) for b in batch]),
                "intent_labels": torch.tensor([b["intent"] for b in batch])}
    return fn


def autocast(device):
    return torch.autocast("cuda", dtype=torch.bfloat16) if device == "cuda" else contextlib.nullcontext()


@torch.no_grad()
def evaluate(model, items, examples, labels, batch_size, device, pad_id):
    """Per-locale intent accuracy and seqeval slot F1 on token tags, plus their mean over locales."""
    model.eval()
    intent_pred, tag_pred = [], []
    for batch in DataLoader(items, batch_size=batch_size, collate_fn=collate(pad_id)):
        with autocast(device):
            out = model(batch["input_ids"].to(device), batch["attention_mask"].to(device))
        intent_pred += out["intent_logits"].argmax(-1).tolist()
        tag_pred += out["slot_logits"].argmax(-1).tolist()
    model.train()

    tags = labels["slot_tags"]
    by_loc = {}
    for loc in dict.fromkeys(ex["locale"] for ex in examples):
        idx = [i for i, ex in enumerate(examples) if ex["locale"] == loc]
        gold, pred = [], []
        for i in idx:
            keep = [j for j, g in enumerate(items[i]["slot_labels"]) if g != -100]
            gold.append([tags[items[i]["slot_labels"][j]] for j in keep])
            pred.append([tags[tag_pred[i][j]] for j in keep])
        by_loc[loc] = {"intent_accuracy": float(np.mean([intent_pred[i] == items[i]["intent"] for i in idx])),
                       "slot_f1": float(seqeval_f1(gold, pred))}
    mean = {k: float(np.mean([m[k] for m in by_loc.values()])) for k in ("intent_accuracy", "slot_f1")}
    return by_loc, mean


def train(cfg, model_name, run, smoke=False, resume=False, train_fraction=1.0, overrides=None, run_name=None,
          trial=None, save=True, oos=False):
    """Train one model; returns the best dev score. `trial` enables Optuna pruning; save=False skips checkpoints.
    oos=True adds an out_of_scope intent trained on data/oos_train (never on the challenge set)."""
    hp = {**cfg["training"], **(overrides or {})}
    if smoke:
        hp["epochs"] = 1
    seed = cfg["project"]["seed"]
    set_seed(seed)
    rng = random.Random(seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    langs = cfg["languages"]
    train_locales = langs["high_resource"] if run == "A" else configured_locales(cfg)
    run_name = run_name or (f"{model_name.split('/')[-1]}-run{run}" + ("-oos" if oos else "")
                            + ("-smoke" if smoke else ""))
    out_dir = ROOT / cfg["paths"]["artifacts"] / "runs" / run_name

    labels = json.loads((SPLITS_DIR / "labels.json").read_text(encoding="utf-8"))
    if oos:
        labels = {**labels, "intents": labels["intents"] + [OOS_LABEL]}
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    train_ex = [ex for loc in train_locales for ex in load_processed(loc, "train")]
    if oos:
        train_ex += oos_examples(OOS_PATHS, train_locales, OOS_UPSAMPLE)
        if "en-US" in train_locales:
            challenge = [json.loads(line)["text"] for line in CHALLENGE_PATH.read_text(encoding="utf-8").splitlines()
                         if line]
            train_ex += external_oos_examples(OOS_EXTERNAL, OOS_EXTERNAL_SAMPLE, seed, challenge)
    dev_ex = [ex for loc in configured_locales(cfg) for ex in load_processed(loc, "dev")]
    if smoke:
        train_ex, dev_ex = rng.sample(train_ex, SMOKE_TRAIN), rng.sample(dev_ex, SMOKE_DEV)
    elif train_fraction < 1.0:
        train_ex = rng.sample(train_ex, int(len(train_ex) * train_fraction))
    train_items = encode(tokenizer, train_ex, labels, hp["max_length"])
    dev_items = encode(tokenizer, dev_ex, labels, hp["max_length"])
    pad_id = tokenizer.pad_token_id

    model = joint_model.build(model_name, labels, hp["dropout"], hp["slot_loss_weight"]).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=hp["learning_rate"], weight_decay=hp["weight_decay"])
    steps_per_epoch = -(-len(train_items) // hp["batch_size"])
    total_steps = steps_per_epoch * hp["epochs"]
    scheduler = get_linear_schedule_with_warmup(optimizer, int(hp["warmup_ratio"] * total_steps), total_steps)

    start_epoch, best, stale, mlflow_run_id = 0, -1.0, 0, None
    last_path = out_dir / "last.pt"
    if resume and last_path.exists():
        state = torch.load(last_path, map_location=device, weights_only=False)
        model.load_state_dict(state["model"])
        optimizer.load_state_dict(state["optimizer"])
        scheduler.load_state_dict(state["scheduler"])
        start_epoch, best, stale, mlflow_run_id = state["epoch"] + 1, state["best"], state["stale"], state["mlflow_run_id"]
        print(f"Resuming {run_name} at epoch {start_epoch + 1}")

    init_mlflow(cfg, "joint")
    with mlflow.start_run(run_id=mlflow_run_id, run_name=None if mlflow_run_id else run_name, nested=trial is not None):
        if mlflow_run_id is None:
            mlflow.log_params({**hp, **lineage_params(cfg), "model": model_name, "run": run, "smoke": smoke, "oos": oos,
                               "train_fraction": train_fraction, "train_locales": ",".join(train_locales),
                               "train_examples": len(train_items), "device": device})
        model.train()
        for epoch in range(start_epoch, hp["epochs"]):
            started, losses = time.time(), []
            loader = DataLoader(train_items, batch_size=hp["batch_size"], shuffle=True, collate_fn=collate(pad_id),
                                generator=torch.Generator().manual_seed(seed + epoch))
            for batch in loader:
                with autocast(device):
                    loss = model(**{k: v.to(device) for k, v in batch.items()})["loss"]
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()
                losses.append(loss.item())

            by_loc, mean = evaluate(model, dev_items, dev_ex, labels, hp["batch_size"] * 2, device, pad_id)
            score = (mean["intent_accuracy"] + mean["slot_f1"]) / 2
            mlflow.log_metrics({"train_loss": float(np.mean(losses)), "dev_mean_intent_accuracy": mean["intent_accuracy"],
                                "dev_mean_slot_f1": mean["slot_f1"], "dev_score": score,
                                "epoch_seconds": time.time() - started}, step=epoch)
            print(f"{run_name} epoch {epoch + 1}/{hp['epochs']}: loss {np.mean(losses):.4f}, "
                  f"dev intent acc {mean['intent_accuracy']:.4f}, dev slot F1 {mean['slot_f1']:.4f} "
                  f"({time.time() - started:.0f}s)")

            if score > best:
                best, stale = score, 0
                mlflow.log_metrics({f"best_dev_{loc}_{k}": v for loc, m in by_loc.items() for k, v in m.items()})
                mlflow.log_metric("best_epoch", epoch + 1)
                if save:
                    joint_model.save(model, out_dir / "best", {
                        "encoder": model_name, "labels": labels, "max_length": hp["max_length"], "run": run,
                        "train_locales": train_locales, "hyperparameters": hp, "epoch": epoch + 1,
                        "dev_mean": mean, "dev_by_locale": by_loc, "mlflow_run_id": mlflow.active_run().info.run_id})
            else:
                stale += 1
            if save:
                out_dir.mkdir(parents=True, exist_ok=True)
                torch.save({"model": model.state_dict(), "optimizer": optimizer.state_dict(),
                            "scheduler": scheduler.state_dict(), "epoch": epoch, "best": best, "stale": stale,
                            "mlflow_run_id": mlflow.active_run().info.run_id}, last_path)
            if trial is not None:
                trial.report(score, epoch)
                if trial.should_prune():
                    import optuna
                    raise optuna.TrialPruned()
            if stale >= hp["early_stopping_patience"]:
                print(f"Early stop: no dev improvement for {stale} epochs")
                break
        mlflow.log_metric("best_dev_score", best)
    return best


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="Hugging Face encoder name")
    parser.add_argument("--run", choices=["A", "B"], required=True)
    parser.add_argument("--smoke", action="store_true", help="400 train / 200 dev examples, 1 epoch")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--run-name")
    parser.add_argument("--learning-rate", type=float)
    parser.add_argument("--epochs", type=int)
    parser.add_argument("--slot-loss-weight", type=float)
    parser.add_argument("--oos", action="store_true", help="add an out_of_scope intent trained on data/oos_train")
    args = parser.parse_args()
    overrides = {k: v for k, v in {"learning_rate": args.learning_rate, "epochs": args.epochs,
                                   "slot_loss_weight": args.slot_loss_weight}.items() if v is not None}
    best = train(load_config(), args.model, args.run, smoke=args.smoke, resume=args.resume, overrides=overrides,
                 run_name=args.run_name, oos=args.oos)
    print(f"Best dev score: {best:.4f}")


if __name__ == "__main__":
    main()
