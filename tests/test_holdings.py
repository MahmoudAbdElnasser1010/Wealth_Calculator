from .conftest import register


def test_cash_crud(client, auth):
    resp = client.post("/api/cash", headers=auth, json={"amount": 1500.5, "currency": "egp", "label": "Wallet"})
    assert resp.status_code == 201
    item = resp.get_json()
    assert item["currency"] == "EGP" and item["amount"] == 1500.5

    resp = client.put(f"/api/cash/{item['id']}", headers=auth, json={"amount": "2000"})
    assert resp.get_json()["amount"] == 2000.0
    assert len(client.get("/api/cash", headers=auth).get_json()) == 1

    assert client.delete(f"/api/cash/{item['id']}", headers=auth).status_code == 204
    assert client.get(f"/api/cash/{item['id']}", headers=auth).status_code == 404


def test_cash_validation(client, auth):
    assert client.post("/api/cash", headers=auth, json={"amount": -5, "currency": "USD"}).status_code == 400
    assert client.post("/api/cash", headers=auth, json={"amount": "abc", "currency": "USD"}).status_code == 400
    assert client.post("/api/cash", headers=auth, json={"amount": 5, "currency": "dollars"}).status_code == 400
    resp = client.post("/api/cash", headers=auth, json={})
    assert resp.status_code == 400 and set(resp.get_json()["details"]["missing"]) == {"amount", "currency"}


def test_gold_crud_and_karat_parsing(client, auth):
    resp = client.post("/api/gold", headers=auth, json={"weight_grams": 10, "karat": "21K", "description": "Ring"})
    assert resp.status_code == 201
    gold_id = resp.get_json()["id"]
    assert resp.get_json()["karat"] == 21

    assert client.post("/api/gold", headers=auth, json={"weight_grams": 10, "karat": 23}).status_code == 400

    detail = client.get(f"/api/gold/{gold_id}?currency=USD", headers=auth).get_json()
    assert detail["price_per_gram"] == 87.5  # 100 USD * 21/24
    assert detail["current_value"] == 875.0

    resp = client.put(f"/api/gold/{gold_id}", headers=auth, json={"karat": 18})
    assert resp.get_json()["karat"] == 18
    assert client.delete(f"/api/gold/{gold_id}", headers=auth).status_code == 204


def test_asset_crud_and_filter(client, auth):
    car = client.post("/api/assets", headers=auth, json={
        "name": "Toyota Corolla", "category": "car", "value": 900000, "currency": "EGP",
    }).get_json()
    client.post("/api/assets", headers=auth, json={
        "name": "Apartment", "category": "home", "value": 120000, "currency": "USD",
    })
    assert client.post("/api/assets", headers=auth, json={
        "name": "Boat", "category": "spaceship", "value": 1, "currency": "USD",
    }).status_code == 400

    cars = client.get("/api/assets?category=car", headers=auth).get_json()
    assert [a["name"] for a in cars] == ["Toyota Corolla"]

    resp = client.put(f"/api/assets/{car['id']}", headers=auth, json={"value": 850000})
    assert resp.get_json()["value"] == 850000.0


def test_users_cannot_see_each_others_items(client, auth):
    item = client.post("/api/cash", headers=auth, json={"amount": 10, "currency": "USD"}).get_json()
    other = register(client, "mallory")
    assert client.get(f"/api/cash/{item['id']}", headers=other).status_code == 404
    assert client.delete(f"/api/cash/{item['id']}", headers=other).status_code == 404
    assert client.get("/api/cash", headers=other).get_json() == []
