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


def test_tracking_hides_contact():
    c = client()
    oid = c.post("/api/orders", json=ORDER).json()["id"]
    tracked = c.get(f"/api/orders/{oid.lower()}").json()
    assert "contact" not in tracked and tracked["id"] == oid


def test_handoff_conversation_lifecycle():
    c = client()
    cid = "web-test-1234"
    opened = c.post("/api/handoffs", json={"conversation_id": cid, "language": "hi-IN", "transcript": [
        {"sender": "customer", "text": "मुझे पैसे वापस चाहिए"}, {"sender": "bot", "text": "Connecting you"}]})
    assert opened.status_code == 201 and opened.json()["status"] == "open"
    inbox = c.get("/api/handoffs").json()
    assert inbox[0]["id"] == cid and inbox[0]["waiting"] and inbox[0]["language"] == "hi-IN"
    assert c.post(f"/api/handoffs/{cid}/messages", json={"sender": "agent", "text": "Namaste, I can help"}).status_code == 201
    got = c.get(f"/api/handoffs/{cid}/messages", params={"after": 2}).json()
    assert [m["text"] for m in got["messages"]] == ["Namaste, I can help"] and got["next"] == 3
    assert not c.get("/api/handoffs").json()[0]["waiting"]  # last message is the agent's
    assert c.post(f"/api/handoffs/{cid}/close").json()["status"] == "closed"
    closed = c.get(f"/api/handoffs/{cid}/messages").json()
    assert closed["status"] == "closed" and closed["messages"] == []  # text deleted on close
    assert c.post(f"/api/handoffs/{cid}/messages", json={"sender": "customer", "text": "hello?"}).status_code == 410
    assert c.get("/api/handoffs").json() == []


def test_handoff_validation():
    c = client()
    assert c.post("/api/handoffs", json={"conversation_id": "x"}).status_code == 422  # malformed id
    assert c.post("/api/handoffs", json={"conversation_id": "web-ok-1234", "transcript": [{"sender": "admin", "text": "hi"}]}).status_code == 422
    c.post("/api/handoffs", json={"conversation_id": "web-ok-1234"})
    assert c.post("/api/handoffs/web-ok-1234/messages", json={"sender": "agent", "text": "x" * 1001}).status_code == 422
    assert c.get("/api/handoffs/web-none-0000/messages").status_code == 404


def test_menu_match_across_scripts():
    c = client()
    for words, dish in [("a large chicken biryani", "biryani"), ("पिज़्ज़ा", "margherita"), ("தோசை", "dosa"),
                        ("寿司", "sushi"), ("شاورما", "shawarma"), ("chicken pizza please", "tikka-pizza"),
                        ("ፒዛ", "margherita")]:
        assert c.get("/api/menu/match", params={"q": words}).json()["id"] == dish, words
    assert c.get("/api/menu/match", params={"q": "cheeseburger"}).status_code == 404
    assert c.get("/api/menu/match", params={"q": "mujhe biryani chahiye"}).json()["matched"] == "biryani"
    assert c.get("/api/orders/FF-1001").json()["status"] == "preparing"  # seeded order, 10 minutes old
    assert c.get("/api/orders/FF-9999").status_code == 404


def test_menu_match_words_typos_and_several_dishes():
    c = client()
    match = lambda q, **kw: c.get("/api/menu/match", params={"q": q, **kw})
    assert match("what's the price for veg ulao").status_code == 404  # "price" is not "rice"; no typos by default
    assert match("Was kostet der Preis?").status_code == 404  # German "Preis" is not "reis" (rice)
    assert match("what's the price for veg ulao", typos=True).json()["id"] == "veg-pulao"
    assert match("lass mich bestellen", typos=True).status_code == 404  # a cut-off name is another word
    got = match("i want to order butter naan and ppav bhaji", all=True, typos=True).json()["items"]
    assert [i["id"] for i in got] == ["naan", "pav-bhaji"]
    got = match("pizza and chicken pizza", all=True).json()["items"]
    assert [i["id"] for i in got] == ["margherita", "tikka-pizza"]  # the longer name is one dish, not two
    got = match("2 dosa, two butter naan, 3x lassi and a pizza", all=True).json()["items"]
    assert [(i["id"], i["qty"]) for i in got] == [("dosa", 2), ("naan", 2), ("lassi", 3), ("margherita", 1)]
    assert match("मुझे २ बिरयानी चाहिए").json()["qty"] == 2  # Devanagari digit
    assert match("99 dosa").json()["qty"] == 20 and match("biryani for 4 people").json()["qty"] == 1
    # Swahili "wali" (rice) is Hinglish "the one": a dish only in a Swahili conversation
    assert match("mujhe spicy wali chahiye").status_code == 404
    assert match("nataka wali").json()["id"] == "veg-pulao"


# One order per language (AI-written, not reviewed by native speakers): dish variants split around other words,
# plurals, hyphens, and quantities before or after the dish, as numbers or number words.
ORDERS = [
    ("I want 3 large chicken tikka pizzas and 2 mutton biryanis", [("tikka-pizza", 3), ("mutton-biryani", 2)]),
    ("Je veux 3 Large Chicken Tikka Pizza et 2 Mutton Biryani.", [("tikka-pizza", 3), ("mutton-biryani", 2)]),
    ("Je voudrais trois pizzas poulet tikka et deux biryanis à l'agneau", [("tikka-pizza", 3), ("mutton-biryani", 2)]),
    ("Ich möchte 3 große Chicken-Tikka-Pizzen und 2 Lamm-Biryanis", [("tikka-pizza", 3), ("mutton-biryani", 2)]),
    ("Zwei Pizzen und drei Lassi bitte", [("margherita", 2), ("lassi", 3)]),
    ("Quiero 3 pizzas grandes de pollo tikka y 2 biryanis de cordero", [("tikka-pizza", 3), ("mutton-biryani", 2)]),
    ("dos dosas y una lassi", [("dosa", 2), ("lassi", 1)]),
    ("मुझे 3 चिकन पिज़्ज़ा और 2 मटन बिरयानी चाहिए", [("tikka-pizza", 3), ("mutton-biryani", 2)]),
    ("दो डोसा और तीन लस्सी", [("dosa", 2), ("lassi", 3)]),
    ("mujhe 2 mutton biryani aur 3 lassi chahiye", [("mutton-biryani", 2), ("lassi", 3)]),
    ("チキンピザを3枚とビリヤニを2つください", [("tikka-pizza", 3), ("biryani", 2)]),
    ("أريد ٣ بيتزا دجاج و٢ برياني لحم", [("tikka-pizza", 3), ("mutton-biryani", 2)]),
    ("Nataka pizza 3 za kuku tikka na biryani 2 ya mbuzi", [("tikka-pizza", 3), ("mutton-biryani", 2)]),
    ("Nataka pizza tatu na lassi mbili", [("margherita", 3), ("lassi", 2)]),
    ("எனக்கு 3 சிக்கன் பிட்சா மற்றும் 2 மட்டன் பிரியாணி வேண்டும்", [("tikka-pizza", 3), ("mutton-biryani", 2)]),
    ("3 ፒዛ እና 2 ብርያኒ እፈልጋለሁ", [("margherita", 3), ("biryani", 2)]),
    ("a pizza and a chicken pizza", [("margherita", 1), ("tikka-pizza", 1)]),  # two dishes, not one variant
    ("biryani x2", [("biryani", 2)]),
]


def test_orders_in_every_language():
    c = client()
    for text, want in ORDERS:
        got = c.get("/api/menu/match", params={"q": text, "all": True, "typos": True}).json().get("items", [])
        assert [(i["id"], i["qty"]) for i in got] == want, text


def test_status_timeline():
    now = datetime.now(timezone.utc)
    order = {"fulfilment": "delivery", "created_at": (now - timedelta(minutes=20)).isoformat()}
    s = status(order, now)
    assert s["status"] == "on_the_way" and s["eta_minutes"] == 10
    assert status({**order, "created_at": (now - timedelta(minutes=45)).isoformat()}, now)["status"] == "delivered"
    assert status({"fulfilment": "pickup", "created_at": now.isoformat()}, now)["steps"][-1] == "ready"
