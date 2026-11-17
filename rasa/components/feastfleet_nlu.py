"""Phase 9: Rasa NLU component that calls the FeastFleet NLU service (src/serving/app.py, POST /predict).

Rasa has no built-in HTTP NLU connector, so this GraphComponent sets intent, intent_ranking and entities itself.
FeastFleet is a FICTIONAL food-delivery business (configs/business.yaml).

Intent mapping (the dialogue only needs these):
- handoff with reason out_of_scope        -> out_of_scope   (explicit request for a person, unsupported topic)
- any other handoff (energy below the signed-off threshold, empty, unsupported language) -> nlu_fallback
- answered_intents / offer_handoff_intents -> unchanged
- every other MASSIVE intent               -> unsupported_request ("I can't help with that here")

The Phase 7 rule is energy-based and already applied by the service, so the pipeline has no FallbackClassifier:
its probability threshold would be a second, unvalidated rule. Only the entities listed in `entities` enter the
tracker, so personal-data slots such as person or place_name are never stored. The detected locale is passed as
the parse field `feastfleet_locale` and fills the `language` slot.
"""
import logging
import re

import requests
from rasa.engine.graph import ExecutionContext, GraphComponent
from rasa.engine.recipes.default_recipe import DefaultV1Recipe
from rasa.engine.storage.resource import Resource
from rasa.engine.storage.storage import ModelStorage
from rasa.shared.nlu.training_data.message import Message
from rasa.shared.nlu.training_data.training_data import TrainingData
from rasa.shared.utils.io import read_yaml_file

logger = logging.getLogger(__name__)
EXTRACTOR = "FeastFleetNLU"
LOCALE_KEY = "feastfleet_locale"
# A FeastFleet order number in any message means "track this order", whatever the model makes of the rest
# ("FF-2016" alone scores as low confidence). \d also matches Arabic-Indic and Devanagari digits.
ORDER_ID = re.compile(r"FF\s*-?\s*(\d{4})", re.IGNORECASE)


FAQ_INTENTS = {"fees": "faq_fees", "time": "faq_time", "payment": "faq_payment", "price": "faq_price",
               "veg": "faq_veg", "menu": "faq_menu"}


def _has(text, word):
    """Substring match; short Latin words ("upi", "menu") must be whole words so "cupid" is not "upi"."""
    if word.isascii() and len(word) <= 5 and word.replace(" ", "").isalpha():
        return re.search(rf"\b{re.escape(word)}\b", text) is not None
    return word in text


def with_faq(text, intent, faq):
    """Store questions (configs/faq.yaml) the model has no intent for; complaints are never turned into FAQs.

    Overrides out_of_scope too: the out-of-scope training data covered payment and allergy problems, so the model
    sends "how can I pay?" to a person. Complaint words keep real complaints with a person (0 of the 110
    challenge-set items match an FAQ topic without one, measured 2026-11-17)."""
    t = text.casefold()
    if any(_has(t, w) for w in faq["complaint_words"]):
        return intent
    for topic, words in faq["topics"].items():  # file order is priority order
        if any(_has(t, w.casefold()) for w in words):
            return {"name": FAQ_INTENTS[topic], "confidence": intent["confidence"]}
    return intent


def with_order_number(text, intent, ents):
    """Route a message carrying an order number to tracking, with the number as an order_id entity."""
    m = ORDER_ID.search(text)
    if not m or intent["name"] == "out_of_scope":  # a complaint that quotes its order number still goes to a person
        return intent, ents
    order = {"entity": "order_id", "value": f"FF-{int(m.group(1)):04d}", "start": m.start(), "end": m.end(),
             "extractor": EXTRACTOR}
    return {"name": "takeaway_query", "confidence": intent["confidence"]}, ents + [order]


def to_rasa(pred, keep, entities, exempt=frozenset()):
    """Service /predict response -> (Rasa intent dict, Rasa entity list)."""
    if pred["handoff"] and not (pred["handoff_reason"] == "low_confidence" and pred["intent"] in exempt):
        name = "out_of_scope" if pred["handoff_reason"] == "out_of_scope" else "nlu_fallback"
    else:
        name = pred["intent"] if pred["intent"] in keep else "unsupported_request"
    ents = [{"entity": s["label"], "value": s["value"], "start": s["start"], "end": s["end"], "extractor": EXTRACTOR}
            for s in pred["slots"] if s["label"] in entities]
    return {"name": name, "confidence": pred["confidence"]}, ents


@DefaultV1Recipe.register(
    [DefaultV1Recipe.ComponentType.INTENT_CLASSIFIER, DefaultV1Recipe.ComponentType.ENTITY_EXTRACTOR],
    is_trainable=False)
class FeastFleetNLU(GraphComponent):
    @staticmethod
    def get_default_config():
        return {"url": "http://nlu:8000/predict", "business_config": "/configs/business.yaml",
                "faq_config": "/configs/faq.yaml",
                "entities": ["food_type"], "timeout": 5}

    def __init__(self, config):
        self.url, self.timeout, self.entities = config["url"], config["timeout"], set(config["entities"])
        business = read_yaml_file(config["business_config"])
        self.keep = set(business["answered_intents"]) | set(business["offer_handoff_intents"])
        self.exempt = set(business.get("low_confidence_exempt_intents", []))
        self.faq = read_yaml_file(config["faq_config"])

    @classmethod
    def create(cls, config, model_storage: ModelStorage, resource: Resource, execution_context: ExecutionContext):
        return cls(config)

    def process_training_data(self, training_data: TrainingData) -> TrainingData:
        return training_data

    def process(self, messages: list[Message]) -> list[Message]:
        for message in messages:
            text = message.get("text") or ""
            if text.startswith("/"):  # button payloads such as /affirm are parsed by Rasa's RegexMessageHandler
                continue
            hint = (message.get("metadata") or {}).get("language")
            try:
                response = requests.post(self.url, json={"text": text, "language": hint}, timeout=self.timeout)
                response.raise_for_status()
                pred = response.json()
                intent, ents = to_rasa(pred, self.keep, self.entities, self.exempt)
                intent, ents = with_order_number(text, with_faq(text, intent, self.faq), ents)
                locale = pred["locale"]
            except (requests.RequestException, KeyError, ValueError) as e:
                # Service down or malformed: hand off rather than guess. Never log the text.
                logger.warning("NLU service call failed (%s); routing to nlu_fallback", type(e).__name__)
                intent, ents, locale = {"name": "nlu_fallback", "confidence": 0.0}, [], None
            # A parse field, not an entity: it has no text span, and the language slot reads it (actions.py).
            message.set(LOCALE_KEY, locale, add_to_output=True)
            message.set("intent", intent, add_to_output=True)
            message.set("intent_ranking", [intent], add_to_output=True)
            message.set("entities", message.get("entities", []) + ents, add_to_output=True)
        return messages


if __name__ == "__main__":  # self-check, run inside the Rasa image: python -m components.feastfleet_nlu
    keep, ents = {"takeaway_order", "general_quirky"}, {"food_type"}
    base = {"locale": "es-ES", "confidence": 0.9, "handoff": False, "handoff_reason": None,
            "slots": [{"label": "food_type", "value": "pizza", "start": 0, "end": 5},
                      {"label": "person", "value": "Ana", "start": 6, "end": 9}]}
    i, e = to_rasa({**base, "intent": "takeaway_order"}, keep, ents)
    assert i["name"] == "takeaway_order" and [(x["entity"], x["value"]) for x in e] == [("food_type", "pizza")], e
    assert to_rasa({**base, "intent": "alarm_set"}, keep, ents)[0]["name"] == "unsupported_request"
    oos = {**base, "intent": "out_of_scope", "handoff": True, "handoff_reason": "out_of_scope"}
    assert to_rasa(oos, keep, ents)[0]["name"] == "out_of_scope"
    for reason in ("low_confidence", "empty", "unsupported_language"):
        assert to_rasa({**base, "intent": None, "handoff": True, "handoff_reason": reason}, keep, ents)[0][
                   "name"] == "nlu_fallback"
    greet = {**base, "intent": "general_greet", "handoff": True, "handoff_reason": "low_confidence"}
    keep2, exempt = keep | {"general_greet"}, {"general_greet"}
    assert to_rasa(greet, keep2, ents, exempt)[0]["name"] == "general_greet"
    assert to_rasa(greet, keep2, ents)[0]["name"] == "nlu_fallback"  # no exemption configured
    assert to_rasa({**greet, "handoff_reason": "unsupported_language"}, keep2, ents, exempt)[0]["name"] == "nlu_fallback"
    low = {"name": "nlu_fallback", "confidence": 0.3}
    i, e = with_order_number("FF-2016", low, [])
    assert i["name"] == "takeaway_query" and e[0]["entity"] == "order_id" and e[0]["value"] == "FF-2016"
    assert with_order_number("where is my order ff 1001?", low, [])[1][0]["value"] == "FF-1001"
    complaint = {"name": "out_of_scope", "confidence": 0.9}
    assert with_order_number("FF-2016 arrived cold, refund me", complaint, [])[0]["name"] == "out_of_scope"
    assert with_order_number("pizza", low, []) == (low, [])
    faq = read_yaml_file("/configs/faq.yaml")
    order = {"name": "takeaway_order", "confidence": 0.9}
    for words, name in [("how much is delivery?", "faq_fees"), ("डिलीवरी चार्ज कितना है?", "faq_fees"),
                        ("can i pay cash on delivery", "faq_payment"), ("how much is the biryani", "faq_price"),
                        ("do you have vegetarian food", "faq_veg"), ("what's on the menu", "faq_menu"),
                        ("メニューを見せて", "faq_menu"), ("i want to order a pizza", "takeaway_order"),
                        ("i was charged twice, refund me", "takeaway_order")]:
        assert with_faq(words, order, faq)["name"] == name, (words, with_faq(words, order, faq))
    assert with_faq("how can i pay?", complaint, faq)["name"] == "faq_payment"  # plain question beats out_of_scope
    assert with_faq("my card payment failed, i want a refund", complaint, faq) == complaint  # complaint stays
    print("feastfleet_nlu self-check passed")
