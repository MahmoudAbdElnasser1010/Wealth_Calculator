from flask import Flask, jsonify

from .config import Config
from .errors import register_error_handlers
from .extensions import db, jwt
from .services.exchange_rates import ExchangeRateService
from .services.gold_prices import GoldPriceService


def create_app(config_class=Config, exchange_rates=None, gold_prices=None):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    jwt.init_app(app)
    register_error_handlers(app)
    _register_jwt_errors()

    ttl, timeout = app.config["PRICE_CACHE_TTL"], app.config["HTTP_TIMEOUT"]
    exchange_rates = exchange_rates or ExchangeRateService(cache_ttl=ttl, timeout=timeout)
    app.extensions["exchange_rates"] = exchange_rates
    app.extensions["gold_prices"] = gold_prices or GoldPriceService(
        exchange_rates, api_key=app.config["GOLDAPI_KEY"], cache_ttl=ttl, timeout=timeout
    )

    from .routes import assets, auth, cash, gold, wealth

    for module in (auth, cash, gold, assets, wealth):
        app.register_blueprint(module.bp)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    with app.app_context():
        db.create_all()

    return app


def _register_jwt_errors():
    def unauthorized(reason):
        return jsonify({"error": f"Authentication required: {reason}"}), 401

    jwt.unauthorized_loader(unauthorized)
    jwt.invalid_token_loader(unauthorized)
    jwt.expired_token_loader(lambda _h, _p: unauthorized("token has expired"))
