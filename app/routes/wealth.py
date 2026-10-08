from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from ..services.wealth import calculate_wealth
from ..validation import parse_currency
from . import current_user, exchange_rates, gold_prices

bp = Blueprint("wealth", __name__, url_prefix="/api")


@bp.get("/wealth")
@jwt_required()
def wealth():
    """Total wealth (cash + gold + assets) in one currency. ?currency=EGP (default: user's base currency)."""
    user = current_user()
    currency = parse_currency(request.args.get("currency", user.base_currency))
    return jsonify(calculate_wealth(user, currency, exchange_rates(), gold_prices()))


@bp.get("/currencies")
def currencies():
    return jsonify(exchange_rates().supported_currencies())
