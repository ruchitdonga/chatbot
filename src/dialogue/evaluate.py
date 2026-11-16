"""Phase 9: run the scripted conversations through the live Rasa stack and score them (FICTIONAL FeastFleet demo).

Needs the NLU service on the host and Rasa with its HTTP API on, so each conversation's tracker can be read:
  uvicorn src.serving.app:create_app --factory --port 8000
  docker compose run -d --service-ports --name ff-eval rasa run --enable-api
  python -m src.dialogue.evaluate
Writes reports/dialogue_eval.md and reports/dialogue_eval.json. The texts in the report are the authored test
sentences from data/dialogue_eval/, not user data.
"""
import argparse
import json
import urllib.request
import uuid
from collections import Counter, defaultdict

import yaml

from src.data.load import ROOT

SCRIPT = ROOT / "data" / "dialogue_eval" / "scripted_conversations.yaml"
TASK_GOALS = {"order", "status"}


def call(url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def split_turns(events):
    """Tracker events -> per user message: predicted intent and the responses (without utter_) that followed."""
    turns, language = [], None
    for e in events:
        if e["event"] == "user":
            turns.append({"intent": e["parse_data"]["intent"]["name"], "bot": []})
        elif e["event"] == "bot" and turns:
            turns[-1]["bot"].append((e.get("metadata") or {}).get("utter_action", "?").removeprefix("utter_"))
        elif e["event"] == "slot" and e["name"] == "language":
            language = e["value"]
    return turns, language


def category(expected, got, prev_got, language_ok, disclosed):
    """Failure category for one turn, or None if the turn passed."""
    if expected == got and language_ok and disclosed:
        return None
    if not disclosed:
        return "no disclosure first"
    if not language_ok:
        return "wrong language detected"
    if "handoff" in got and "handoff" not in expected:
        return "handoff instead of answer"
    if "handoff" in expected and "handoff" not in got:
        return "missed handoff"
    if any(g.startswith("ask_") for g in got) and got == prev_got:
        return "slot-fill loop"
    return "misroute"


def score(conv, turns, language):
    """Compare one conversation's tracker turns with the script -> list of per-turn result dicts."""
    language_ok = conv["locale"] is None or language == conv["locale"]
    results, prev = [], None
    for i, step in enumerate(conv["turns"]):
        actual = turns[i] if i < len(turns) else {"intent": None, "bot": []}
        got, disclosed = list(actual["bot"]), True
        if i == 0:
            disclosed = bool(got) and got[0] == "disclosure"
            got = got[1:] if disclosed else got
        results.append({"conversation": conv["id"], "locale": conv["locale"], "goal": conv["goal"], "turn": i + 1,
                        "user": step["user"], "expected": step["expect"], "got": got, "intent": actual["intent"],
                        "detected_language": language,
                        "failure": category(step["expect"], got, prev, language_ok, disclosed)})
        prev = got
    return results


def run(url):
    convs = yaml.safe_load(SCRIPT.read_text(encoding="utf-8"))["conversations"]
    turns_out = []
    for conv in convs:
        sender = f"eval-{conv['id']}-{uuid.uuid4().hex[:6]}"
        for step in conv["turns"]:
            body = {"sender": sender, "message": step["user"]}
            if conv.get("hint"):
                body["metadata"] = {"language": conv["hint"]}
            call(f"{url}/webhooks/rest/webhook", body)
        events = call(f"{url}/conversations/{sender}/tracker?include_events=ALL")["events"]
        turns_out += score(conv, *split_turns(events))
    return convs, turns_out


def rate(n, d):
    return f"{n}/{d} ({100 * n / d:.0f}%)" if d else "–"


def report(convs, turns):
    by_conv = defaultdict(list)
    for t in turns:
        by_conv[t["conversation"]].append(t)
    done = {c["id"]: all(t["failure"] is None for t in by_conv[c["id"]]) for c in convs}
    tasks = [c for c in convs if c["goal"] in TASK_GOALS]
    failed = [t for t in turns if t["failure"]]
    lines = ["# Scripted conversation evaluation (Phase 9)", "",
             "FeastFleet is a FICTIONAL business; orders are mock. Conversations authored before running "
             "(`data/dialogue_eval/scripted_conversations.yaml`); non-English sentences unreviewed.", "",
             "A conversation is completed when every turn gives exactly the scripted replies, in the expected "
             "language, with the AI disclosure first.", "",
             "| Measure | Result |", "|---|---|",
             f"| Task completion (order / order-status conversations) | {rate(sum(done[c['id']] for c in tasks), len(tasks))} |",
             f"| All conversations completed | {rate(sum(done.values()), len(convs))} |",
             f"| Turns correct | {rate(len(turns) - len(failed), len(turns))} |",
             f"| Disclosure first | {rate(sum(t['failure'] != 'no disclosure first' for t in turns if t['turn'] == 1), len(convs))} |",
             "", "## By language", "", "| Locale | Completed | Task completion |", "|---|---|---|"]
    for loc in dict.fromkeys(c["locale"] for c in convs):
        cs = [c for c in convs if c["locale"] == loc]
        ts = [c for c in cs if c["goal"] in TASK_GOALS]
        lines.append(f"| {loc or 'unsupported'} | {rate(sum(done[c['id']] for c in cs), len(cs))} | "
                     f"{rate(sum(done[c['id']] for c in ts), len(ts))} |")
    lines += ["", "## By goal", "", "| Goal | Completed |", "|---|---|"]
    for goal in dict.fromkeys(c["goal"] for c in convs):
        cs = [c for c in convs if c["goal"] == goal]
        lines.append(f"| {goal} | {rate(sum(done[c['id']] for c in cs), len(cs))} |")
    lines += ["", f"## Failed turns ({len(failed)})", "", "| Category | Turns |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in Counter(t["failure"] for t in failed).most_common()]
    lines += ["", "| Conversation | Turn | User | Expected | Got | NLU intent | Language | Category |",
              "|---|---|---|---|---|---|---|---|"]
    for t in failed:
        lines.append(f"| {t['conversation']} | {t['turn']} | {t['user']} | {', '.join(t['expected'])} | "
                     f"{', '.join(t['got']) or '(nothing)'} | {t['intent']} | {t['detected_language']} | {t['failure']} |")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:5005")
    args = ap.parse_args()
    convs, turns = run(args.url)
    (ROOT / "reports" / "dialogue_eval.json").write_text(json.dumps(turns, ensure_ascii=False, indent=1), encoding="utf-8")
    text = report(convs, turns)
    (ROOT / "reports" / "dialogue_eval.md").write_text(text, encoding="utf-8")
    print(text.split("## By language")[0])


if __name__ == "__main__":
    main()
