from flask import current_app
from flask_jwt_extended import get_jwt_identity

from ..errors import APIError
from ..extensions import db
from ..models import User


def current_user():
    user = db.session.get(User, int(get_jwt_identity()))
    if user is None:
        raise APIError("User not found", 401)
    return user


def get_owned_or_404(model, item_id, user):
    item = db.session.get(model, item_id)
    if item is None or item.user_id != user.id:
        raise APIError(f"{model.__name__} not found", 404)
    return item


def exchange_rates():
    return current_app.extensions["exchange_rates"]


def gold_prices():
    return current_app.extensions["gold_prices"]
