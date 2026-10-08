import pytest
import requests

from app import create_app
from app.config import TestConfig
from app.extensions import db
from app.services.exchange_rates import ExchangeRateService
from app.services.gold_prices import GRAMS_PER_TROY_OUNCE, GoldPriceService

# 1 USD = 50 EGP, 0.9 EUR. Gold spot = 2000 USD / troy ounce.
USD_RATES = {"USD": 1, "EGP": 50, "EUR": 0.9}
GOLD_USD_PER_OUNCE = float(GRAMS_PER_TROY_OUNCE) * 100  # => exactly 100 USD per gram of 24K


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload, self.status_code = payload, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self.payload


class FakeSession:
    """Stands in for requests.Session; routes URLs to canned payloads."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def get(self, url, headers=None, timeout=None):
        self.calls.append((url, headers))
        if url not in self.routes:
            raise requests.ConnectionError(f"no route for {url}")
        return FakeResponse(self.routes[url])


@pytest.fixture
def session():
    return FakeSession({
        ExchangeRateService.URL: {"result": "success", "base_code": "USD", "rates": USD_RATES},
        GoldPriceService.FREE_URL: {"name": "Gold", "price": GOLD_USD_PER_OUNCE, "symbol": "XAU"},
    })


@pytest.fixture
def app(session):
    fx = ExchangeRateService(session=session)
    gold = GoldPriceService(fx, session=session)
    app = create_app(TestConfig, exchange_rates=fx, gold_prices=gold)
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def register(client, username="alice", password="secret123", base_currency="USD"):
    resp = client.post("/api/auth/register", json={
        "username": username, "password": password, "base_currency": base_currency,
    })
    assert resp.status_code == 201, resp.get_json()
    return {"Authorization": f"Bearer {resp.get_json()['access_token']}"}


@pytest.fixture
def auth(client):
    return register(client)
