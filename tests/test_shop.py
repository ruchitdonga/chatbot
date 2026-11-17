"""FeastFleet orders API: totals, payment methods, validation, and that tracking never exposes contact details."""
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from src.shop.app import create_app, status

ORDER = {"items": [{"id": "dosa", "qty": 1}, {"id": "lassi", "qty": 1}], "fulfilment": "delivery",
         "contact": {"name": "Test Customer", "phone": "+91 98765 43210", "address": "1 Test Street", "notes": ""},
         "payment": {"method": "cod"}}


def client():
    return TestClient(create_app())


def test_menu_and_cod_order_totals():
    c = client()
    assert len(c.get("/api/menu").json()["items"]) >= 10
    r = c.post("/api/orders", json=ORDER)
    assert r.status_code == 201
    order = r.json()
    assert order["id"] == "FF-2001" and order["status"] == "confirmed"
    assert order["totals"] == {"subtotal": 20800, "delivery_fee": 4000, "total": 24800, "currency": "INR"}
    assert order["payment"] == {"method": "cod"}


def test_card_payment_free_delivery_and_decline():
    c = client()
    big = {**ORDER, "items": [{"id": "sushi", "qty": 2}], "payment": {"method": "card", "card_brand": "Visa",
                                                                       "card_last4": "4242"}}
    order = c.post("/api/orders", json=big).json()
    assert order["totals"]["delivery_fee"] == 0 and order["payment"] == {"method": "card"}  # no card data echoed
    declined = {**big, "payment": {"method": "card", "card_brand": "Visa", "card_last4": "0002"}}
    assert c.post("/api/orders", json=declined).status_code == 402
    assert c.post("/api/orders", json={**big, "payment": {"method": "card"}}).status_code == 422


def test_validation():
    c = client()
    assert c.post("/api/orders", json={**ORDER, "items": [{"id": "caviar", "qty": 1}]}).status_code == 422
    assert c.post("/api/orders", json={**ORDER, "contact": {**ORDER["contact"], "phone": "abc"}}).status_code == 422
    no_address = {**ORDER, "contact": {**ORDER["contact"], "address": " "}}
    assert c.post("/api/orders", json=no_address).status_code == 422
    assert c.post("/api/orders", json={**no_address, "fulfilment": "pickup"}).status_code == 201  # pickup: no address
    assert c.post("/api/orders", json={**ORDER, "items": [{"id": "lassi", "qty": 99}]}).status_code == 422


def test_tracking_hides_contact_and_accepts_chat_orders():
    c = client()
    oid = c.post("/api/orders", json=ORDER).json()["id"]
    tracked = c.get(f"/api/orders/{oid.lower()}").json()
    assert "contact" not in tracked and tracked["id"] == oid
    chat = c.post("/api/chat-orders", json={"food": "pilau"}).json()
    assert chat["items"][0]["name"] == "pilau" and chat["source"] == "chat"
    assert chat["totals"]["total"] is None  # unpriced until the kitchen confirms; no fee-only "total"
    assert c.get("/api/orders/FF-1001").json()["status"] == "preparing"  # seeded order, 10 minutes old
    assert c.get("/api/orders/FF-9999").status_code == 404


def test_status_timeline():
    now = datetime.now(timezone.utc)
    order = {"fulfilment": "delivery", "created_at": (now - timedelta(minutes=20)).isoformat()}
    s = status(order, now)
    assert s["status"] == "on_the_way" and s["eta_minutes"] == 10
    assert status({**order, "created_at": (now - timedelta(minutes=45)).isoformat()}, now)["status"] == "delivered"
    assert status({"fulfilment": "pickup", "created_at": now.isoformat()}, now)["steps"][-1] == "ready"
