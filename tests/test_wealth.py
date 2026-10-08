from decimal import Decimal

from app.services.exchange_rates import ExchangeRateService
from app.services.gold_prices import GoldPriceService


def _seed(client, auth):
    client.post("/api/cash", headers=auth, json={"amount": 1000, "currency": "USD"})
    client.post("/api/cash", headers=auth, json={"amount": 5000, "currency": "EGP"})        # 100 USD
    client.post("/api/gold", headers=auth, json={"weight_grams": 10, "karat": 24})           # 1000 USD
    client.post("/api/gold", headers=auth, json={"weight_grams": 20, "karat": 18})           # 1500 USD
    client.post("/api/assets", headers=auth, json={
        "name": "Car", "category": "car", "value": 500000, "currency": "EGP"})              # 10000 USD
    client.post("/api/assets", headers=auth, json={
        "name": "Home", "category": "home", "value": 90000, "currency": "EUR"})             # 100000 USD


def test_total_wealth_in_usd(client, auth):
    _seed(client, auth)
    data = client.get("/api/wealth", headers=auth).get_json()
    assert data["currency"] == "USD"
    assert data["summary"] == {"cash": 1100.0, "gold": 2500.0, "assets": 110000.0}
    assert data["total_wealth"] == 113600.0
    assert data["breakdown"]["gold"]["total_weight_grams"] == 30.0
    assert [g["price_per_gram"] for g in data["breakdown"]["gold"]["items"]] == [100.0, 75.0]


def test_total_wealth_in_other_currency(client, auth):
    _seed(client, auth)
    data = client.get("/api/wealth?currency=EGP", headers=auth).get_json()
    assert data["total_wealth"] == 113600.0 * 50
    assert data["summary"]["gold"] == 2500.0 * 50


def test_empty_wealth(client, auth):
    data = client.get("/api/wealth", headers=auth).get_json()
    assert data["total_wealth"] == 0.0


def test_unsupported_currency(client, auth):
    client.post("/api/cash", headers=auth, json={"amount": 1, "currency": "XYZ"})
    resp = client.get("/api/wealth", headers=auth)
    assert resp.status_code == 400
    assert "XYZ" in resp.get_json()["error"]


def test_gold_prices_endpoint(client):
    data = client.get("/api/gold/prices?currency=EGP").get_json()
    assert data["prices"]["24K"] == 5000.0
    assert data["prices"]["21K"] == 4375.0
    assert data["prices"]["18K"] == 3750.0
    assert data["source"] == "gold-api.com"


def test_provider_outage_returns_503(client, auth, session):
    session.routes.clear()
    client.post("/api/gold", headers=auth, json={"weight_grams": 1, "karat": 24})
    resp = client.get("/api/wealth", headers=auth)
    assert resp.status_code == 503


def test_prices_are_cached(client, session):
    client.get("/api/gold/prices")
    client.get("/api/gold/prices")
    gold_calls = [url for url, _ in session.calls if url == GoldPriceService.FREE_URL]
    assert len(gold_calls) == 1


def test_goldapi_provider_uses_quoted_karat_prices(session):
    url = GoldPriceService.GOLDAPI_URL.format(currency="EGP")
    session.routes[url] = {"price_gram_24k": 5000, "price_gram_21k": 4400, "price_gram_18k": 3760}
    service = GoldPriceService(ExchangeRateService(session=session), api_key="key", session=session)
    prices = service.prices_per_gram("EGP")
    assert prices[21] == 4400 and prices[18] == 3760
    assert round(prices[22], 2) == Decimal("4583.33")  # not quoted -> derived from purity
    assert session.calls[-1][1]["x-access-token"] == "key"
