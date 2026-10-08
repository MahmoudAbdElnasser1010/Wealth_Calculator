from flask import jsonify
from werkzeug.exceptions import HTTPException


class APIError(Exception):
    """An error that is returned to the client as JSON."""

    def __init__(self, message, status_code=400, details=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details


class PriceUnavailableError(APIError):
    """Raised when an external price provider cannot be reached or returns bad data."""

    def __init__(self, message):
        super().__init__(message, status_code=503)


def register_error_handlers(app):
    @app.errorhandler(APIError)
    def handle_api_error(err):
        body = {"error": err.message}
        if err.details:
            body["details"] = err.details
        return jsonify(body), err.status_code

    @app.errorhandler(HTTPException)
    def handle_http_error(err):
        return jsonify({"error": err.description}), err.code
