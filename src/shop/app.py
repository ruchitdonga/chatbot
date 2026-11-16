"""FeastFleet orders API (FeastFleet is a fictional brand). Shared by the website checkout and the chat assistant.

GET  /api/menu                 menu with prices (integer cents, EUR)
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

CURRENCY = "EUR"
DELIVERY_FEE, FREE_DELIVERY_FROM = 249, 3000
DELIVERY_MINUTES, PICKUP_MINUTES = 30, 15
MENU = [
    {"id": "margherita", "name": "Margherita pizza", "desc": "Tomato, mozzarella, basil", "price": 1150, "category": "Pizza", "emoji": "🍕"},
    {"id": "pepperoni", "name": "Pepperoni pizza", "desc": "Spicy salami, mozzarella", "price": 1300, "category": "Pizza", "emoji": "🍕"},
    {"id": "biryani", "name": "Chicken biryani", "desc": "Basmati rice, saffron, raita", "price": 1300, "category": "Indian", "emoji": "🍛"},
    {"id": "paneer", "name": "Paneer butter masala", "desc": "Tomato cream sauce, naan", "price": 1200, "category": "Indian", "emoji": "🍲"},
    {"id": "dosa", "name": "Masala dosa", "desc": "Rice crêpe, potato, sambar", "price": 950, "category": "Indian", "emoji": "🥞"},
    {"id": "sushi", "name": "Salmon sushi", "desc": "12 pieces, pickled ginger", "price": 1690, "category": "Japanese", "emoji": "🍣"},
    {"id": "ramen", "name": "Tonkotsu ramen", "desc": "Pork broth, egg, spring onion", "price": 1420, "category": "Japanese", "emoji": "🍜"},
    {"id": "shawarma", "name": "Chicken shawarma", "desc": "Garlic sauce, pickles, fries", "price": 980, "category": "Middle Eastern", "emoji": "🌯"},
    {"id": "falafel", "name": "Falafel wrap", "desc": "Tahini, salad, pickled turnip", "price": 890, "category": "Middle Eastern", "emoji": "🧆"},
    {"id": "doner", "name": "Döner kebab", "desc": "Flatbread, salad, yoghurt sauce", "price": 850, "category": "Turkish", "emoji": "🥙"},
    {"id": "doro-wat", "name": "Doro wat", "desc": "Spiced chicken stew, injera", "price": 1350, "category": "East African", "emoji": "🍗"},
    {"id": "chips-mayai", "name": "Chips mayai", "desc": "Chips omelette, kachumbari", "price": 700, "category": "East African", "emoji": "🍳"},
    {"id": "tiramisu", "name": "Tiramisu", "desc": "Mascarpone, espresso, cocoa", "price": 600, "category": "Desserts & drinks", "emoji": "🍰"},
    {"id": "lassi", "name": "Mango lassi", "desc": "Yoghurt, mango, cardamom", "price": 400, "category": "Desserts & drinks", "emoji": "🥭"},
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
