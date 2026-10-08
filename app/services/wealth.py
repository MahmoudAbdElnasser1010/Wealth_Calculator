from decimal import ROUND_HALF_UP, Decimal

from ..models import Asset, CashHolding, GoldHolding

CENT = Decimal("0.01")


def money(value):
    return float(Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP))


def calculate_wealth(user, currency, exchange_rates, gold_prices):
    """Value everything the user owns in `currency` and return a full breakdown."""
    cash_items, cash_total = [], Decimal(0)
    for c in CashHolding.query.filter_by(user_id=user.id).order_by(CashHolding.id):
        converted = exchange_rates.convert(c.amount, c.currency, currency)
        cash_total += converted
        cash_items.append({**c.to_dict(), "converted_value": money(converted)})

    gold_items, gold_total, gold_grams = [], Decimal(0), Decimal(0)
    holdings = GoldHolding.query.filter_by(user_id=user.id).order_by(GoldHolding.id).all()
    prices = gold_prices.prices_per_gram(currency) if holdings else {}
    for g in holdings:
        price = prices[g.karat]
        value = price * g.weight_grams
        gold_total += value
        gold_grams += g.weight_grams
        gold_items.append({**g.to_dict(), "price_per_gram": money(price), "converted_value": money(value)})

    asset_items, asset_total = [], Decimal(0)
    for a in Asset.query.filter_by(user_id=user.id).order_by(Asset.id):
        converted = exchange_rates.convert(a.value, a.currency, currency)
        asset_total += converted
        asset_items.append({**a.to_dict(), "converted_value": money(converted)})

    total = cash_total + gold_total + asset_total
    return {
        "currency": currency,
        "total_wealth": money(total),
        "summary": {
            "cash": money(cash_total),
            "gold": money(gold_total),
            "assets": money(asset_total),
        },
        "breakdown": {
            "cash": cash_items,
            "gold": {"total_weight_grams": float(gold_grams), "items": gold_items},
            "assets": asset_items,
        },
    }
