from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from ..extensions import db
from ..models import CashHolding
from ..validation import (
    get_json_body,
    parse_currency,
    parse_optional_str,
    parse_positive_decimal,
    require_fields,
)
from . import current_user, get_owned_or_404

bp = Blueprint("cash", __name__, url_prefix="/api/cash")


@bp.get("")
@jwt_required()
def list_cash():
    user = current_user()
    items = CashHolding.query.filter_by(user_id=user.id).order_by(CashHolding.id).all()
    return jsonify([c.to_dict() for c in items])


@bp.post("")
@jwt_required()
def add_cash():
    user = current_user()
    data = get_json_body()
    require_fields(data, "amount", "currency")
    item = CashHolding(
        user_id=user.id,
        amount=parse_positive_decimal(data["amount"], "amount"),
        currency=parse_currency(data["currency"]),
        label=parse_optional_str(data.get("label"), "label", 120),
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


@bp.get("/<int:item_id>")
@jwt_required()
def get_cash(item_id):
    return jsonify(get_owned_or_404(CashHolding, item_id, current_user()).to_dict())


@bp.put("/<int:item_id>")
@jwt_required()
def update_cash(item_id):
    item = get_owned_or_404(CashHolding, item_id, current_user())
    data = get_json_body()
    if "amount" in data:
        item.amount = parse_positive_decimal(data["amount"], "amount")
    if "currency" in data:
        item.currency = parse_currency(data["currency"])
    if "label" in data:
        item.label = parse_optional_str(data["label"], "label", 120)
    db.session.commit()
    return jsonify(item.to_dict())


@bp.delete("/<int:item_id>")
@jwt_required()
def delete_cash(item_id):
    item = get_owned_or_404(CashHolding, item_id, current_user())
    db.session.delete(item)
    db.session.commit()
    return "", 204
