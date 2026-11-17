"""Custom actions for the FeastFleet assistant (FeastFleet is a fictional brand).

The assistant uses the FeastFleet orders API (src/shop/app.py; SHOP_URL): it matches a requested dish to the menu
and adds it to the website cart (checkout then takes address and payment), and it tracks orders placed at checkout.
If the API is unreachable it hands off to a person rather than guessing.
"""
import json
import logging
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from rasa_sdk import Action
from rasa_sdk.events import SlotSet
from rasa_sdk.forms import ValidationAction

SHOP_URL = os.environ.get("SHOP_URL", "http://shop:8001")
ORDER_ID = re.compile(r"FF\s*-?\s*(\d{4})", re.IGNORECASE)  # \d also matches Arabic-Indic and Devanagari digits
logger = logging.getLogger(__name__)


def normalise_order_id(text):
    m = ORDER_ID.search(text or "")
    return f"FF-{int(m.group(1)):04d}" if m else None


def shop(path, body=None):
    """Call the orders API -> (status code, JSON body or None). Never logs order contents."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(SHOP_URL + path, data, {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, None
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        logger.warning("orders API unreachable (%s)", type(e).__name__)
        return None, None


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


class ActionAddToCart(Action):
    """Match the dish to the menu and put it in the website cart; checkout takes address and payment."""

    def name(self):
        return "action_add_to_cart"

    def run(self, dispatcher, tracker, domain):
        food = tracker.get_slot("food_type")
        code, item = shop("/api/menu/match?q=" + urllib.parse.quote(food or ""))
        if code == 200:
            dispatcher.utter_message(response="utter_added_to_cart", dish=item["name"])
            # The website's chat widget reads this and adds the dish to the visitor's cart (demo/chat.js).
            dispatcher.utter_message(json_message={"cart_add": {"id": item["id"], "qty": 1}})
        elif code == 404:
            dispatcher.utter_message(response="utter_not_on_menu", food_type=food)
        else:
            dispatcher.utter_message(response="utter_handoff")
        return [SlotSet("food_type", None)]  # a second order in the same conversation asks again


class ActionCheckOrder(Action):
    def name(self):
        return "action_check_order"

    def run(self, dispatcher, tracker, domain):
        order_id = normalise_order_id(tracker.get_slot("order_id"))
        code, order = shop(f"/api/orders/{order_id}") if order_id else (404, None)
        if code == 200 and order["status"] in ("delivered", "ready"):
            dispatcher.utter_message(response="utter_order_delivered", order_id=order_id)
        elif code == 200:
            dispatcher.utter_message(response="utter_order_status", order_id=order_id,
                                     eta=max(1, order["eta_minutes"]))
        elif code == 404:
            dispatcher.utter_message(response="utter_order_not_found")
        else:
            dispatcher.utter_message(response="utter_handoff")
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
