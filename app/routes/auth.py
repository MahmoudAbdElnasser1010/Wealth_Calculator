from flask import Blueprint, jsonify
from flask_jwt_extended import create_access_token, jwt_required

from ..errors import APIError
from ..extensions import db
from ..models import User
from ..validation import get_json_body, parse_currency, require_fields
from . import current_user

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.post("/register")
def register():
    data = get_json_body()
    require_fields(data, "username", "password")
    username = str(data["username"]).strip()
    password = str(data["password"])
    if not 3 <= len(username) <= 80:
        raise APIError("'username' must be between 3 and 80 characters")
    if len(password) < 6:
        raise APIError("'password' must be at least 6 characters")
    if User.query.filter_by(username=username).first():
        raise APIError("Username is already taken", 409)

    user = User(username=username, base_currency=parse_currency(data.get("base_currency", "USD"), "base_currency"))
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    token = create_access_token(identity=str(user.id))
    return jsonify({"user": user.to_dict(), "access_token": token}), 201


@bp.post("/login")
def login():
    data = get_json_body()
    require_fields(data, "username", "password")
    user = User.query.filter_by(username=str(data["username"]).strip()).first()
    if user is None or not user.check_password(str(data["password"])):
        raise APIError("Invalid username or password", 401)
    return jsonify({"user": user.to_dict(), "access_token": create_access_token(identity=str(user.id))})


@bp.get("/me")
@jwt_required()
def me():
    return jsonify(current_user().to_dict())


@bp.patch("/me")
@jwt_required()
def update_me():
    """Change the default currency used for wealth reports."""
    user = current_user()
    data = get_json_body()
    if "base_currency" in data:
        user.base_currency = parse_currency(data["base_currency"], "base_currency")
    db.session.commit()
    return jsonify(user.to_dict())
