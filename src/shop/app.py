"""FeastFleet orders API (FeastFleet is a fictional brand). Shared by the website checkout and the chat assistant.

GET  /api/menu                 menu with prices (integer paise, INR) and veg/non-veg flags
POST /api/orders               checkout: cart items, delivery or pickup, contact, payment (card or cash on delivery)
POST /api/chat-orders          an order placed in chat: free-text food, cash on delivery
GET  /api/orders/{id}          status timeline for tracking (no contact details)

Payments are simulated: the browser sends only the card brand and last four digits, never the card number, expiry or
CVC; a card ending 0002 is declined (test card). Orders live in memory only and are never logged.
Run: uvicorn src.shop.app:app --port 8001
"""
import itertools
import re
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

CURRENCY = "INR"  # amounts in paise
DELIVERY_FEE, FREE_DELIVERY_FROM = 4000, 49900
DELIVERY_MINUTES, PICKUP_MINUTES = 30, 15


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


class OrderRequest(BaseModel):
    items: list[Item] = Field(min_length=1, max_length=30)
    fulfilment: Literal["delivery", "pickup"]
    contact: Contact
    payment: Payment


class ChatOrderRequest(BaseModel):
    food: str = Field(min_length=1, max_length=100)


def totals(lines, fulfilment):
    if any(line["price"] is None for line in lines):  # chat orders are priced by the kitchen, so no total yet
        return {"subtotal": None, "delivery_fee": None, "total": None, "currency": CURRENCY}
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

    @app.post("/api/chat-orders", status_code=201)
    def chat_order(req: ChatOrderRequest):
        lines = [{"id": None, "name": req.food.strip(), "qty": 1, "price": None}]  # priced by the kitchen later
        return public(save({"items": lines, "fulfilment": "delivery", "contact": None, "source": "chat",
                            "payment": {"method": "cod"}, "totals": totals(lines, "delivery")}))

    @app.get("/api/orders/{order_id}")
    def track(order_id: str):
        order = orders.get(order_id.strip().upper())
        if order is None:
            raise HTTPException(404, "Order not found.")
        return public(order)

    return app


app = create_app()
