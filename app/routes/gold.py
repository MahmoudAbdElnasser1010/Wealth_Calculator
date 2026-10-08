from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from ..extensions import db
from ..models import GoldHolding
from ..services.gold_prices import SUPPORTED_KARATS
from ..services.wealth import money
from ..validation import (
    get_json_body,
    parse_choice,
    parse_currency,
    parse_optional_str,
    parse_positive_decimal,
    require_fields,
)
from . import current_user, get_owned_or_404, gold_prices

bp = Blueprint("gold", __name__, url_prefix="/api/gold")


def _parse_karat(value):
    if isinstance(value, str) and value.strip().upper().endswith("K"):
        value = value.strip()[:-1]
    try:
        value = int(value)
    except (TypeError, ValueError):
        pass
    return parse_choice(value, "karat", SUPPORTED_KARATS)


@bp.get("/prices")
@jwt_required(optional=True)
def prices():
    """Live gold price per gram for every supported karat. ?currency=EGP (default: USD)."""
    currency = parse_currency(request.args.get("currency", "USD"))
    per_gram = gold_prices().prices_per_gram(currency)
    return jsonify({
        "currency": currency,
        "unit": "gram",
        "source": gold_prices().source(),
        "prices": {f"{k}K": money(per_gram[k]) for k in SUPPORTED_KARATS},
    })


@bp.get("")
@jwt_required()
def list_gold():
    user = current_user()
    items = GoldHolding.query.filter_by(user_id=user.id).order_by(GoldHolding.id).all()
    return jsonify([g.to_dict() for g in items])


@bp.post("")
@jwt_required()
def add_gold():
    user = current_user()
    data = get_json_body()
    require_fields(data, "weight_grams", "karat")
    item = GoldHolding(
        user_id=user.id,
        weight_grams=parse_positive_decimal(data["weight_grams"], "weight_grams"),
        karat=_parse_karat(data["karat"]),
        description=parse_optional_str(data.get("description"), "description", 255),
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


@bp.get("/<int:item_id>")
@jwt_required()
def get_gold(item_id):
    """A single gold holding with its current value. ?currency=EGP (default: user's base currency)."""
    user = current_user()
    item = get_owned_or_404(GoldHolding, item_id, user)
    currency = parse_currency(request.args.get("currency", user.base_currency))
    price = gold_prices().price_per_gram(item.karat, currency)
    return jsonify({
        **item.to_dict(),
        "currency": currency,
        "price_per_gram": money(price),
        "current_value": money(price * item.weight_grams),
    })


@bp.put("/<int:item_id>")
@jwt_required()
def update_gold(item_id):
    item = get_owned_or_404(GoldHolding, item_id, current_user())
    data = get_json_body()
    if "weight_grams" in data:
        item.weight_grams = parse_positive_decimal(data["weight_grams"], "weight_grams")
    if "karat" in data:
        item.karat = _parse_karat(data["karat"])
    if "description" in data:
        item.description = parse_optional_str(data["description"], "description", 255)
    db.session.commit()
    return jsonify(item.to_dict())


@bp.delete("/<int:item_id>")
@jwt_required()
def delete_gold(item_id):
    item = get_owned_or_404(GoldHolding, item_id, current_user())
    db.session.delete(item)
    db.session.commit()
    return "", 204
