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
class PlaceOutcome:
    """What the register says about a place, and on what evidence.

    A place has no single flat to price, so there is no estimate here: the
    price a square metre costs there, the sales the figure is measured on,
    the period those sales cover and the sales themselves.
    """

    place: str = ""
    district: str = ""
    median_price_per_sqm: Optional[float] = None
    first_quartile_price_per_sqm: Optional[float] = None
    third_quartile_price_per_sqm: Optional[float] = None
    sample_size: int = 0
    registered_count: Optional[int] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    comparison_area: str = ""
    confidence: str = "low"
    notes: List[str] = field(default_factory=list)
    comparables: List[Dict[str, Any]] = field(default_factory=list)
    districts: List[str] = field(default_factory=list)
    source: str = "rcn"
    currency: str = "PLN"

    @property
    def has_figures(self) -> bool:
        return self.sample_size > 0


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

# A place's page reads the register over two years, and it reads a bounded
# number of the sales it finds there: a busy city registers tens of thousands
# of them, and a page that read all of them would answer slowly and say
# nothing the sample did not already say.
PLACE_WINDOW_MONTHS = 24
PLACE_SAMPLE_LIMIT = 10000


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

    async def covered_places(self) -> List[tuple[Any, List[Any]]]:
        """The places the register covers, and the districts it covers of each.

        A place gets a page only when the register holds a sale for it. The
        site knows five cities, but the register of a deployment may hold
        three of them - and a city it holds nothing for has no page, no link
        and no place in the sitemap. The read is one grouped query over the
        register's own rows.
        """
        from data.places import PLACES
        from data.rcn.rcn_models import normalize_text
        from db.property_transaction_repo import usable_sales_by_city_street

        since = date.today() - timedelta(days=365 * PLACE_WINDOW_MONTHS)
        counts = await usable_sales_by_city_street(self._session, since=since)

        covered: List[tuple[Any, List[Any]]] = []
        for place in PLACES:
            city_norm = normalize_text(place.register_city)
            street_counts = {
                street: count for (city, street), count in counts.items() if city == city_norm
            }
            if not sum(street_counts.values()):
                continue
            districts = [
                district
                for district in place.districts
                if sum(street_counts.get(normalize_text(street), 0) for street in district.streets)
            ]
            covered.append((place, districts))
        return covered

    async def place_outcome(self, city: str, district: str = "") -> "PlaceOutcome":
        """What the register says about a place - a city, or a district of one.

        A place has no flat to price, so the answer is the price a square
        metre costs there, the sales that is measured on, the period those
        sales cover and the sales themselves.

        The register knows streets, not districts: a district's sales are the
        sales registered on the streets the district stands on.
        """
        from data.places import find_district, find_place
        from data.rcn.rcn_models import normalize_text
        from db.property_transaction_repo import (
            count_transactions,
            transactions_for,
            transactions_for_streets,
        )
        from services.rcn_valuation import place_figures

        place = find_place(city)
        if place is None:
            return PlaceOutcome(source="rcn", notes=[f"The register does not know {city}."])

        district_name = (district or "").strip()
        district_entry = None
        if district_name:
            district_entry = find_district(place, district_name)
            if district_entry is None:
                return PlaceOutcome(
                    source="rcn",
                    notes=[f"{place.name} has no district called {district_name}."],
                )

        since = date.today() - timedelta(days=365 * PLACE_WINDOW_MONTHS)
        city_norm = normalize_text(place.register_city)

        if district_entry is not None:
            street_norms = [normalize_text(street) for street in district_entry.streets]
            transactions = await transactions_for_streets(
                self._session,
                city_norm,
                street_norms,
                since=since,
                limit=PLACE_SAMPLE_LIMIT,
            )
            comparison_area = f"{district_entry.name}, {place.name}"
        else:
            street_norms = None
            transactions = await transactions_for(
                self._session,
                city_norm,
                since=since,
                limit=PLACE_SAMPLE_LIMIT,
            )
            comparison_area = place.name

        # The register holds far more sales than a page reads, so the sample
        # is the most recent of them and the count is asked of the database
        # for the period that sample covers. The page then says how many
        # sales the place has and how many of them it measured.
        sample_capped = len(transactions) >= PLACE_SAMPLE_LIMIT
        registered_count = None
        if transactions:
            period_start = min(t.transaction_date for t in transactions)
            period_end = max(t.transaction_date for t in transactions)
            registered_count = await count_transactions(
                self._session,
                city_norm,
                street_norms,
                since=period_start,
                until=period_end,
            )

        figures = place_figures(
            transactions,
            comparison_area,
            sample_capped=sample_capped,
            registered_count=registered_count,
        )

        # The districts a page may link to are the ones the register covers:
        # a link to a district without a sale is a link to a 404.
        covered_districts: List[str] = []
        for covered_place, districts in await self.covered_places():
            if covered_place.name == place.name:
                covered_districts = [entry.name for entry in districts]
                break

        return PlaceOutcome(
            place=place.name,
            district=district_entry.name if district_entry else "",
            median_price_per_sqm=figures.median_price_per_sqm,
            first_quartile_price_per_sqm=figures.first_quartile_price_per_sqm,
            third_quartile_price_per_sqm=figures.third_quartile_price_per_sqm,
            sample_size=figures.sample_size,
            registered_count=figures.registered_count,
            period_start=figures.period_start,
            period_end=figures.period_end,
            comparison_area=figures.comparison_area,
            confidence=figures.confidence,
            notes=figures.notes,
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
                for comparable in figures.comparables
            ],
            districts=covered_districts,
            source="rcn",
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
