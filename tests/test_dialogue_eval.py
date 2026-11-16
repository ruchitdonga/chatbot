"""Phase 9: scoring of scripted conversations from Rasa tracker events (synthetic events, no Rasa needed)."""
from src.dialogue.evaluate import score, split_turns


def ev_user(intent):
    return {"event": "user", "parse_data": {"intent": {"name": intent}}}


def ev_bot(name):
    return {"event": "bot", "metadata": {"utter_action": f"utter_{name}"}}


CONV = {"id": "c", "locale": "es-ES", "goal": "order",
        "turns": [{"user": "a", "expect": ["ask_food_type"]}, {"user": "b", "expect": ["order_placed"]}]}


def test_completed_conversation():
    events = [ev_user("takeaway_order"), {"event": "slot", "name": "language", "value": "es-ES"},
              ev_bot("disclosure"), ev_bot("ask_food_type"), ev_user("nlu_fallback"), ev_bot("order_placed")]
    assert [t["failure"] for t in score(CONV, *split_turns(events))] == [None, None]


def test_failure_categories():
    loop = [ev_user("takeaway_order"), {"event": "slot", "name": "language", "value": "es-ES"},
            ev_bot("disclosure"), ev_bot("ask_food_type"), ev_user("nlu_fallback"), ev_bot("ask_food_type")]
    assert [t["failure"] for t in score(CONV, *split_turns(loop))] == [None, "slot-fill loop"]
    wrong_lang = [ev_user("takeaway_order"), {"event": "slot", "name": "language", "value": "en-US"},
                  ev_bot("disclosure"), ev_bot("ask_food_type")]
    assert score(CONV, *split_turns(wrong_lang))[0]["failure"] == "wrong language detected"
    handoff = [ev_user("nlu_fallback"), ev_bot("disclosure"), ev_bot("handoff")]
    res = score({**CONV, "locale": None}, *split_turns(handoff))
    assert [t["failure"] for t in res] == ["handoff instead of answer", "misroute"]  # turn 2 never happened
    assert score(CONV, *split_turns([ev_user("x"), ev_bot("greet")]))[0]["failure"] == "no disclosure first"
