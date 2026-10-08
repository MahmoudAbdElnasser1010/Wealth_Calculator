from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from ..errors import APIError
from ..extensions import db
from ..models import ASSET_CATEGORIES, Asset
from ..validation import (
    get_json_body,
    parse_choice,
    parse_currency,
    parse_optional_str,
    parse_positive_decimal,
    require_fields,
)
from . import current_user, get_owned_or_404

bp = Blueprint("assets", __name__, url_prefix="/api/assets")


def _parse_name(value):
    name = parse_optional_str(value, "name", 120)
    if not name:
        raise APIError("'name' must not be empty")
    return name


@bp.get("")
@jwt_required()
def list_assets():
    """List assets, optionally filtered with ?category=car."""
    user = current_user()
    query = Asset.query.filter_by(user_id=user.id)
    if request.args.get("category"):
        query = query.filter_by(category=parse_choice(request.args["category"], "category", ASSET_CATEGORIES))
    return jsonify([a.to_dict() for a in query.order_by(Asset.id).all()])


@bp.get("/categories")
def categories():
    return jsonify(list(ASSET_CATEGORIES))


@bp.post("")
@jwt_required()
def add_asset():
    user = current_user()
    data = get_json_body()
    require_fields(data, "name", "value", "currency")
    item = Asset(
        user_id=user.id,
        name=_parse_name(data["name"]),
        category=parse_choice(data.get("category", "other"), "category", ASSET_CATEGORIES),
        value=parse_positive_decimal(data["value"], "value"),
        currency=parse_currency(data["currency"]),
        description=parse_optional_str(data.get("description"), "description", 255),
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


@bp.get("/<int:item_id>")
@jwt_required()
def get_asset(item_id):
    return jsonify(get_owned_or_404(Asset, item_id, current_user()).to_dict())


@bp.put("/<int:item_id>")
@jwt_required()
def update_asset(item_id):
    item = get_owned_or_404(Asset, item_id, current_user())
    data = get_json_body()
    if "name" in data:
        item.name = _parse_name(data["name"])
    if "category" in data:
        item.category = parse_choice(data["category"], "category", ASSET_CATEGORIES)
    if "value" in data:
        item.value = parse_positive_decimal(data["value"], "value")
    if "currency" in data:
        item.currency = parse_currency(data["currency"])
    if "description" in data:
        item.description = parse_optional_str(data["description"], "description", 255)
    db.session.commit()
    return jsonify(item.to_dict())


@bp.delete("/<int:item_id>")
@jwt_required()
def delete_asset(item_id):
    item = get_owned_or_404(Asset, item_id, current_user())
    db.session.delete(item)
    db.session.commit()
    return "", 204
