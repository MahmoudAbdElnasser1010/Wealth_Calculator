import re
from decimal import Decimal, InvalidOperation

from flask import request

from .errors import APIError

_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


def get_json_body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise APIError("Request body must be a JSON object")
    return data


def require_fields(data, *fields):
    missing = [f for f in fields if data.get(f) in (None, "")]
    if missing:
        raise APIError("Missing required fields", details={"missing": missing})


def parse_positive_decimal(value, field, allow_zero=False):
    if isinstance(value, bool):
        raise APIError(f"'{field}' must be a number")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise APIError(f"'{field}' must be a number")
    if not number.is_finite():
        raise APIError(f"'{field}' must be a finite number")
    if number < 0 or (number == 0 and not allow_zero):
        raise APIError(f"'{field}' must be {'zero or ' if allow_zero else ''}greater than zero")
    return number


def parse_currency(value, field="currency"):
    if not isinstance(value, str) or not _CURRENCY_RE.match(value.strip().upper()):
        raise APIError(f"'{field}' must be a 3-letter ISO 4217 currency code, e.g. USD or EGP")
    return value.strip().upper()


def parse_optional_str(value, field, max_length):
    if value is None:
        return None
    if not isinstance(value, str):
        raise APIError(f"'{field}' must be a string")
    value = value.strip()
    if len(value) > max_length:
        raise APIError(f"'{field}' must be at most {max_length} characters")
    return value or None


def parse_choice(value, field, choices):
    if value not in choices:
        raise APIError(f"'{field}' must be one of: {', '.join(str(c) for c in choices)}")
    return value
