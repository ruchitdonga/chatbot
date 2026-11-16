"""Phase 9 custom actions for the FICTIONAL FeastFleet demo.

MOCK BACKEND: orders live in the dict below (two hard-coded demo orders plus whatever is ordered while the action
server runs). Nothing is stored on disk and no food is ever ordered or delivered.
"""
import itertools
import re
from datetime import datetime, timezone

from rasa_sdk import Action
from rasa_sdk.events import SlotSet
from rasa_sdk.forms import ValidationAction

MOCK_ORDERS = {"FF-1001": {"food": "pizza", "eta": 20}, "FF-1002": {"food": "sushi", "eta": 35}}
_next_id = itertools.count(2001)
ORDER_ID = re.compile(r"FF\s*-?\s*(\d{4})", re.IGNORECASE)  # \d also matches Arabic-Indic and Devanagari digits


def normalise_order_id(text):
    m = ORDER_ID.search(text or "")
    return f"FF-{int(m.group(1)):04d}" if m else None


class ValidateSlotMappings(ValidationAction):
    def name(self):
        return "action_validate_slot_mappings"

    async def extract_language(self, dispatcher, tracker, domain):
        # Sticky: keep the first detected language. Short follow-ups ("pizza", "FF-1001") are often misdetected,
        # and replies switching language mid-conversation would confuse the user.
        if tracker.get_slot("language"):
            return {}
        value = tracker.latest_message.get("feastfleet_locale")  # set by rasa/components/feastfleet_nlu.py
        return {"language": value} if value else {}


class ActionPlaceOrder(Action):
    def name(self):
        return "action_place_order"

    def run(self, dispatcher, tracker, domain):
        order_id, food = f"FF-{next(_next_id)}", tracker.get_slot("food_type")
        MOCK_ORDERS[order_id] = {"food": food, "eta": 30}
        dispatcher.utter_message(response="utter_order_placed", order_id=order_id, food_type=food)
        return [SlotSet("food_type", None)]  # a second order in the same conversation asks again


class ActionCheckOrder(Action):
    def name(self):
        return "action_check_order"

    def run(self, dispatcher, tracker, domain):
        order_id = normalise_order_id(tracker.get_slot("order_id"))
        if order_id in MOCK_ORDERS:
            dispatcher.utter_message(response="utter_order_status", order_id=order_id,
                                     eta=MOCK_ORDERS[order_id]["eta"])
        else:
            dispatcher.utter_message(response="utter_order_not_found")
        return [SlotSet("order_id", None)]


class ActionTellTime(Action):
    def name(self):
        return "action_tell_time"

    def run(self, dispatcher, tracker, domain):
        dispatcher.utter_message(response="utter_time", time=datetime.now(timezone.utc).strftime("%H:%M"))
        return []


if __name__ == "__main__":  # self-check: python -m actions.actions (inside the rasa-sdk image)
    assert normalise_order_id("it's ff 1001 please") == "FF-1001"
    assert normalise_order_id("FF-١٠٠٢") == "FF-1002"
    assert normalise_order_id("my pizza") is None and normalise_order_id(None) is None
    print("actions self-check passed")
