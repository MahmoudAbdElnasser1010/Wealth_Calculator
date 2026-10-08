from decimal import Decimal

import requests

from ..errors import APIError, PriceUnavailableError
from .cache import TTLCache


class ExchangeRateService:
    """Currency conversion backed by the free open.er-api.com feed (no API key needed).

    https://www.exchangerate-api.com/docs/free
    """

    URL = "https://open.er-api.com/v6/latest/USD"

    def __init__(self, cache_ttl=600, timeout=10, session=None):
        self.cache = TTLCache(cache_ttl)
        self.timeout = timeout
        self.session = session or requests.Session()

    def get_usd_rates(self):
        """Return a dict of currency code -> units of that currency per 1 USD."""
        rates = self.cache.get("USD")
        if rates is not None:
            return rates
        try:
            resp = self.session.get(self.URL, timeout=self.timeout)
            resp.raise_for_status()
            payload = resp.json()
        except (requests.RequestException, ValueError) as exc:
            raise PriceUnavailableError(f"Exchange rates are unavailable: {exc}") from exc
        if payload.get("result") != "success" or "rates" not in payload:
            raise PriceUnavailableError("Exchange rate provider returned an unexpected response")
        rates = {code: Decimal(str(rate)) for code, rate in payload["rates"].items()}
        self.cache.set("USD", rates)
        return rates

    def supported_currencies(self):
        return sorted(self.get_usd_rates())

    def rate(self, from_currency, to_currency):
        """Units of `to_currency` per 1 unit of `from_currency`."""
        from_currency, to_currency = from_currency.upper(), to_currency.upper()
        if from_currency == to_currency:
            return Decimal(1)
        rates = self.get_usd_rates()
        for code in (from_currency, to_currency):
            if code not in rates:
                raise APIError(f"Unsupported currency: {code}", 400)
        return rates[to_currency] / rates[from_currency]

    def convert(self, amount, from_currency, to_currency):
        return Decimal(amount) * self.rate(from_currency, to_currency)
