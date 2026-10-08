from decimal import Decimal

import requests

from ..errors import PriceUnavailableError
from .cache import TTLCache

GRAMS_PER_TROY_OUNCE = Decimal("31.1034768")
SUPPORTED_KARATS = (24, 22, 21, 20, 18, 16, 14, 12, 10, 9, 8)


def karat_purity(karat):
    """Fraction of pure gold in an alloy of the given karat (24K = 100%)."""
    return Decimal(karat) / Decimal(24)


class GoldPriceService:
    """Live gold price per gram for any karat, in any currency.

    Two providers are supported:

    * GoldAPI.io (https://www.goldapi.io) when a ``GOLDAPI_KEY`` is configured.
      It returns per-gram prices for 24K/22K/21K/20K/18K/16K/14K/10K directly in the
      requested currency.
    * gold-api.com (https://gold-api.com, free, no key) otherwise. It returns the
      USD spot price per troy ounce of pure gold; per-karat gram prices are derived
      from purity (karat / 24) and converted with the exchange rate service.
    """

    GOLDAPI_URL = "https://www.goldapi.io/api/XAU/{currency}"
    FREE_URL = "https://api.gold-api.com/price/XAU"

    def __init__(self, exchange_rates, api_key=None, cache_ttl=600, timeout=10, session=None):
        self.exchange_rates = exchange_rates
        self.api_key = api_key
        self.cache = TTLCache(cache_ttl)
        self.timeout = timeout
        self.session = session or requests.Session()

    # -- public API ---------------------------------------------------------

    def price_per_gram(self, karat, currency="USD"):
        return self.prices_per_gram(currency)[karat]

    def prices_per_gram(self, currency="USD"):
        """Return {karat: price per gram} for every supported karat in `currency`."""
        currency = currency.upper()
        cached = self.cache.get(currency)
        if cached is not None:
            return cached

        if self.api_key:
            prices = self._from_goldapi(currency)
        else:
            usd_24k = self._free_spot_usd_per_gram()
            rate = self.exchange_rates.rate("USD", currency)
            prices = {k: usd_24k * rate * karat_purity(k) for k in SUPPORTED_KARATS}

        self.cache.set(currency, prices)
        return prices

    def source(self):
        return "goldapi.io" if self.api_key else "gold-api.com"

    # -- providers ----------------------------------------------------------

    def _get_json(self, url, headers=None):
        try:
            resp = self.session.get(url, headers=headers, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as exc:
            raise PriceUnavailableError(f"Gold price is unavailable: {exc}") from exc

    def _free_spot_usd_per_gram(self):
        payload = self._get_json(self.FREE_URL)
        try:
            usd_per_ounce = Decimal(str(payload["price"]))
        except (KeyError, TypeError, ArithmeticError) as exc:
            raise PriceUnavailableError("Gold price provider returned an unexpected response") from exc
        return usd_per_ounce / GRAMS_PER_TROY_OUNCE

    def _from_goldapi(self, currency):
        payload = self._get_json(
            self.GOLDAPI_URL.format(currency=currency),
            headers={"x-access-token": self.api_key, "Content-Type": "application/json"},
        )
        try:
            base_24k = Decimal(str(payload["price_gram_24k"]))
        except (KeyError, TypeError, ArithmeticError) as exc:
            raise PriceUnavailableError("Gold price provider returned an unexpected response") from exc

        prices = {}
        for k in SUPPORTED_KARATS:
            quoted = payload.get(f"price_gram_{k}k")
            # Use GoldAPI's own quote where it has one, otherwise derive from 24K purity.
            prices[k] = Decimal(str(quoted)) if quoted is not None else base_24k * karat_purity(k)
        return prices
