"""Currency conversion service using free ECB/NBP exchange rates.

Provides FX rate caching and price normalization across currencies.
Uses European Central Bank (ECB) and National Bank of Poland (NBP) APIs.

It also reads the NBP reference rate ("stopa referencyjna") from the same
bank, because the tools that price a mortgage must not carry a hardcoded
interest rate.

CE scope: Free ECB/NBP APIs with daily caching.
Pro gets premium real-time FX feeds later.
"""

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ECB provides free daily EUR-based rates
ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
# NBP provides PLN rates (table A)
NBP_URL = "https://api.nbp.pl/api/exchangerates/tables/A?format=json"
# NBP publishes its base rates (reference rate included) as a machine readable
# file. The api.nbp.pl endpoint serves currency mid-rates only - table A has no
# interest rate in it - so the reference rate is read from the bank's own file.
# Source: https://nbp.pl/polityka-pieniezna/decyzje-rpp/podstawowe-stopy-procentowe-nbp/
NBP_REFERENCE_RATE_URL = "https://static.nbp.pl/dane/stopy/stopy_procentowe.xml"

# The last resort when the network is unavailable: the value NBP last
# published, with the date it published it. It is never used silently - an
# answer that falls back to it says so.
NBP_REFERENCE_RATE_FALLBACK = 3.75
NBP_REFERENCE_RATE_FALLBACK_DATE = "2026-03-05"

SUPPORTED_CURRENCIES = {
    "EUR",
    "USD",
    "GBP",
    "PLN",
    "CHF",
    "CZK",
    "UAH",
    "TRY",
    "ARS",
    "BRL",
    "CNY",
    "JPY",
    "KRW",
}

CACHE_DIR = Path("cache/fx_rates")
CACHE_TTL_SECONDS = 86400  # 24 hours


def _fetch_ecb_rates() -> dict[str, float]:
    """Fetch exchange rates from ECB (EUR-based)."""
    rates = {"EUR": 1.0}
    try:
        req = urllib.request.Request(ECB_URL, headers={"User-Agent": "fx-rates/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:  # nosec B310 - hardcoded trusted ECB URL
            content = resp.read().decode()

        # Parse XML manually (avoid xmltodict dependency)
        import re

        for match in re.finditer(r'currency=[\'"](\w+)[\'"].*rate=[\'"]([\d.]+)[\'"]', content):
            currency, rate = match.group(1), float(match.group(2))
            if currency in SUPPORTED_CURRENCIES:
                rates[currency] = rate

        logger.info("ECB rates fetched: %d currencies", len(rates))
    except Exception as e:
        logger.warning("Failed to fetch ECB rates: %s", e)

    return rates


def _fetch_nbp_rates() -> dict[str, float]:
    """Fetch exchange rates from NBP (PLN-based)."""
    rates = {"PLN": 1.0}
    try:
        req = urllib.request.Request(NBP_URL, headers={"User-Agent": "fx-rates/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:  # nosec B310 - hardcoded trusted NBP URL
            data = json.loads(resp.read().decode())

        for table in data:
            for rate_info in table.get("rates", []):
                code = rate_info.get("code", "")
                mid = rate_info.get("mid")
                if code in SUPPORTED_CURRENCIES and mid is not None:
                    rates[code] = float(mid)

        logger.info("NBP rates fetched: %d currencies", len(rates))
    except Exception as e:
        logger.warning("Failed to fetch NBP rates: %s", e)

    return rates


class CurrencyConverter:
    """Currency converter with daily rate caching."""

    def __init__(self, cache_dir: Optional[str] = None):
        self._cache_dir = Path(cache_dir) if cache_dir else CACHE_DIR
        self._rates: dict[str, dict[str, float]] = {}

    def _load_cache(self) -> dict[str, float] | None:
        """Load cached rates if fresh enough."""
        cache_file = self._cache_dir / "rates.json"
        if not cache_file.exists():
            return None

        try:
            with open(cache_file) as f:
                cached = json.load(f)

            # Check cache age
            fetched = cached.get("fetched_at", "")
            if fetched:
                fetched_dt = datetime.fromisoformat(fetched)
                age = (datetime.now(timezone.utc) - fetched_dt).total_seconds()
                if age < CACHE_TTL_SECONDS:
                    rates: dict[str, float] = cached.get("rates", {})
                    return rates
        except Exception:
            pass

        return None

    def _save_cache(self, rates: dict[str, float]) -> None:
        """Save rates to cache."""
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = self._cache_dir / "rates.json"
        try:
            with open(cache_file, "w") as f:
                json.dump(
                    {
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                        "rates": rates,
                    },
                    f,
                    indent=2,
                )
        except Exception as e:
            logger.warning("Failed to save FX cache: %s", e)

    def _build_cross_rates(self, base_rates: dict[str, float]) -> dict[str, dict[str, float]]:
        """Build cross-currency conversion table from EUR-based rates."""
        cross: dict[str, dict[str, float]] = {}
        currencies = [c for c in SUPPORTED_CURRENCIES if c in base_rates]

        for src in currencies:
            cross[src] = {}
            src_in_eur = base_rates.get(src, 1.0) if src != "EUR" else 1.0
            for dst in currencies:
                dst_in_eur = base_rates.get(dst, 1.0) if dst != "EUR" else 1.0
                # src -> EUR -> dst
                cross[src][dst] = dst_in_eur / src_in_eur

        return cross

    def refresh_rates(self) -> dict[str, float]:
        """Fetch fresh rates and update cache."""
        # Try ECB first (more comprehensive)
        rates = _fetch_ecb_rates()

        # Supplement with NBP for PLN accuracy
        nbp_rates = _fetch_nbp_rates()
        if "PLN" not in rates and "PLN" in nbp_rates:
            # Convert NBP PLN-based to EUR-based
            eur_to_pln = nbp_rates.get("EUR", 4.3)  # approximate fallback
            rates["PLN"] = 1.0 / eur_to_pln  # PLN expressed as 1 PLN = X EUR
            for code, pln_rate in nbp_rates.items():
                if code not in rates and code in SUPPORTED_CURRENCIES:
                    rates[code] = pln_rate / eur_to_pln

        if len(rates) > 1:
            self._save_cache(rates)

        self._rates = self._build_cross_rates(rates)
        return rates

    def get_rates(self) -> dict[str, dict[str, float]]:
        """Get conversion rates, loading from cache or fetching fresh."""
        if self._rates:
            return self._rates

        cached = self._load_cache()
        if cached:
            self._rates = self._build_cross_rates(cached)
            return self._rates

        self.refresh_rates()
        return self._rates

    def convert(
        self,
        amount: float,
        from_currency: str,
        to_currency: str,
    ) -> Optional[float]:
        """Convert amount between currencies.

        Args:
            amount: Amount to convert
            from_currency: Source currency code (e.g. "PLN")
            to_currency: Target currency code (e.g. "EUR")

        Returns:
            Converted amount, or None if conversion not available
        """
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        if from_currency == to_currency:
            return amount

        rates = self.get_rates()
        if from_currency not in rates or to_currency not in rates.get(from_currency, {}):
            logger.warning("No rate for %s -> %s", from_currency, to_currency)
            return None

        rate = rates[from_currency][to_currency]
        return round(amount * rate, 2)

    def format_price(
        self,
        amount: float,
        currency: str,
        locale: str = "en",
    ) -> str:
        """Format a price amount with currency symbol.

        Args:
            amount: Price amount
            currency: Currency code
            locale: Locale for formatting

        Returns:
            Formatted price string
        """
        currency_symbols = {
            "EUR": "€",
            "USD": "$",
            "GBP": "£",
            "PLN": "zł",
            "CHF": "CHF",
            "CZK": "Kč",
            "UAH": "₴",
            "TRY": "₺",
            "ARS": "$",
            "BRL": "R$",
            "CNY": "¥",
            "JPY": "¥",
            "KRW": "₩",
        }
        symbol = currency_symbols.get(currency, currency)

        # Format with thousands separator
        if locale in ("de", "es", "it", "pt", "fr"):
            formatted = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        else:
            formatted = f"{amount:,.2f}"

        # EUR-style: symbol after amount
        if currency in ("EUR", "PLN", "CZK", "UAH", "TRY", "CHF"):
            return f"{formatted} {symbol}"
        return f"{symbol}{formatted}"


# Module-level singleton
_converter: Optional[CurrencyConverter] = None


def get_currency_converter() -> CurrencyConverter:
    """Get or create the global currency converter instance."""
    global _converter
    if _converter is None:
        _converter = CurrencyConverter()
    return _converter


@dataclass(frozen=True)
class NbpReferenceRate:
    """The NBP reference rate, with the date the bank published it.

    The date is part of the value: a rate without a date is a number nobody
    can trace, and a mortgage payment computed from it cannot be explained.
    """

    rate: float
    published_at: Optional[str]
    effective_from: Optional[str]
    source_url: str = NBP_REFERENCE_RATE_URL
    is_fallback: bool = False

    @property
    def label(self) -> str:
        """How an answer names the rate it used."""
        if self.is_fallback:
            return f"NBP reference rate - offline fallback, last published {self.published_at}"
        return f"NBP reference rate, published {self.published_at}"


def _parse_nbp_reference_rate(content: str) -> Optional[NbpReferenceRate]:
    """Read the reference rate out of the NBP base-rates file.

    The file is parsed with a regular expression rather than an XML parser,
    the same way the ECB feed is read above: the file is small, flat and
    stable, and `xml.etree` is what the security scan flags.
    """
    import re

    element = re.search(r"<pozycja\b[^>]*\bid=\"ref\"[^>]*>", content)
    if not element:
        return None

    block = element.group(0)
    value = re.search(r'oprocentowanie="([\d.,]+)"', block)
    if not value:
        return None

    # NBP writes the decimal separator as a comma.
    rate = float(value.group(1).replace(",", "."))
    effective = re.search(r'obowiazuje_od="([\d-]+)"', block)
    published = re.search(r'data_publikacji="([\d-]+)"', content)

    return NbpReferenceRate(
        rate=rate,
        published_at=published.group(1) if published else None,
        effective_from=effective.group(1) if effective else None,
    )


def _fetch_nbp_reference_rate() -> Optional[NbpReferenceRate]:
    """Fetch the reference rate from the NBP base-rates file."""
    try:
        req = urllib.request.Request(NBP_REFERENCE_RATE_URL, headers={"User-Agent": "fx-rates/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:  # nosec B310 - hardcoded trusted NBP URL
            content = resp.read().decode("utf-8-sig")

        rate = _parse_nbp_reference_rate(content)
        if rate is None:
            logger.warning("NBP reference rate not found in %s", NBP_REFERENCE_RATE_URL)
        else:
            logger.info(
                "NBP reference rate fetched: %s%% (published %s)",
                rate.rate,
                rate.published_at,
            )
        return rate
    except Exception as e:
        logger.warning("Failed to fetch NBP reference rate: %s", e)
        return None


def _load_nbp_reference_rate_cache() -> Optional[NbpReferenceRate]:
    """Load the cached reference rate if it is fresh enough."""
    cache_file = CACHE_DIR / "nbp_reference_rate.json"
    if not cache_file.exists():
        return None

    try:
        with open(cache_file) as f:
            cached = json.load(f)

        fetched = cached.get("fetched_at", "")
        if fetched:
            fetched_dt = datetime.fromisoformat(fetched)
            age = (datetime.now(timezone.utc) - fetched_dt).total_seconds()
            if age < CACHE_TTL_SECONDS:
                return NbpReferenceRate(
                    rate=float(cached["rate"]),
                    published_at=cached.get("published_at"),
                    effective_from=cached.get("effective_from"),
                )
    except Exception:
        pass

    return None


def _save_nbp_reference_rate_cache(rate: NbpReferenceRate) -> None:
    """Save the reference rate to the cache."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = CACHE_DIR / "nbp_reference_rate.json"
        with open(cache_file, "w") as f:
            json.dump(
                {
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "rate": rate.rate,
                    "published_at": rate.published_at,
                    "effective_from": rate.effective_from,
                },
                f,
                indent=2,
            )
    except Exception as e:
        logger.warning("Failed to save the NBP reference rate cache: %s", e)


def get_nbp_reference_rate() -> NbpReferenceRate:
    """The NBP reference rate, read from the bank at request time.

    The file is fetched and cached on disk for a day, the same way the
    currency rates are. When the network is unavailable the last published
    value is used instead - and the result says it is a fallback, so an
    offline answer is never dressed up as a live rate.
    """
    cached = _load_nbp_reference_rate_cache()
    if cached:
        return cached

    fetched = _fetch_nbp_reference_rate()
    if fetched:
        _save_nbp_reference_rate_cache(fetched)
        return fetched

    logger.warning(
        "Using the offline NBP reference rate fallback (last published %s)",
        NBP_REFERENCE_RATE_FALLBACK_DATE,
    )
    return NbpReferenceRate(
        rate=NBP_REFERENCE_RATE_FALLBACK,
        published_at=NBP_REFERENCE_RATE_FALLBACK_DATE,
        effective_from=NBP_REFERENCE_RATE_FALLBACK_DATE,
        is_fallback=True,
    )
