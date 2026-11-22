"""Valuation: what a flat is worth, and what the number rests on.

Two providers answer the same question. The simple one multiplies the area by
the catalogue's own price per square metre. The RCN one compares the flat
with the prices people actually paid for neighbouring flats, as the official
register records them — and says how many sales the comparison stands on,
which period they cover and which area they came from.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from sqlalchemy.ext.asyncio import AsyncSession

from services.rcn_valuation import MarketTrend

logger = logging.getLogger(__name__)


@runtime_checkable
class ValuationProvider(Protocol):
    def estimate_value(self, property_data: Dict[str, Any]) -> float: ...


class SimpleValuationProvider:
    def estimate_value(self, property_data: Dict[str, Any]) -> float:
        area = float(property_data.get("area", 0) or 0)
        price_per_sqm = float(property_data.get("price_per_sqm", 0) or 0)
        value = area * price_per_sqm
        return float(value)


@dataclass
class ValuationOutcome:
    """A valuation and the evidence under it.

    A number without the evidence is not an answer, so the outcome always
    carries the sample, the period and the area it came from.
    """

    estimated_value: Optional[float] = None
    low: Optional[float] = None
    high: Optional[float] = None
    price_per_sqm_median: Optional[float] = None
    sample_size: int = 0
    comparison_area: str = ""
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    confidence: str = "low"
    notes: List[str] = field(default_factory=list)
    comparables: List[Dict[str, Any]] = field(default_factory=list)
    source: str = "simple"
    currency: str = "PLN"


@dataclass(frozen=True)
class RegisterContext:
    """What the official register says about a place, in one read.

    The forecast needs two things from the register: what a square metre costs
    there, and how that moved. Both are measured from the same sales, so both
    come from one read.
    """

    median_price_per_sqm: Optional[float] = None
    trend: Optional[MarketTrend] = None
    sample_size: int = 0
    comparison_area: str = ""
    period_start: Optional[date] = None
    period_end: Optional[date] = None

    @property
    def has_data(self) -> bool:
        return self.sample_size > 0


# A busy city registers tens of thousands of sales in a couple of years, so
# the comparison is bounded. The bound limits the evidence, never the honesty
# about it: the result always says how much evidence there was.
STREET_LIMIT = 2000
CITY_LIMIT = 5000


class RcnValuationProvider:
    """Values a flat from the prices people actually paid.

    The register is downloaded and ingested by a separate job; this provider
    only ever reads what is stored, so an answer never waits for a download.
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    async def _transactions(self, city: str, street: str = "") -> List[Any]:
        """The sales of a place: the street first, the city when it is too thin."""
        from data.rcn.rcn_models import normalize_text
        from db.property_transaction_repo import transactions_for
        from services.rcn_valuation import MAX_MONTHS, MIN_COMPARABLE_SAMPLE

        city_norm = normalize_text(city)
        street_norm = normalize_text(street) or None
        since = date.today() - timedelta(days=365 * MAX_MONTHS)

        transactions = await transactions_for(
            self._session, city_norm, street_norm, since=since, limit=STREET_LIMIT
        )
        if len(transactions) < MIN_COMPARABLE_SAMPLE:
            # The street alone is too thin: the city is the wider comparison.
            wider = await transactions_for(
                self._session, city_norm, None, since=since, limit=CITY_LIMIT
            )
            seen = {t.external_id for t in transactions}
            transactions.extend(t for t in wider if t.external_id not in seen)
        return transactions

    async def outcome(self, property_data: Dict[str, Any]) -> ValuationOutcome:
        from services.rcn_valuation import (
            ValuationSubject,
            value_transactions,
        )

        city = str(property_data.get("city") or "").strip()
        street = str(property_data.get("street") or "").strip()
        if not city:
            return ValuationOutcome(source="rcn", notes=["The address does not name a city."])

        area = property_data.get("area_sqm", property_data.get("area"))
        rooms = property_data.get("rooms")
        subject = ValuationSubject(
            city=city,
            street=street,
            area_sqm=float(area) if area else None,
            rooms=int(rooms) if rooms else None,
        )

        transactions = await self._transactions(city, street)

        result = value_transactions(transactions, subject)

        return ValuationOutcome(
            estimated_value=result.estimate,
            low=result.low,
            high=result.high,
            price_per_sqm_median=result.price_per_sqm_median,
            sample_size=result.sample_size,
            comparison_area=result.comparison_area,
            period_start=result.period_start,
            period_end=result.period_end,
            confidence=result.confidence,
            notes=result.notes,
            comparables=[
                {
                    "address": comparable.address,
                    "area_sqm": comparable.area_sqm,
                    "price": comparable.price,
                    "price_per_sqm": comparable.price_per_sqm,
                    "transaction_date": comparable.transaction_date.isoformat(),
                    "rooms": comparable.rooms,
                    "floor": comparable.floor,
                    "deed_reference": comparable.deed_reference,
                }
                for comparable in result.comparables
            ],
            source=result.source,
        )

    async def context(self, city: str, street: str = "") -> "RegisterContext":
        """What the register says about a place: its prices and their movement.

        The street is the comparison when it carries enough sales; the city is
        the fallback, and a measurement that cannot be made is left empty
        rather than filled with an assumption.
        """
        from services.rcn_valuation import (
            ValuationSubject,
            appreciation_from_transactions,
            select_comparables,
            value_transactions,
        )

        transactions = await self._transactions(city, street)
        subject = ValuationSubject(city=city, street=street)
        result = value_transactions(transactions, subject)

        # The rate is measured on the comparison the estimate stands on, so
        # the two never describe different places. When that comparison is too
        # thin to carry a rate, the city is measured instead and named.
        selected, _notes = select_comparables(transactions, subject)
        trend = appreciation_from_transactions(selected, result.comparison_area)
        if trend is None:
            trend = appreciation_from_transactions(transactions, city)

        return RegisterContext(
            median_price_per_sqm=result.price_per_sqm_median,
            trend=trend,
            sample_size=result.sample_size,
            comparison_area=result.comparison_area,
            period_start=result.period_start,
            period_end=result.period_end,
        )


async def read_register_context(city: str, street: str = "") -> Optional[RegisterContext]:
    """Read the register for a place, in a session of its own.

    The caller may be synchronous code on a worker thread, so the session is
    opened here rather than passed in: a pooled connection belongs to the loop
    that opened it.
    """
    if not city.strip():
        return None
    from db.database import standalone_session

    async with standalone_session() as session:
        provider = RcnValuationProvider(session)
        return await provider.context(city, street)


def read_register_context_sync(city: str, street: str = "") -> Optional[RegisterContext]:
    """Read the register for a place from synchronous code.

    A register that cannot be read is not a reason to fail a forecast: the
    forecast then falls back to what it has and says so.
    """
    if not city.strip():
        return None
    from tools.async_bridge import run_detached

    try:
        return run_detached(read_register_context(city, street))
    except Exception as exc:  # pragma: no cover - the store may be absent
        logger.warning("The official price register could not be read: %s", exc)
        return None
