"""FeastFleet orders API (FeastFleet is a fictional brand). Shared by the website checkout and the chat assistant.

GET  /api/menu                 menu with prices (integer paise, INR) and veg/non-veg flags
POST /api/orders               checkout: cart items, delivery or pickup, contact, payment (card or cash on delivery)
GET  /api/menu/match?q=        the menu item a customer's words mean, in any of the assistant's languages
                               (&all=true: every dish named; &typos=true: close spellings, for orders only)
GET  /api/orders/{id}          status timeline for tracking (no contact details)
POST /api/handoffs             the chat widget hands a conversation to a person (transcript so far)
GET  /api/handoffs             agent inbox: open chats; GET/POST /api/handoffs/{id}/messages; POST .../close
The assistant never places orders itself: it adds the matched dish to the website cart, and checkout does the rest.

Payments are simulated: the browser sends only the card brand and last four digits, never the card number, expiry or
CVC; a card ending 0002 is declined (test card). Orders live in memory only and are never logged.
Run: uvicorn src.shop.app:app --port 8001
"""
import difflib
import itertools
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

import yaml
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

CURRENCY = "INR"  # amounts in paise
DELIVERY_FEE, FREE_DELIVERY_FROM = 4000, 49900
DELIVERY_MINUTES, PICKUP_MINUTES = 30, 15
MAX_OPEN_HANDOFFS, MAX_HANDOFF_MESSAGES = 50, 200


def dish(id_, name, desc, rupees, category, emoji, veg):
    return {"id": id_, "name": name, "desc": desc, "price": rupees * 100, "category": category, "emoji": emoji,
            "veg": veg}


MENU = [  # veg follows the Indian veg/non-veg marker; egg counts as non-veg
    dish("biryani", "Hyderabadi chicken biryani", "Dum-cooked with saffron, served with mirchi ka salan and raita", 289, "Biryani & rice", "🍛", False),
    dish("mutton-biryani", "Mutton biryani", "Slow-cooked basmati, fried onions, boiled egg", 349, "Biryani & rice", "🍲", False),
    dish("veg-pulao", "Veg pulao", "Basmati with whole spices and vegetables, raita on the side", 189, "Biryani & rice", "🍚", True),
    dish("dosa", "Masala dosa", "Crisp rice crêpe, spiced potato, sambar and coconut chutney", 129, "South Indian", "🥞", True),
    dish("idli-vada", "Idli vada combo", "Two idli, one medu vada, sambar and chutney", 99, "South Indian", "🍘", True),
    dish("paneer", "Paneer butter masala", "Cottage cheese in a tomato and cashew gravy", 239, "Curries & breads", "🍲", True),
    dish("dal-makhani", "Dal makhani", "Black lentils slow-cooked with butter and cream", 199, "Curries & breads", "🥘", True),
    dish("naan", "Butter naan", "Tandoor-baked, brushed with butter", 49, "Curries & breads", "🫓", True),
    dish("pav-bhaji", "Pav bhaji", "Spiced mashed vegetables, two buttered pav", 149, "Street food", "🍛", True),
    dish("vada-pav", "Vada pav", "Potato fritter in a pav with green and garlic chutney", 59, "Street food", "🍔", True),
    dish("margherita", "Margherita pizza", "Tomato, mozzarella, basil", 249, "Pizza", "🍕", True),
    dish("tikka-pizza", "Chicken tikka pizza", "Tandoori chicken, onion, capsicum", 329, "Pizza", "🍕", False),
    dish("sushi", "Salmon sushi", "12 pieces, pickled ginger, wasabi", 499, "Japanese", "🍣", False),
    dish("ramen", "Chicken ramen", "Rich broth, noodles, soft egg, spring onion", 399, "Japanese", "🍜", False),
    dish("shawarma", "Chicken shawarma roll", "Garlic toum, pickles, fries", 179, "Middle Eastern", "🌯", False),
    dish("falafel", "Falafel wrap", "Tahini, salad, pickled turnip", 159, "Middle Eastern", "🧆", True),
    dish("doro-wat", "Doro wat", "Ethiopian spiced chicken stew with injera", 329, "East African", "🍗", False),
    dish("chips-mayai", "Chips mayai", "Kenyan chips omelette with kachumbari", 169, "East African", "🍳", False),
    dish("gulab-jamun", "Gulab jamun", "Two warm dumplings in rose-cardamom syrup", 89, "Sweets & drinks", "🍮", True),
    dish("lassi", "Mango lassi", "Yoghurt, Alphonso mango, cardamom", 79, "Sweets & drinks", "🥭", True),
]
MENU_BY_ID = {m["id"]: m for m in MENU}
# Words customers use for each dish in the assistant's languages (AI-written, unreviewed). The longest alias found in
# the customer's words wins, so "chicken pizza" beats "pizza".
ALIASES = {
    "biryani": ["biryani", "biriyani", "बिरयानी", "பிரியாணி", "برياني", "ビリヤニ", "ብርያኒ", "ብሪያኒ"],
    "mutton-biryani": ["mutton biryani", "mutton", "मटन", "மட்டன்"],
    "veg-pulao": ["pulao", "pulav", "पुलाव", "चावल", "rice", "arroz", "reis", "riz", "wali", "أرز", "ご飯", "சாதம்"],
    "dosa": ["dosa", "dosai", "डोसा", "தோசை", "ドーサ"],
    "idli-vada": ["idli", "vada", "इडली", "இட்லி", "வடை"],
    "paneer": ["paneer", "पनीर", "பனீர்"],
    "dal-makhani": ["dal", "daal", "दाल", "பருப்பு"],
    "naan": ["naan", "नान", "roti", "रोटी", "bread", "brot", "pain", "ナン", "خبز"],
    "pav-bhaji": ["pav bhaji", "bhaji", "पाव भाजी", "भाजी"],
    "vada-pav": ["vada pav", "vadapav", "वड़ा पाव", "वडा पाव"],
    "margherita": ["pizza", "pizze", "pizzen", "margherita", "पिज़्ज़ा", "पिज्जा", "பிட்சா", "பீட்சா", "بيتزا", "ピザ", "ፒዛ"],
    "tikka-pizza": ["chicken pizza", "tikka pizza", "pepperoni", "salami pizza", "salamipizza", "चिकन पिज़्ज़ा"],
    "sushi": ["sushi", "sushis", "寿司", "すし", "सुशी", "سوشي", "ሱሺ"],
    "ramen": ["ramen", "ラーメン", "noodles", "noodle", "नूडल्स", "nudeln", "nouilles", "fideos"],
    "shawarma": ["shawarma", "shawerma", "شاورما", "शावरमा", "döner", "doner", "kebab", "كباب"],
    "falafel": ["falafel", "فلافل", "फलाफल"],
    "doro-wat": ["doro wat", "doro wot", "ዶሮ ወጥ", "ዶሮ", "injera", "እንጀራ"],
    "chips-mayai": ["chips mayai", "chipsi mayai", "chipsi", "mayai"],
    "gulab-jamun": ["gulab jamun", "jamun", "गुलाब जामुन", "मिठाई", "dessert", "postre", "nachtisch"],
    "lassi": ["lassi", "लस्सी", "லஸ்ஸி", "لاسي", "ラッシー", "ላሲ"],
}


def _alias_spans(alias, text):
    """Where an alias occurs. ASCII aliases must be whole words, plurals allowed ("price" is not "rice", German
    "preis" is not "reis", "biryanis" is biryani); other scripts (Japanese has no spaces) match as substrings."""
    pattern = rf"\b{re.escape(alias)}(?:s|es)?\b" if alias.isascii() else re.escape(alias)
    return [m.span() for m in re.finditer(pattern, text)]


# Typos are matched only against the dishes' own names ("pulao", "biryani"), not generic words like "bread" or
# "postre", which near-miss everyday words ("read", "poste"); words of 5+ letters, so a slip stays unambiguous.
TYPO_ALIASES = {w: d for d, aliases in ALIASES.items() for a in aliases if a.isascii() and a.isalpha() and len(a) >= 5
                for w in [a] if w in re.findall(r"[a-z]+", MENU_BY_ID[d]["name"].casefold())}
BY_LENGTH = sorted(((a.casefold(), d) for d, aliases in ALIASES.items() for a in aliases), key=lambda x: -len(x[0]))

# Words that turn a plain pizza or biryani into its variant when written next to it ("pizza de pollo tikka",
# "Lamm-Biryanis", "biryani ya mbuzi"); on their own they name no dish ("chicken" is also chicken biryani).
VARIANTS = {
    "tikka-pizza": ("margherita", ["tikka", "chicken", "pollo", "poulet", "hähnchen", "huhn", "kuku", "चिकन",
                                   "சிக்கன்", "دجاج", "بالدجاج", "チキン"]),
    "mutton-biryani": ("biryani", ["lamm", "lamb", "agneau", "mouton", "cordero", "mbuzi", "لحم", "ضأن", "マトン"]),
}
MODIFIERS = sorted(((w.casefold(), v) for v, (_, words) in VARIANTS.items() for w in words), key=lambda x: -len(x[0]))
# Words that join two separate dishes: "a pizza and a chicken pizza" is two dishes, not one variant.
AND = {"and", "et", "und", "y", "e", "aur", "or", "ou", "oder", "o", "na", "और", "மற்றும்", "እና", "و", "&", "+"}

# Swahili "wali" (rice) is also Hinglish "the one" ("spicy wali biryani"): not a dish in a message that has Hinglish
# marker words (configs/faq.yaml, the list the assistant uses to spot Hinglish).
HINGLISH = set(yaml.safe_load((Path(__file__).resolve().parents[2] / "configs" / "faq.yaml").read_text(encoding="utf-8"))
               ["hinglish_words"])
NOT_IN_HINGLISH = {"wali"}
# Quantities (AI-written, unreviewed). Words before the dish in every language listed; after the dish only where the
# language puts it there (Swahili "pizza tatu"), because Hindi "दो" after a dish is "give" ("डोसा दे दो").
SWAHILI_NUMBERS = dict(zip("mbili tatu nne tano sita saba nane tisa kumi".split(), range(2, 11)))
NUMBER_WORDS = SWAHILI_NUMBERS | {w: n for words in [
    "two three four five six seven eight nine ten",          # English
    "deux trois quatre cinq six sept huit neuf dix",         # French
    "zwei drei vier fünf sechs sieben acht neun zehn",       # German
    "dos tres cuatro cinco seis siete ocho nueve diez",      # Spanish
    "दो तीन चार पाँच छह सात आठ नौ दस",                        # Hindi
] for n, w in enumerate(words.split(), 2)} | {"पांच": 5}
KANJI = dict(zip("二三四五六七八九十", range(2, 11)))
AFTER = re.compile(r"\s*(?:を|が|は)?\s*(?:[x×]\s*)?(?:(\d{1,2})(?!\d)|([二三四五六七八九十])(?=[つ枚個皿本杯人])|("
                   + "|".join(SWAHILI_NUMBERS) + r")\b)")


def _number(token):
    """A quantity written as one token ("2", "3x", "२", "و٢", "drei"), else None."""
    tok = token.strip(".,!?;:()").removeprefix("و")
    digits = tok.strip("x×")  # "3x"; only for digits, so "deux" and "six" keep their x
    if digits.isdigit() and len(digits) <= 2:
        return int(digits)  # int() reads Devanagari and Arabic-Indic digits too
    return NUMBER_WORDS.get(tok)


def _qty_before(segment, offset):
    """A number at most three words before the dish, not across "and" or a comma -> (qty, position) or None."""
    for m in reversed(list(re.finditer(r"\S+", segment))[-4:]):
        n = _number(m.group())
        if n:
            return n, offset + m.start()
        if m.group().strip(".!?") in AND or "," in m.group() or "、" in m.group():
            return None
    return None


def _joined(gap):
    """True when two words belong to one dish: at most four other words between, no "and" or comma."""
    if any(c in gap for c in ",、と"):
        return False
    toks = gap.split()
    return len(toks) <= 4 and not any(t.strip(".!?") in AND or t.startswith("و") for t in toks)


def match_dishes(text, typos=False):
    """Every menu item named in the text, in the order written: [(item, matched words, quantity)]. Longest alias
    first, so "chicken pizza" is one dish, not two; a plain pizza or biryani next to a variant word becomes that
    variant (VARIANTS). The quantity is a number just before the dish or, where the language puts it there, just
    after (else 1). typos=True also accepts a close spelling of a long one-word alias ("veg ulao"); only for text
    already known to be an order or a price question, because on everyday text it names dishes that were never
    meant (French "nouvelles" -> noodles; measured on MASSIVE, 2026-11-17)."""
    raw = (text or "").casefold()
    t = raw.replace("-", " ")  # "Chicken-Tikka-Pizzen"; same length, so positions match raw
    hinglish = bool(HINGLISH & set(re.findall(r"[a-z]+", t)))
    hits = []  # [start, end, dish id, is a variant word]

    def take(words, dish_id, modifier=False):
        nonlocal t
        for start, end in _alias_spans(words, t):
            hits.append([start, end, dish_id, modifier])
            t = t[:start] + " " * (end - start) + t[end:]  # blank it so "pizza" inside "chicken pizza" is not reused

    for alias, dish_id in BY_LENGTH:
        if not (hinglish and alias in NOT_IN_HINGLISH):
            take(alias, dish_id)
    for word, variant in MODIFIERS:
        take(word, variant, modifier=True)
    if typos:
        for m in re.finditer(r"[a-z]{4,}", t):
            close = difflib.get_close_matches(m.group(), TYPO_ALIASES, n=1, cutoff=0.85)
            if close and not close[0].startswith(m.group()):  # a cut-off name is usually another word (German "lass")
                hits.append([m.start(), m.end(), TYPO_ALIASES[close[0]], False])
    hits.sort()

    # Quantities: first a number before each dish, then, for dishes still without one, a number after it that no
    # other dish has taken. Variant words do not end the stretch searched ("3 large chicken tikka pizzas").
    dishes = [h for h in hits if not h[3]]
    qty, used = {}, set()
    for i, (start, _, _, _) in enumerate(dishes):
        offset = dishes[i - 1][1] if i else 0
        found = _qty_before(raw[offset:start], offset)
        if found:
            qty[start] = found[0]
            used.add(found[1])
    for i, (start, end, _, _) in enumerate(dishes):
        stop = dishes[i + 1][0] if i + 1 < len(dishes) else len(raw)
        m = AFTER.match(raw, end, stop)
        if start not in qty and m and m.start(m.lastindex) not in used:
            g = m.group(m.lastindex)
            qty[start] = KANJI.get(g) or SWAHILI_NUMBERS.get(g) or int(g)
            used.add(m.start(m.lastindex))

    # A plain pizza or biryani next to one of its variant words is that variant.
    merged = []
    for h in hits:
        h = [*h, qty.get(h[0])]
        prev = merged[-1] if merged else None
        if prev and _joined(raw[prev[1]:h[0]]):
            pair = {prev[2], h[2]}
            variant = next((v for v, (plain, _) in VARIANTS.items()
                            if pair == {v, plain} or (pair == {v} and prev[3] != h[3])), None)
            if variant:
                prev[1], prev[2], prev[3], prev[4] = h[1], variant, prev[3] and h[3], prev[4] or h[4]
                continue
        merged.append(h)

    out, index = [], {}
    for start, end, dish_id, modifier, n in merged:
        if modifier:
            continue  # "chicken" with no pizza next to it names no dish
        n = n or 1
        if dish_id in index:  # the same dish twice: add the quantities
            item, words, old = out[index[dish_id]]
            out[index[dish_id]] = (item, words, min(old + n, 20))
        else:
            index[dish_id] = len(out)
            out.append((MENU_BY_ID[dish_id], raw[start:end], min(max(n, 1), 20)))  # the cart allows 1-20 of a dish
    return out


def match_dish(text, typos=False):
    """(menu item, matched words, quantity) for the longest dish name in the text, or None."""
    hits = match_dishes(text, typos)
    return max(hits, key=lambda h: len(h[1])) if hits else None
STEPS = ["confirmed", "preparing", "on_the_way", "delivered"]
PICKUP_STEPS = ["confirmed", "preparing", "ready"]
PHONE = re.compile(r"^\+?[0-9 ()-]{7,20}$")


class Item(BaseModel):
    id: str
    qty: int = Field(ge=1, le=20)


class Contact(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    phone: str = Field(max_length=25)
    address: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=200)


class Payment(BaseModel):
    method: Literal["card", "cod"]
    card_brand: str | None = Field(default=None, max_length=20)
    card_last4: str | None = Field(default=None, pattern=r"^\d{4}$")  # the only card data the server ever sees


class ChatMessage(BaseModel):
    sender: Literal["customer", "bot", "agent"]
    text: str = Field(min_length=1, max_length=1000)


class HandoffRequest(BaseModel):
    conversation_id: str = Field(pattern=r"^[A-Za-z0-9_-]{8,64}$")
    language: str = Field(default="auto", max_length=10)
    transcript: list[ChatMessage] = Field(default_factory=list, max_length=50)  # the chat so far, for the agent


class AgentMessage(BaseModel):
    sender: Literal["customer", "agent"]
    text: str = Field(min_length=1, max_length=1000)


class OrderRequest(BaseModel):
    items: list[Item] = Field(min_length=1, max_length=30)
    fulfilment: Literal["delivery", "pickup"]
    contact: Contact
    payment: Payment


def totals(lines, fulfilment):
    subtotal = sum(line["price"] * line["qty"] for line in lines)
    fee = 0 if fulfilment == "pickup" or subtotal >= FREE_DELIVERY_FROM else DELIVERY_FEE
    return {"subtotal": subtotal, "delivery_fee": fee, "total": subtotal + fee, "currency": CURRENCY}


def status(order, now=None):
    """Status timeline from the time since the order (simulated kitchen and rider)."""
    now = now or datetime.now(timezone.utc)
    minutes = (now - datetime.fromisoformat(order["created_at"])).total_seconds() / 60
    if order["fulfilment"] == "pickup":
        steps, ready = PICKUP_STEPS, PICKUP_MINUTES
        current = 0 if minutes < 2 else (1 if minutes < ready else 2)
    else:
        steps, ready = STEPS, DELIVERY_MINUTES
        current = 0 if minutes < 2 else (1 if minutes < 12 else (2 if minutes < ready else 3))
    return {"status": steps[current], "steps": steps, "step": current, "eta_minutes": max(0, round(ready - minutes))}


def public(order):
    """What tracking may show: no name, phone, address or notes."""
    keep = ("id", "items", "fulfilment", "totals", "created_at", "source")
    return {**{k: order[k] for k in keep}, "payment": {"method": order["payment"]["method"]}, **status(order)}


def create_app():
    app = FastAPI(title="FeastFleet orders")
    orders, ids = {}, itertools.count(2001)
    seeded = datetime.now(timezone.utc) - timedelta(minutes=10)
    for oid, item in (("FF-1001", "margherita"), ("FF-1002", "sushi")):  # existing orders for the order-status flow
        lines = [{"id": item, "name": MENU_BY_ID[item]["name"], "qty": 1, "price": MENU_BY_ID[item]["price"]}]
        orders[oid] = {"id": oid, "items": lines, "fulfilment": "delivery", "contact": None, "source": "web",
                       "payment": {"method": "cod"}, "totals": totals(lines, "delivery"),
                       "created_at": seeded.isoformat()}

    def save(order):
        order["id"] = f"FF-{next(ids)}"
        order["created_at"] = datetime.now(timezone.utc).isoformat()
        orders[order["id"]] = order
        return order

    @app.get("/api/menu")
    def menu():
        return {"currency": CURRENCY, "delivery_fee": DELIVERY_FEE, "free_delivery_from": FREE_DELIVERY_FROM,
                "items": MENU}

    @app.post("/api/orders", status_code=201)
    def place(req: OrderRequest):
        unknown = [i.id for i in req.items if i.id not in MENU_BY_ID]
        if unknown:
            raise HTTPException(422, f"Unknown menu items: {', '.join(unknown)}")
        if not PHONE.match(req.contact.phone) or sum(c.isdigit() for c in req.contact.phone) < 7:
            raise HTTPException(422, "Please enter a valid phone number.")
        if req.fulfilment == "delivery" and not (req.contact.address or "").strip():
            raise HTTPException(422, "A delivery address is required.")
        if req.payment.method == "card":
            if not req.payment.card_last4:
                raise HTTPException(422, "Card details are incomplete.")
            if req.payment.card_last4 == "0002":
                raise HTTPException(402, "Your card was declined. Try another card or pay cash on delivery.")
        lines = [{"id": i.id, "name": MENU_BY_ID[i.id]["name"], "qty": i.qty, "price": MENU_BY_ID[i.id]["price"]}
                 for i in req.items]
        order = save({"items": lines, "fulfilment": req.fulfilment, "contact": req.contact.model_dump(), "source": "web",
                      "payment": req.payment.model_dump(exclude_none=True), "totals": totals(lines, req.fulfilment)})
        return {**public(order), "contact": order["contact"]}  # contact echoed only to the person who placed it

    @app.get("/api/menu/match")
    def match(q: str = Query(min_length=1, max_length=300), typos: bool = False, all: bool = False):
        """The assistant asks which menu item a customer means; 404 when nothing on the menu matches.
        all=true returns {"items": [...]} for every dish named; typos=true accepts close spellings (see match_dishes).
        Each item carries "matched" (the words, to locate the dish in the text) and "qty" (a number written just
        before it, else 1)."""
        hits = match_dishes(q, typos) if all else [h for h in [match_dish(q, typos)] if h]
        if not hits:
            raise HTTPException(404, "Not on the menu.")
        found = [{**item, "matched": words, "qty": qty} for item, words, qty in hits]
        return {"items": found} if all else found[0]

    @app.get("/api/orders/{order_id}")
    def track(order_id: str):
        order = orders.get(order_id.strip().upper())
        if order is None:
            raise HTTPException(404, "Order not found.")
        return public(order)

    # ---- Human handoff: an agent reads and answers a chat the assistant handed off -------------------------
    # Message text is held in memory only while the handoff is open and deleted when the agent closes it
    # (reports/data_minimisation_policy.md). Never logged. No agent login: localhost demo only.
    handoffs = {}

    def open_one(hid):
        h = handoffs.get(hid)
        if h is None:
            raise HTTPException(404, "No such chat.")
        return h

    @app.post("/api/handoffs", status_code=201)
    def open_handoff(req: HandoffRequest):
        h = handoffs.get(req.conversation_id)
        if h is None or h["status"] == "closed":
            if sum(x["status"] == "open" for x in handoffs.values()) >= MAX_OPEN_HANDOFFS:
                raise HTTPException(503, "All agents are busy. Please try again shortly.")
            stamp = datetime.now(timezone.utc).isoformat()
            h = {"id": req.conversation_id, "language": req.language, "status": "open", "opened_at": stamp,
                 "messages": [{**m.model_dump(), "at": stamp} for m in req.transcript]}
            handoffs[req.conversation_id] = h
        return {"id": h["id"], "status": h["status"]}

    @app.get("/api/handoffs")
    def inbox():
        """Open chats for the agent inbox, oldest first, without message bodies."""
        rows = [{"id": h["id"], "language": h["language"], "opened_at": h["opened_at"], "count": len(h["messages"]),
                 "waiting": bool(h["messages"]) and h["messages"][-1]["sender"] != "agent",
                 "last": h["messages"][-1]["text"][:80] if h["messages"] else ""}
                for h in handoffs.values() if h["status"] == "open"]
        return sorted(rows, key=lambda r: r["opened_at"])

    @app.get("/api/handoffs/{hid}/messages")
    def messages(hid: str, after: int = Query(0, ge=0)):
        h = open_one(hid)
        return {"id": hid, "status": h["status"], "language": h["language"], "messages": h["messages"][after:],
                "next": len(h["messages"])}

    @app.post("/api/handoffs/{hid}/messages", status_code=201)
    def post_message(hid: str, msg: AgentMessage):
        h = open_one(hid)
        if h["status"] != "open":
            raise HTTPException(410, "This chat has been closed.")
        if len(h["messages"]) >= MAX_HANDOFF_MESSAGES:
            raise HTTPException(429, "This chat is too long; please start a new one.")
        h["messages"].append({**msg.model_dump(), "at": datetime.now(timezone.utc).isoformat()})
        return {"next": len(h["messages"])}

    @app.post("/api/handoffs/{hid}/close")
    def close(hid: str):
        h = open_one(hid)
        h["status"], h["messages"] = "closed", []  # the conversation text is deleted here
        return {"id": hid, "status": "closed"}

    return app


app = create_app()
