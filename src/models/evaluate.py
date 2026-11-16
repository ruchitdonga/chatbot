"""Phase 6: evaluate saved joint-model checkpoints per locale.

Predictions are saved to artifacts/predictions/<run>/<partition>.jsonl and every metric is computed
from those files; run without --checkpoint to regenerate the reports without loading any model.
Headline slot F1 is seqeval entity F1 on token tags; character-exact span F1 is secondary (XLM-R
splits 14% of ja-JP slots mid-token, reports/alignment_report.md). Means are unweighted over locales.
Use --partition dev while developing; test is for final reporting only.

Run from the repo root:
  python -m src.models.evaluate --checkpoint artifacts/runs/xlm-roberta-base-runA/best --partition test
  python -m src.models.evaluate --partition test   # reports from saved predictions only
  python -m src.models.evaluate --checkpoint <dir> --limit 50 --device cpu   # quick check, writes nothing
"""
import argparse
import json
import random
from collections import Counter
from pathlib import Path

import numpy as np
import torch
from scipy.stats import binomtest
from seqeval.metrics import f1_score as seqeval_f1
from sklearn.metrics import f1_score
from torch.utils.data import DataLoader
from transformers import AutoTokenizer

from src.data.load import ROOT, configured_locales, load_config
from src.data.prepare import SPLITS_DIR, load_processed
from src.models import joint_model
from src.models.inference import decode_spans
from src.models.train import autocast, collate, encode

BASELINES = ["majority", "bag_of_embeddings"]
METRICS = ["intent_accuracy", "intent_macro_f1", "slot_f1", "slot_f1_char_exact"]


@torch.no_grad()
def predict(checkpoint, examples, device, batch_size=64):
    model, meta = joint_model.load(checkpoint, device)
    labels = meta["labels"]
    tags = labels["slot_tags"]
    tokenizer = AutoTokenizer.from_pretrained(meta["encoder"])
    items = encode(tokenizer, examples, labels, meta["max_length"])
    offsets = tokenizer([ex["utt"] for ex in examples], truncation=True, max_length=meta["max_length"],
                        return_offsets_mapping=True)["offset_mapping"]
    best, tag_ids = [], []
    for batch in DataLoader(items, batch_size=batch_size, collate_fn=collate(tokenizer.pad_token_id)):
        with autocast(device):
            out = model(batch["input_ids"].to(device), batch["attention_mask"].to(device))
        conf, idx = out["intent_logits"].float().softmax(-1).max(-1)
        best += list(zip(conf.tolist(), idx.tolist()))
        tag_ids += out["slot_logits"].argmax(-1).tolist()
    return build_records(examples, items, offsets, best, tag_ids, labels)


def build_records(examples, items, offsets, best, tag_ids, labels):
    """Prediction records from per-example (confidence, intent index) and token tag ids."""
    tags = labels["slot_tags"]
    records = []
    for ex, item, off, (conf, intent), pred in zip(examples, items, offsets, best, tag_ids):
        keep = [j for j, g in enumerate(item["slot_labels"]) if g != -100]
        records.append({
            "id": ex["id"], "locale": ex["locale"], "utt": ex["utt"],
            "gold_intent": ex["intent"], "pred_intent": labels["intents"][intent], "confidence": round(conf, 4),
            "gold_tags": [tags[item["slot_labels"][j]] for j in keep], "pred_tags": [tags[pred[j]] for j in keep],
            "gold_spans": ex["spans"], "pred_spans": decode_spans([tags[t] for t in pred[:len(off)]], off),
        })
    return records


def span_f1(records):
    """Micro F1 over exact (start, end, label) character spans."""
    tp = fp = fn = 0
    for r in records:
        gold, pred = {tuple(s) for s in r["gold_spans"]}, {tuple(s) for s in r["pred_spans"]}
        tp, fp, fn = tp + len(gold & pred), fp + len(pred - gold), fn + len(gold - pred)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def metrics(records):
    by_loc = {}
    for loc in dict.fromkeys(r["locale"] for r in records):
        rs = [r for r in records if r["locale"] == loc]
        gold, pred = [r["gold_intent"] for r in rs], [r["pred_intent"] for r in rs]
        by_loc[loc] = {
            "n": len(rs),
            "intent_accuracy": float(np.mean([g == p for g, p in zip(gold, pred)])),
            "intent_macro_f1": float(f1_score(gold, pred, average="macro", zero_division=0)),
            "slot_f1": float(seqeval_f1([r["gold_tags"] for r in rs], [r["pred_tags"] for r in rs])),
            "slot_f1_char_exact": span_f1(rs),
        }
    return {"by_locale": by_loc, "mean": {k: float(np.mean([m[k] for m in by_loc.values()])) for k in METRICS}}


def transfer_gap(by_loc, cfg):
    """Mean of high-resource locales minus mean of low-resource locales."""
    langs = cfg["languages"]
    return {k: float(np.mean([by_loc[l][k] for l in langs["high_resource"]])
                     - np.mean([by_loc[l][k] for l in langs["low_resource"]])) for k in ("intent_accuracy", "slot_f1")}


def fairness(by_loc, max_gap_pp):
    """Locales more than max_gap_pp percentage points below the ten-locale mean (NFR-2 uses intent accuracy)."""
    out = {}
    for k in ("intent_accuracy", "slot_f1"):
        mean = float(np.mean([m[k] for m in by_loc.values()]))
        gaps = {loc: round((mean - m[k]) * 100, 1) for loc, m in by_loc.items()}
        out[k] = {"mean": mean, "flagged": {loc: g for loc, g in gaps.items() if g > max_gap_pp}}
    return out


def mcnemar(model_correct, baseline_correct):
    """Exact McNemar test on paired correctness (two-sided binomial test on the discordant pairs)."""
    b = sum(m and not x for m, x in zip(model_correct, baseline_correct))
    c = sum(x and not m for m, x in zip(model_correct, baseline_correct))
    return {"model_only_correct": b, "baseline_only_correct": c,
            "p_value": binomtest(b, b + c, 0.5).pvalue if b + c else 1.0}


def significance(records, pred_dir, partition):
    out = {}
    for name in BASELINES:
        path = pred_dir / name / f"{partition}.jsonl"
        if not path.exists():
            continue
        base = {(r["locale"], r["id"]): r["pred"] == r["gold"] for r in read_jsonl(path)}
        model = {(r["locale"], r["id"]): r["pred_intent"] == r["gold_intent"] for r in records}
        keys = [k for k in model if k in base]
        out[name] = mcnemar([model[k] for k in keys], [base[k] for k in keys])
    return out


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def analyse(records, cfg, partition):
    """All metrics for one run's saved predictions."""
    result = {"full": metrics(records)}
    if partition == "test":
        subsets = json.loads((SPLITS_DIR / "test_subsets.json").read_text(encoding="utf-8"))
        for name, ids_by_loc in (("unseen_in_train", subsets["seen_in_train"]), ("judge_clean", subsets["judge_flagged"])):
            excluded = {(loc, i) for loc, ids in ids_by_loc.items() for i in ids}
            result[name] = metrics([r for r in records if (r["locale"], r["id"]) not in excluded])
    by_loc = result["full"]["by_locale"]
    result["transfer_gap"] = transfer_gap(by_loc, cfg)
    result["fairness"] = fairness(by_loc, cfg["targets"]["max_gap_below_mean_pp"])
    result["significance_vs_baselines"] = significance(records, ROOT / cfg["paths"]["artifacts"] / "predictions",
                                                       partition)
    errors = Counter((r["gold_intent"], r["pred_intent"]) for r in records if r["gold_intent"] != r["pred_intent"])
    result["top_confusions"] = [{"gold": g, "pred": p, "count": n} for (g, p), n in errors.most_common(10)]
    return result


def fmt(x):
    return f"{x:.3f}"


def fmt_p(p):
    return "p < 1e-300" if p == 0 else f"p = {p:.2e}"  # 0 means the value underflowed float64


def write_reports(cfg, partition, results, error_records):
    reports = ROOT / cfg["paths"]["reports"]
    metrics_path = reports / "metrics.json"
    all_metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.exists() else {}
    all_metrics[partition] = results
    metrics_path.write_text(json.dumps(all_metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    t = cfg["targets"]
    lines = [f"# Evaluation Report ({partition} split)", "",
             "Generated by `python -m src.models.evaluate` from saved predictions in `artifacts/predictions/`. "
             "Slot F1 is seqeval entity-level F1 on token BIO tags (headline); char-exact is micro F1 over exact "
             "character spans (secondary). Means are unweighted over the ten locales.", "",
             f"Targets: mean intent accuracy ≥ {t['mean_intent_accuracy']}, mean slot F1 ≥ {t['mean_slot_micro_f1']}, "
             f"no locale more than {t['max_gap_below_mean_pp']} pp below the mean intent accuracy.", "",
             "## Summary", "",
             "| Run | Intent acc | Intent macro-F1 | Slot F1 | Slot F1 char-exact | Transfer gap (intent) | Locales >10 pp below |",
             "|---|---|---|---|---|---|---|"]
    for run, r in results.items():
        m = r["full"]["mean"]
        flagged = r["fairness"]["intent_accuracy"]["flagged"]
        lines.append(f"| {run} | {fmt(m['intent_accuracy'])} | {fmt(m['intent_macro_f1'])} | {fmt(m['slot_f1'])} "
                     f"| {fmt(m['slot_f1_char_exact'])} | {r['transfer_gap']['intent_accuracy'] * 100:.1f} pp "
                     f"| {', '.join(f'{k} ({v} pp)' for k, v in flagged.items()) or 'none'} |")
    for run, r in results.items():
        lines += ["", f"## {run}", "", "| Locale | Intent acc | Intent macro-F1 | Slot F1 | Slot F1 char-exact"
                  + (" | Intent acc unseen | Intent acc judge-clean |" if "unseen_in_train" in r else " |"),
                  "|---|---|---|---|---|" + ("---|---|" if "unseen_in_train" in r else "")]
        for loc in configured_locales(cfg):
            m = r["full"]["by_locale"][loc]
            row = f"| {loc} | {fmt(m['intent_accuracy'])} | {fmt(m['intent_macro_f1'])} | {fmt(m['slot_f1'])} | {fmt(m['slot_f1_char_exact'])} |"
            if "unseen_in_train" in r:
                row += (f" {fmt(r['unseen_in_train']['by_locale'][loc]['intent_accuracy'])} "
                        f"| {fmt(r['judge_clean']['by_locale'][loc]['intent_accuracy'])} |")
            lines.append(row)
        sig = r["significance_vs_baselines"]
        if sig:
            lines += ["", "McNemar test on intent correctness vs baselines: " + "; ".join(
                f"{name}: model-only correct {s['model_only_correct']}, baseline-only correct "
                f"{s['baseline_only_correct']}, {fmt_p(s['p_value'])}" for name, s in sig.items()) + "."]
        lines += ["", "Most frequent intent confusions: " + ", ".join(
            f"`{c['gold']}` → `{c['pred']}` ({c['count']})" for c in r["top_confusions"]) + "."]
    (reports / "evaluation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    sample = ["# Error Samples", "", f"Random intent or slot errors ({partition} split), up to 3 per locale and run, "
              "seed from the config. For the manual error analysis (at least 20 cases).", ""]
    for run, recs in error_records.items():
        sample += [f"## {run}", "", "| Locale | Utterance | Gold intent | Predicted | Confidence | Gold slots | Predicted slots |",
                   "|---|---|---|---|---|---|---|"]
        for r in recs:
            show = lambda spans: ", ".join(f"{lab}: {r['utt'][s:e]}" for s, e, lab in spans) or "-"  # noqa: E731
            sample.append(f"| {r['locale']} | {r['utt'].replace('|', '¦')} | {r['gold_intent']} | {r['pred_intent']} | {r['confidence']} "
                          f"| {show(r['gold_spans'])} | {show(r['pred_spans'])} |")
        sample.append("")
    (reports / "error_samples.md").write_text("\n".join(sample), encoding="utf-8")


def error_sample(records, seed, per_locale=3):
    rng = random.Random(seed)
    out = []
    for loc in dict.fromkeys(r["locale"] for r in records):
        wrong = [r for r in records if r["locale"] == loc and (
            r["gold_intent"] != r["pred_intent"] or r["gold_tags"] != r["pred_tags"])]
        out += rng.sample(wrong, min(per_locale, len(wrong)))
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", nargs="*", default=[], help="artifacts/runs/<run>/best directories")
    parser.add_argument("--partition", choices=["dev", "test"], default="dev")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--limit", type=int, help="examples per locale; prints means and writes nothing")
    args = parser.parse_args()
    cfg = load_config()
    pred_dir = ROOT / cfg["paths"]["artifacts"] / "predictions"

    for ckpt in args.checkpoint:
        run = Path(ckpt).parent.name
        examples = [ex for loc in configured_locales(cfg) for ex in load_processed(loc, args.partition)[:args.limit]]
        records = predict(ckpt, examples, args.device)
        if args.limit:
            print(run, {k: round(v, 4) for k, v in metrics(records)["mean"].items()}, "(limited; nothing written)")
            continue
        (pred_dir / run).mkdir(parents=True, exist_ok=True)
        with open(pred_dir / run / f"{args.partition}.jsonl", "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    if args.limit:
        return

    # Reports cover every joint-model run with saved predictions (baselines lack token tags).
    results, errors = {}, {}
    for path in sorted(pred_dir.glob(f"*/{args.partition}.jsonl")):
        records = read_jsonl(path)
        if records and "gold_tags" in records[0]:
            results[path.parent.name] = analyse(records, cfg, args.partition)
            errors[path.parent.name] = error_sample(records, cfg["project"]["seed"])
    if not results:
        raise SystemExit(f"No joint-model predictions for '{args.partition}' in {pred_dir}")
    write_reports(cfg, args.partition, results, errors)
    for run, r in results.items():
        print(run, {k: round(v, 4) for k, v in r["full"]["mean"].items()})


if __name__ == "__main__":
    main()
