# Wealth Calculator API

A Flask REST API for personal money management. Each user records the **cash**, **gold** and **assets** they own and gets their **total wealth** in any currency.

- **Cash**: an amount in any currency (USD, EGP, EUR, SAR and so on).
- **Gold**: a weight in grams plus a karat (24K, 22K, 21K, 18K and so on). It is valued at the live gold price for that karat.
- **Assets**: things like a car or a home, each with a name, category, value and currency.
- **Total wealth**: everything above converted to one currency and added up, with a full breakdown.

## Pricing sources

| What | Provider | Key needed |
|------|----------|------------|
| Gold price (default) | [gold-api.com](https://gold-api.com): the USD spot price per troy ounce. The price per gram for each karat is `spot / 31.1035 × karat / 24`, then converted to the requested currency. | No |
| Gold price (optional) | [GoldAPI.io](https://www.goldapi.io): per-gram prices for 24K/22K/21K/20K/18K/16K/14K/10K, quoted directly in the requested currency. It is used automatically when `GOLDAPI_KEY` is set. | Yes (free tier) |
| Exchange rates | [open.er-api.com](https://www.exchangerate-api.com/docs/free) | No |

Prices are cached in memory for `PRICE_CACHE_TTL` seconds (default 600). If a provider is unreachable, price-dependent endpoints return `503`.

Supported karats: 24, 22, 21, 20, 18, 16, 14, 12, 10, 9, 8.

## Getting started

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env        # optional: set secrets / GOLDAPI_KEY, then export them
python run.py               # http://localhost:5000
pytest                      # run the test suite (external APIs are stubbed)
```

The settings below are read from environment variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `SECRET_KEY` / `JWT_SECRET_KEY` | dev values | **Change these in production** |
| `DATABASE_URL` | `sqlite:///wealth.db` | Any SQLAlchemy URL |
| `GOLDAPI_KEY` | none | Switches gold pricing to GoldAPI.io |
| `PRICE_CACHE_TTL` | `600` | How long prices and rates are cached, in seconds |
| `JWT_EXPIRES_HOURS` | `24` | Access token lifetime |

## API

Every endpoint except register, login, health, gold prices, currencies and asset categories needs the header `Authorization: Bearer <access_token>`.

### Auth
| Method | Path | Body |
|--------|------|------|
| POST | `/api/auth/register` | `{"username", "password", "base_currency"?}` returns the user and `access_token` |
| POST | `/api/auth/login` | `{"username", "password"}` returns the user and `access_token` |
| GET | `/api/auth/me` | none |
| PATCH | `/api/auth/me` | `{"base_currency": "EGP"}`, the default currency for reports |

### Cash: `/api/cash`
`GET` (list), `POST` `{"amount": 1500, "currency": "EGP", "label"?: "Bank"}`, `GET/PUT/DELETE /api/cash/<id>`

### Gold: `/api/gold`
`GET` (list), `POST` `{"weight_grams": 10, "karat": 21, "description"?: "Ring"}` (karat may also be `"21K"`), `PUT/DELETE /api/gold/<id>`

- `GET /api/gold/<id>?currency=EGP` returns the holding with `price_per_gram` and `current_value`.
- `GET /api/gold/prices?currency=EGP` returns the live price per gram for every karat.

### Assets: `/api/assets`
`GET` (list, optional `?category=car`), `POST` `{"name": "Toyota Corolla", "category": "car", "value": 900000, "currency": "EGP", "description"?}`, `GET/PUT/DELETE /api/assets/<id>`

Categories (`GET /api/assets/categories`): `car, home, land, business, electronics, jewelry, other`.

### Total wealth
`GET /api/wealth?currency=EGP` (defaults to the user's `base_currency`):

```json
{
  "currency": "USD",
  "total_wealth": 113600.0,
  "summary": {"cash": 1100.0, "gold": 2500.0, "assets": 110000.0},
  "breakdown": {
    "cash":   [{"id": 1, "amount": 5000.0, "currency": "EGP", "converted_value": 100.0, "...": "..."}],
    "gold":   {"total_weight_grams": 30.0,
               "items": [{"id": 1, "weight_grams": 10.0, "karat": 24, "price_per_gram": 100.0, "converted_value": 1000.0}]},
    "assets": [{"id": 1, "name": "Car", "category": "car", "value": 500000.0, "currency": "EGP", "converted_value": 10000.0}]
  }
}
```

### Misc
- `GET /api/currencies` lists the supported currency codes.
- `GET /api/health` is a health check.

## Example

```bash
TOKEN=$(curl -s -X POST localhost:5000/api/auth/register -H 'Content-Type: application/json' \
  -d '{"username":"mahmoud","password":"secret123","base_currency":"EGP"}' | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
H="Authorization: Bearer $TOKEN"

curl -s -X POST localhost:5000/api/cash   -H "$H" -H 'Content-Type: application/json' -d '{"amount":50000,"currency":"EGP"}'
curl -s -X POST localhost:5000/api/cash   -H "$H" -H 'Content-Type: application/json' -d '{"amount":1000,"currency":"USD"}'
curl -s -X POST localhost:5000/api/gold   -H "$H" -H 'Content-Type: application/json' -d '{"weight_grams":25,"karat":21}'
curl -s -X POST localhost:5000/api/assets -H "$H" -H 'Content-Type: application/json' -d '{"name":"Car","category":"car","value":900000,"currency":"EGP"}'
curl -s localhost:5000/api/wealth -H "$H"
```

## Project layout

```
app/
  __init__.py          app factory
  config.py            settings from the environment
  models.py            User, CashHolding, GoldHolding, Asset
  validation.py        request parsing helpers
  errors.py            JSON error handling
  services/
    gold_prices.py     gold price per gram for each karat (gold-api.com / GoldAPI.io)
    exchange_rates.py  currency conversion (open.er-api.com)
    wealth.py          total wealth calculation
  routes/              auth, cash, gold, assets, wealth blueprints
tests/                 pytest suite with stubbed price providers
run.py                 entry point
```
