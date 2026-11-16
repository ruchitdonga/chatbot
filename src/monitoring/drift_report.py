"""Phase 11: drift monitoring for the FeastFleet NLU (fictional demo). OBJ-6, EO-4, FR-6.

Reference (guide): the TRAIN split with the deployed model's predictions -> locale, predicted intent, predicted slot
labels, utterance length. Model-behaviour baseline: the handoff (fallback) rate on the held-out DEV split, because the
model is over-confident on data it was trained on and a train baseline would make "fallback rate doubled" fire on
normal traffic.

Batches (from the TEST split, 5,000 utterances each):
  normal - a random sample.
  drift  - SYNTHETIC: a Swahili surge (50% sw-KE, the rest spread over the other nine locales). Not real traffic.
Per batch: PSI on locale, intent and slot-label distributions, the fallback rate, the retraining triggers from
configs/project.yaml `retraining`, and an Evidently DataDriftPreset report (HTML).
`--log logs/nlu_events.jsonl` runs the same checks on the live service's event log (allow-listed fields only).

Run: python -m src.monitoring.drift_report [--log logs/nlu_events.jsonl]
"""
import argparse
import json
import math
import os
import random
from collections import Counter

from src.data.load import ROOT, configured_locales, load_config
from src.data.prepare import load_processed

CACHE = ROOT / "artifacts" / "monitoring"
OUT = ROOT / "reports" / "monitoring"
BATCH_SIZE, SEED = 5000, 0


def psi(ref, cur, eps=1e-4):
    """Population stability index between two Counters of category -> count (eps for empty bins)."""
    cats, nr, nc = set(ref) | set(cur), sum(ref.values()), sum(cur.values())
    total = 0.0
    for c in cats:
        p, q = max(ref.get(c, 0) / nr, eps), max(cur.get(c, 0) / nc, eps)
        total += (q - p) * math.log(q / p)
    return total


def profile(rows):
    """Distributions the triggers look at, from rows with locale, intent, slot_labels, handoff."""
    return {"n": len(rows),
            "locale": Counter(r["locale"] for r in rows),
            "intent": Counter(r["intent"] or "none" for r in rows),
            "slot_labels": Counter(s for r in rows for s in r["slot_labels"]),
            "fallback_rate": sum(r["handoff"] for r in rows) / max(len(rows), 1)}


def triggers(ref, cur, baseline_fallback, cfg):
    """Retraining triggers (configs/project.yaml `retraining`) for one batch -> dict of measures and fired flags."""
    thr, min_n, mult = cfg["psi_threshold"], cfg["min_utterances"], cfg["fallback_rate_multiplier"]
    out = {f"psi_{k}": round(psi(ref[k], cur[k]), 4) for k in ("locale", "intent", "slot_labels")}
    out["fallback_rate"] = round(cur["fallback_rate"], 4)
    out["enough_data"] = cur["n"] >= min_n
    fired = []
    if out["enough_data"]:
        fired += [f"PSI {k} > {thr}" for k in ("locale", "intent") if out[f"psi_{k}"] > thr]
        if cur["fallback_rate"] >= mult * baseline_fallback:
            fired.append(f"fallback rate >= {mult}x baseline")
    out["fired"] = fired
    return out


def predict_split(nlu, cfg, partition):
    """Deployed-model predictions for every utterance of one split, cached in artifacts/monitoring/."""
    path = CACHE / f"{partition}.jsonl"
    if path.exists():
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    records = [r for loc in configured_locales(cfg) for r in load_processed(loc, partition)]
    order = sorted(range(len(records)), key=lambda i: len(records[i]["utt"]))  # similar lengths -> less padding
    fb, rows = cfg["fallback"], [None] * len(records)
    for start in range(0, len(order), 64):
        idx = order[start:start + 64]
        preds = nlu.predict_batch([records[i]["utt"] for i in idx], fb["temperature"], fb["threshold"])
        for i, p in zip(idx, preds):
            rows[i] = {"locale": records[i]["locale"], "intent": p["intent"], "n_chars": len(records[i]["utt"]),
                       "slot_labels": [s["label"] for s in p["slots"]], "confidence": p["confidence"],
                       "handoff": p["handoff"]}
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    return rows


def make_batches(test):
    rng = random.Random(SEED)
    normal = rng.sample(test, BATCH_SIZE)
    sw = [r for r in test if r["locale"] == "sw-KE"]
    rest = [r for r in test if r["locale"] != "sw-KE"]
    drift = rng.sample(sw, BATCH_SIZE // 2) + rng.sample(rest, BATCH_SIZE // 2)
    return {"normal (test sample)": normal, "drift (SYNTHETIC Swahili surge)": drift}


def evidently_html(reference, current, path):
    """Evidently DataDriftPreset on the per-utterance columns -> HTML file; returns (drifted, total) columns."""
    import pandas as pd
    from evidently import DataDefinition, Dataset, Report
    from evidently.presets import DataDriftPreset

    def frame(rows):
        return pd.DataFrame({"locale": [r["locale"] for r in rows], "intent": [r["intent"] or "none" for r in rows],
                             "n_chars": [r["n_chars"] for r in rows], "n_slots": [len(r["slot_labels"]) for r in rows]})

    definition = DataDefinition(numerical_columns=["n_chars", "n_slots"], categorical_columns=["locale", "intent"])
    snapshot = Report([DataDriftPreset()]).run(Dataset.from_pandas(frame(current), data_definition=definition),
                                               Dataset.from_pandas(frame(reference), data_definition=definition))
    snapshot.save_html(str(path))
    for m in snapshot.dict()["metrics"]:
        if str(m.get("metric_name", "")).startswith("DriftedColumnsCount"):
            return int(m["value"]["count"]), 4
    return None, 4


def write_report(ref_profile, dev_fallback, results, evid, cfg, log_result):
    r = cfg["retraining"]
    lines = ["# Drift report (Phase 11)", "",
             "FeastFleet is a FICTIONAL demo. Reference: TRAIN split with the deployed model's predictions "
             f"({ref_profile['n']:,} utterances). Fallback-rate baseline: DEV split ({dev_fallback:.1%}), because the "
             "model is over-confident on its own training data. The drift batch is **SYNTHETIC**.", "",
             f"Triggers (`configs/project.yaml` → `retraining`): PSI > {r['psi_threshold']} on locale or intent over at "
             f"least {r['min_utterances']:,} utterances, or a fallback rate ≥ {r['fallback_rate_multiplier']}× the "
             "baseline. Slot-label PSI is reported but is not a trigger.", "",
             "| Batch | n | PSI locale | PSI intent | PSI slot labels | Fallback rate | Evidently drifted columns | Triggers fired |",
             "|---|---|---|---|---|---|---|---|"]
    for name, t in results.items():
        drifted, total = evid.get(name, (None, None))
        lines.append(f"| {name} | {t['n']:,} | {t['psi_locale']} | {t['psi_intent']} | {t['psi_slot_labels']} | "
                     f"{t['fallback_rate']:.1%} | {drifted if drifted is not None else '–'}/{total or '–'} | "
                     f"{', '.join(t['fired']) or 'none'} |")
    if log_result:
        t = log_result
        lines += ["", "## Live event log", "",
                  f"`logs/nlu_events.jsonl`: {t['n']:,} events; PSI locale {t['psi_locale']}, intent {t['psi_intent']}, "
                  f"slot labels {t['psi_slot_labels']}; fallback rate {t['fallback_rate']:.1%}. "
                  + ("Triggers fired: " + (", ".join(t["fired"]) or "none") if t["enough_data"] else
                     f"**Not enough data** for a decision (fewer than {r['min_utterances']:,} events; the log so far "
                     "holds only test and demo traffic).")]
    lines += ["", "Evidently HTML reports: `reports/monitoring/evidently_*.html` (columns: locale, predicted intent, "
              "characters, predicted slot count). The live log has no utterance length: length is computed offline "
              "from the splits only."]
    (ROOT / "reports" / "drift_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", help="also check the live event log, e.g. logs/nlu_events.jsonl")
    args = ap.parse_args()
    cfg = load_config()
    from src.serving.nlu import OnnxNLU
    run = os.path.basename(os.path.dirname(cfg["models"]["deployed_checkpoint"]))
    nlu = OnnxNLU(ROOT / cfg["serving"]["onnx_dir"] / run, threads=os.cpu_count(), quantized=cfg["serving"]["quantized"])
    train, dev, test = (predict_split(nlu, cfg, p) for p in ("train", "dev", "test"))
    ref, dev_fallback = profile(train), profile(dev)["fallback_rate"]

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "reference_profile.json").write_text(json.dumps(
        {"source": "train split, deployed-model predictions", "n": ref["n"],
         "locale": ref["locale"], "intent": ref["intent"], "slot_labels": ref["slot_labels"],
         "n_chars_mean": sum(r["n_chars"] for r in train) / len(train),
         "fallback_rate_train": ref["fallback_rate"], "fallback_rate_baseline_dev": dev_fallback},
        ensure_ascii=False, indent=1), encoding="utf-8")

    results, evid = {}, {}
    for i, (name, rows) in enumerate(make_batches(test).items()):
        results[name] = {"n": len(rows), **triggers(ref, profile(rows), dev_fallback, cfg["retraining"])}
        evid[name] = evidently_html(random.Random(SEED).sample(train, 20000), rows,
                                    OUT / f"evidently_{['normal', 'drift'][i]}.html")
    log_result = None
    if args.log:
        events = [json.loads(line) for line in (ROOT / args.log).read_text(encoding="utf-8").splitlines() if line]
        cur = profile(events)
        log_result = {"n": cur["n"], **triggers(ref, cur, dev_fallback, cfg["retraining"])}
    (OUT / "drift_results.json").write_text(json.dumps({"batches": results, "evidently": evid, "live_log": log_result},
                                                       indent=1), encoding="utf-8")
    write_report(ref, dev_fallback, results, evid, cfg, log_result)
    print((ROOT / "reports" / "drift_report.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
