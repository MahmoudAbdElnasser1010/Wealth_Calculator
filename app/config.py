import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret-key-change-me-in-prod")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.environ.get("JWT_EXPIRES_HOURS", "24")))
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///wealth.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # External pricing
    GOLDAPI_KEY = os.environ.get("GOLDAPI_KEY") or None
    PRICE_CACHE_TTL = int(os.environ.get("PRICE_CACHE_TTL", "600"))
    HTTP_TIMEOUT = float(os.environ.get("HTTP_TIMEOUT", "10"))


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_SECRET_KEY = "test-jwt-secret-key-with-enough-length"
