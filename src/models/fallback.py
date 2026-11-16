"""Phase 7: calibrate intent confidence and recommend the fallback rule.

1. Fit a temperature T on dev intent logits (minimising NLL); report ECE before and after, with a
   reliability diagram.
2. Three in-scope scores are compared: max_prob (calibrated top probability), margin (top-1 minus
   top-2 probability) and energy (logsumexp of the scaled logits). An input goes to human handoff when
   its score is below a threshold. For each score the threshold is chosen on dev (in-scope) plus the
   challenge set's tune half: among thresholds routing at least targets.safe_fallback_routing of tune
   items, the one answering the most dev inputs; if none reaches the target, the one routing the most.
   The method is chosen by the same rule. Held-out results are reported for every method, but only
   tune and dev data drive any choice.
3. For the chosen method: held-out routing per category and the dev fallback rate per locale.

The rule is a recommendation: a person reviews it and copies it into configs/project.yaml
(fallback.threshold). Test data is not used.
Run from the repo root: python -m src.models.fallback --checkpoint artifacts/runs/<run>/best
"""
import argparse
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402
from scipy.optimize import minimize_scalar  # noqa: E402
from transformers import AutoTokenizer  # noqa: E402

from src.data.load import ROOT, configured_locales, load_config  # noqa: E402
from src.data.prepare import load_processed  # noqa: E402
from src.models import joint_model  # noqa: E402
from src.models.train import OOS_LABEL, autocast  # noqa: E402

THRESHOLDS = np.round(np.arange(0.05, 1.0, 0.01), 2)


@torch.no_grad()
def intent_logits(model, tokenizer, texts, max_length, device, batch_size=64):
    out = []
    for i in range(0, len(texts), batch_size):
        enc = tokenizer(texts[i:i + batch_size], truncation=True, max_length=max_length, padding=True,
                        return_tensors="pt")
        with autocast(device):
            logits = model(enc["input_ids"].to(device), enc["attention_mask"].to(device))["intent_logits"]
        out.append(logits.float().cpu().numpy())
    return np.concatenate(out)


def softmax(z):
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def fit_temperature(logits, gold):
    def nll(t):
        return -np.log(softmax(logits / t)[np.arange(len(gold)), gold] + 1e-12).mean()
    return float(minimize_scalar(nll, bounds=(0.05, 10.0), method="bounded").x)


def score_methods(logits, temperature):
    """In-scope scores per input; higher means more likely in scope."""
    z = logits / temperature
    probs = softmax(z)
    top2 = np.sort(probs, axis=1)[:, -2:]
    zmax = z.max(axis=1)
    energy = zmax + np.log(np.exp(z - zmax[:, None]).sum(axis=1))  # logsumexp, i.e. negative energy
    return {"max_prob": probs.max(axis=1), "margin": top2[:, 1] - top2[:, 0], "energy": energy}


def ece(probs, gold, bins=15):
    """Expected calibration error with equal-width confidence bins; also returns the bins for plotting."""
    conf, correct = probs.max(axis=1), probs.argmax(axis=1) == gold
    total, rows = 0.0, []
    edges = np.linspace(0, 1, bins + 1)
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (conf > lo) & (conf <= hi)
        if mask.any():
            total += mask.mean() * abs(correct[mask].mean() - conf[mask].mean())
            rows.append((float(conf[mask].mean()), float(correct[mask].mean()), int(mask.sum())))
    return float(total), rows


def choose_threshold(dev_score, oos_score, target, thresholds=THRESHOLDS):
    """Rows are (threshold, share of out-of-scope routed to handoff, share of dev answered)."""
    rows = [(float(t), float((oos_score < t).mean()), float((dev_score >= t).mean())) for t in thresholds]
    meeting = [r for r in rows if r[1] >= target]
    best = max(meeting, key=lambda r: (r[2], -r[0])) if meeting else max(rows, key=lambda r: (r[1], r[2]))
    return best, rows


def plot_reliability(before, after, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot([0, 1], [0, 1], linestyle="--", color="grey", label="perfect calibration")
    for rows, label in ((before, "before"), (after, "after temperature scaling")):
        ax.plot([r[0] for r in rows], [r[1] for r in rows], marker="o", label=label)
    ax.set_xlabel("Mean confidence in bin")
    ax.set_ylabel("Accuracy in bin")
    ax.set_title("Intent confidence reliability (dev)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()
    cfg = load_config()
    model, meta = joint_model.load(args.checkpoint, args.device)
    tokenizer = AutoTokenizer.from_pretrained(meta["encoder"])
    intent2id = {x: i for i, x in enumerate(meta["labels"]["intents"])}

    dev = [ex for loc in configured_locales(cfg) for ex in load_processed(loc, "dev")]
    gold = np.array([intent2id[ex["intent"]] for ex in dev])
    dev_logits = intent_logits(model, tokenizer, [ex["utt"] for ex in dev], meta["max_length"], args.device)
    items = [json.loads(line) for line in (ROOT / "data" / "challenge_set" / "challenge_set.jsonl")
             .read_text(encoding="utf-8").splitlines() if line]
    oos_logits = intent_logits(model, tokenizer, [i["text"] for i in items], meta["max_length"], args.device)

    temperature = fit_temperature(dev_logits, gold)
    ece_before, bins_before = ece(softmax(dev_logits), gold)
    dev_probs = softmax(dev_logits / temperature)
    ece_after, bins_after = ece(dev_probs, gold)
    dev_scores, oos_scores = score_methods(dev_logits, temperature), score_methods(oos_logits, temperature)
    has_oos_class = OOS_LABEL in meta["labels"]["intents"]
    if has_oos_class:
        # A predicted out_of_scope intent always goes to handoff, whatever the threshold.
        k = meta["labels"]["intents"].index(OOS_LABEL)
        for scores, logits in ((dev_scores, dev_logits), (oos_scores, oos_logits)):
            for s in scores.values():
                s[logits.argmax(axis=1) == k] = -np.inf

    tune = np.array([i["split"] == "tune" for i in items])
    target = cfg["targets"]["safe_fallback_routing"]
    methods, curves = {}, {}
    for name in dev_scores:
        # Energy is unbounded, so its grid follows the dev score distribution.
        finite = dev_scores[name][np.isfinite(dev_scores[name])]
        grid = THRESHOLDS if name != "energy" else np.quantile(finite, np.linspace(0, 0.99, 100))
        (t, tune_routing, coverage), curves[name] = choose_threshold(dev_scores[name], oos_scores[name][tune],
                                                                     target, grid)
        methods[name] = {"threshold": t, "tune_routing": tune_routing, "dev_coverage": coverage,
                         "heldout_routing": float((oos_scores[name][~tune] < t).mean())}
    meeting = [m for m in methods if methods[m]["tune_routing"] >= target]
    chosen = (max(meeting, key=lambda m: methods[m]["dev_coverage"]) if meeting
              else max(methods, key=lambda m: (methods[m]["tune_routing"], methods[m]["dev_coverage"])))
    threshold = methods[chosen]["threshold"]

    routed = oos_scores[chosen] < threshold
    heldout_by_category = {}
    for cat in dict.fromkeys(i["category"] for i in items):
        idx = [k for k, i in enumerate(items) if i["category"] == cat and i["split"] == "heldout"]
        heldout_by_category[cat] = {"n": len(idx), "routed": float(routed[idx].mean())}
    heldout_by_language = {}
    for lang in dict.fromkeys(i["language"] for i in items):
        idx = [k for k, i in enumerate(items) if i["language"] == lang and i["split"] == "heldout"]
        if idx:
            heldout_by_language[lang] = {"n": len(idx), "routed": float(routed[idx].mean())}
    answered = dev_scores[chosen] >= threshold
    correct = dev_probs.argmax(axis=1) == gold
    by_locale = {loc: float(1 - answered[[k for k, ex in enumerate(dev) if ex["locale"] == loc]].mean())
                 for loc in configured_locales(cfg)}
    result = {
        "checkpoint": args.checkpoint, "temperature": temperature, "ece_before": ece_before, "ece_after": ece_after,
        "target_routing": target, "oos_class": has_oos_class,
        "heldout_routed_by_oos_class": float(np.isneginf(oos_scores[chosen][~tune]).mean()),
        "method": chosen, "recommended_threshold": threshold,
        "tune_routing": methods[chosen]["tune_routing"], "heldout_routing": methods[chosen]["heldout_routing"],
        "methods": methods, "heldout_by_category": heldout_by_category, "heldout_by_language": heldout_by_language,
        "dev_coverage": methods[chosen]["dev_coverage"], "dev_fallback_rate": 1 - methods[chosen]["dev_coverage"],
        "dev_accuracy_when_answered": float(correct[answered].mean()) if answered.any() else 0.0,
        "dev_wrong_answers_share": float((answered & ~correct).mean()),
        "dev_fallback_rate_by_locale": by_locale,
    }
    reports = ROOT / cfg["paths"]["reports"]
    (reports / "fallback.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    plot_reliability(bins_before, bins_after, reports / "figures" / "reliability.png")

    lines = [
        "# Calibration and Fallback", "",
        f"Generated by `python -m src.models.fallback` for `{args.checkpoint}`. Dev data and the challenge set only; "
        "test data not used.", "",
        f"- Temperature fitted on dev: **{temperature:.3f}**. ECE before {ece_before:.4f}, after {ece_after:.4f} "
        "(15 equal-width bins). ![Reliability](figures/reliability.png)",
        f"- Chosen rule: **{chosen} < {threshold:.4g} → handoff**, chosen on tune + dev only. "
        "A person must review it and copy it into `fallback.threshold` in `configs/project.yaml`.",
        f"- **Held-out routing: {result['heldout_routing']:.1%}** (NFR-3 target {target:.0%})"
        + (f"; {result['heldout_routed_by_oos_class']:.1%} of held-out items were routed by the predicted "
           "`out_of_scope` intent alone." if has_oos_class else "."),
        f"- Dev (in-scope): {result['dev_coverage']:.1%} answered, {result['dev_fallback_rate']:.1%} handed off; "
        f"accuracy when answered {result['dev_accuracy_when_answered']:.1%}; wrong answers given on "
        f"{result['dev_wrong_answers_share']:.1%} of inputs.",
        "", "## Methods compared", "",
        "| Method | Threshold | Tune routed | Dev answered | Held-out routed |", "|---|---|---|---|---|",
    ]
    lines += [f"| {name}{' (chosen)' if name == chosen else ''} | {m['threshold']:.4g} | {m['tune_routing']:.1%} "
              f"| {m['dev_coverage']:.1%} | {m['heldout_routing']:.1%} |" for name, m in methods.items()]
    lines += ["", "## Held-out routing by category (chosen method)", "",
              "| Category | Items | Routed to handoff |", "|---|---|---|"]
    lines += [f"| {c} | {v['n']} | {v['routed']:.0%} |" for c, v in heldout_by_category.items()]
    lines += ["", "## Held-out routing by language (chosen method)", "",
              "English items share topics with the external out-of-scope training data, so English may be optimistic.",
              "", "| Language | Items | Routed to handoff |", "|---|---|---|"]
    lines += [f"| {lang} | {v['n']} | {v['routed']:.0%} |" for lang, v in heldout_by_language.items()]
    lines += ["", "## Dev fallback rate by locale (chosen method)", "",
              "A locale handed off far more often than others is a fairness problem as well as a coverage one.", "",
              "| Locale | Handed off |", "|---|---|"]
    lines += [f"| {loc} | {rate:.1%} |" for loc, rate in by_locale.items()]
    lines += ["", "## Trade-off for the chosen method (every 5th threshold)", "",
              "| Threshold | Tune out-of-scope routed | Dev answered |", "|---|---|---|"]
    lines += [f"| {t:.4g} | {r:.1%} | {c:.1%} |" for t, r, c in curves[chosen][::5]]
    (reports / "fallback_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ("heldout_by_category", "heldout_by_language", "dev_fallback_rate_by_locale")},
                     indent=2))


if __name__ == "__main__":
    main()
