"""Valuing a flat from the prices people actually paid.

The Rejestr Cen Nieruchomości holds the price, the area and the deed date of
every sale a notary registered. A valuation is therefore a comparison, not a
model: the flats sold nearby, recently, of a similar size, and what their price
per square metre was.

The service is deliberately explicit about what it knows. A result always carries
the number of comparable sales, the period they cover and the area they came
from, because a number without those three is a guess wearing a suit.
"""

import logging
import statistics
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Iterable, Optional, Sequence

from data.rcn.rcn_models import RCNTransaction, normalize_text

logger = logging.getLogger(__name__)

# The secondary market is what an existing flat is worth; the new-build market
# prices a different product.
SECONDARY_MARKET = "rynekWtorny"

# A comparable set smaller than this is not an answer, it is an anecdote.
MIN_SAMPLE = 5
# Below this the result is worth showing but not worth believing.
LOW_CONFIDENCE_SAMPLE = 8
MEDIUM_CONFIDENCE_SAMPLE = 20
# The sample a comparison area needs before the comparison may stand on it.
# Below it the area widens — place and size give way before time does.
MIN_COMPARABLE_SAMPLE = LOW_CONFIDENCE_SAMPLE

# How far the comparable's area may differ from the subject's.
DEFAULT_AREA_TOLERANCE = 0.15
# The window of deeds the comparison looks at.
DEFAULT_MONTHS = 18
# How far the window may widen before the city replaces the street.
MAX_MONTHS = 60

# A measured trend needs at least this many sales on each side of the split.
MIN_TREND_HALF = 4
# ...and at least this much time between the two halves.
MIN_TREND_SPAN_DAYS = 180
# A measured rate outside this range is not a trend, it is a handful of sales.
MAX_TREND_RATE = 0.25
MIN_TREND_RATE = -0.15


@dataclass(frozen=True)
class ValuationSubject:
    """The flat being valued."""

    city: str
    street: str = ""
    area_sqm: Optional[float] = None
    rooms: Optional[int] = None
    market: str = SECONDARY_MARKET
    months: int = DEFAULT_MONTHS

    def normalized_city(self) -> str:
        return normalize_text(self.city)

    def normalized_street(self) -> str:
        return normalize_text(self.street)


@dataclass(frozen=True)
class Comparable:
    """One sale the comparison stands on."""

    address: str
    area_sqm: float
    price: float
    price_per_sqm: float
    transaction_date: date
    rooms: Optional[int] = None
    floor: Optional[int] = None
    deed_reference: str = ""


@dataclass(frozen=True)
class ValuationResult:
    """What the register says a flat is worth, and on what evidence."""

    estimate: Optional[float]
    low: Optional[float]
    high: Optional[float]
    price_per_sqm_median: Optional[float]
    comparables: list[Comparable]
    sample_size: int
    comparison_area: str
    period_start: Optional[date]
    period_end: Optional[date]
    currency: str = "PLN"
    source: str = "rcn"
    confidence: str = "low"
    notes: list[str] = field(default_factory=list)

    @property
    def has_value(self) -> bool:
        return self.estimate is not None


@dataclass(frozen=True)
class MarketTrend:
    """What the register says the prices did over a period of time.

    A forecast needs a rate, and a rate nobody measured is a constant wearing
    a forecast's clothes. This one is the change between the older half of the
    sales and the newer half of them, annualised.
    """

    annual_rate: float
    sample_size: int
    period_start: date
    period_end: date
    median_early: float
    median_late: float
    comparison_area: str = ""

    def describe(self) -> str:
        """The rate, said out loud, with the evidence behind it."""
        percent = self.annual_rate * 100
        direction = "rose" if percent >= 0 else "fell"
        return (
            f"Registered prices {direction} {abs(percent):.1f}% a year in "
            f"{self.comparison_area or 'the comparison area'} "
            f"({self.sample_size} sales between {self.period_start.isoformat()} and "
            f"{self.period_end.isoformat()})."
        )


def _months_before(reference: date, months: int) -> date:
    return reference - timedelta(days=round(months * 30.44))


def _quantiles(values: Sequence[float]) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """The first quartile, the median and the third quartile."""
    if not values:
        return None, None, None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0], ordered[0], ordered[0]
    quartiles = statistics.quantiles(ordered, n=4, method="inclusive")
    return quartiles[0], statistics.median(ordered), quartiles[2]


def _matches_city(transaction: RCNTransaction, subject: ValuationSubject) -> bool:
    if not subject.normalized_city():
        return True
    return normalize_text(transaction.address.city) == subject.normalized_city()


def _matches_street(transaction: RCNTransaction, subject: ValuationSubject) -> bool:
    if not subject.normalized_street():
        return True
    return normalize_text(transaction.address.street) == subject.normalized_street()


def select_comparables(
    transactions: Iterable[RCNTransaction],
    subject: ValuationSubject,
    reference_date: Optional[date] = None,
) -> tuple[list[RCNTransaction], list[str]]:
    """Choose the sales the comparison stands on, and say how they were chosen.

    The comparison starts as narrow as it can be — the street, the last months
    and a close size — and widens only as far as it has to. Size and place give
    way before time does: a sale three years old on the same street says more
    about that street than a sale last month across the city does about the flat.

    Every step the selection takes is recorded, because a number without the
    area and the sample it rests on is not an answer.
    """
    reference = reference_date or date.today()
    notes: list[str] = []

    city_pool = [t for t in transactions if _matches_city(t, subject)]
    if not city_pool:
        return [], [f"No sales of flats are registered in {subject.city}."]

    market_pool = city_pool
    if subject.market:
        secondary = [t for t in city_pool if t.market == subject.market]
        if secondary:
            market_pool = secondary
            notes.append(f"Secondary market only ({subject.market}).")
        else:
            notes.append(
                f"No sales on the {subject.market} market; every registered sale was used."
            )

    window = _months_before(reference, subject.months)
    in_window = [t for t in market_pool if t.transaction_date >= window]

    if not in_window:
        # Nothing at all was sold in the window; reach back for what there is.
        months = subject.months
        while not in_window and months < MAX_MONTHS:
            months += 12
            in_window = [
                t for t in market_pool if t.transaction_date >= _months_before(reference, months)
            ]
        if in_window:
            notes.append(
                f"No flat was sold in the last {subject.months} months — the window was "
                f"widened to {months} months to find any sales at all."
            )

    # The areas the comparison may rest on, most specific first: the street at
    # a similar size, the street, the city at a similar size, the city.
    candidates: list[tuple[str, list[RCNTransaction]]] = []
    for label, pool in _comparison_areas(in_window, subject):
        sized = _filter_by_area(pool, subject)
        if sized:
            candidates.append((f"{label}-sized", sized))
        candidates.append((label, pool))

    chosen: list[RCNTransaction] = []
    chosen_label = ""
    for label, pool in candidates:
        if pool and len(pool) >= MIN_COMPARABLE_SAMPLE:
            chosen, chosen_label = pool, label
            break

    if len(chosen) == 0:
        # No area carried enough sales: take the largest pool there is and
        # say plainly that the estimate is thin.
        best_label = ""
        best_pool: list[RCNTransaction] = []
        for label, pool in candidates:
            if len(pool) > len(best_pool):
                best_label, best_pool = label, pool
        if len(best_pool) == 0:
            return [], notes + [f"No sales of flats are registered in {subject.city}."]
        chosen, chosen_label = best_pool, best_label
        notes.append(
            f"Only {len(best_pool)} sale(s) could be found for this flat — the estimate "
            f"is indicative, not a valuation."
        )

    if chosen_label.startswith("city") and subject.normalized_street():
        on_street = len([t for t in in_window if _matches_street(t, subject)])
        if on_street == 0:
            notes.append(
                f"No flat was sold on {subject.street} in this window — the comparison "
                f"fell back to the whole city."
            )
        else:
            notes.append(
                f"Only {on_street} sale(s) on {subject.street} — the comparison fell back "
                f"to the whole city."
            )

    if subject.area_sqm:
        if chosen_label.endswith("-sized"):
            notes.append(f"Flats of a similar size ({_size_band(subject)}).")
        else:
            notes.append(
                "Not enough flats of a similar size were sold on the comparison area — "
                "the comparison widened to every size."
            )

    if subject.rooms and len(chosen) >= MIN_COMPARABLE_SAMPLE:
        same_rooms = [t for t in chosen if t.rooms == subject.rooms]
        if len(same_rooms) >= MIN_COMPARABLE_SAMPLE:
            chosen = same_rooms
            notes.append(f"Flats with {subject.rooms} rooms.")

    if len(chosen) < MIN_COMPARABLE_SAMPLE and chosen_label.startswith("city"):
        # The comparison area is already the whole city; now let time widen.
        months = subject.months
        while len(chosen) < MIN_COMPARABLE_SAMPLE and months < MAX_MONTHS:
            months += 12
            wider = [
                t for t in market_pool if t.transaction_date >= _months_before(reference, months)
            ]
            if len(wider) > len(chosen):
                chosen = wider
                notes.append(f"The window was widened to {months} months to find enough sales.")

    chosen.sort(key=lambda t: t.transaction_date, reverse=True)
    return chosen, notes


def _comparison_areas(
    in_window: list[RCNTransaction], subject: ValuationSubject
) -> list[tuple[str, list[RCNTransaction]]]:
    """The areas a comparison may rest on, most specific first."""
    areas: list[tuple[str, list[RCNTransaction]]] = []
    if subject.normalized_street():
        areas.append(("street", [t for t in in_window if _matches_street(t, subject)]))
    areas.append(("city", in_window))
    return areas


def _filter_by_area(pool: list[RCNTransaction], subject: ValuationSubject) -> list[RCNTransaction]:
    """The sales of a similar size."""
    if not subject.area_sqm:
        return []
    lower = subject.area_sqm * (1 - DEFAULT_AREA_TOLERANCE)
    upper = subject.area_sqm * (1 + DEFAULT_AREA_TOLERANCE)
    return [t for t in pool if lower <= t.area_sqm <= upper]


def _size_band(subject: ValuationSubject) -> str:
    if not subject.area_sqm:
        return "any size"
    return (
        f"{subject.area_sqm * (1 - DEFAULT_AREA_TOLERANCE):.0f}–"
        f"{subject.area_sqm * (1 + DEFAULT_AREA_TOLERANCE):.0f} m²"
    )


def appreciation_from_transactions(
    transactions: Iterable[RCNTransaction],
    comparison_area: str = "",
) -> Optional[MarketTrend]:
    """Measure how the registered prices moved, or say that they cannot be measured.

    The sales are split in two by date: the older half and the newer half. The
    median price per square metre of each half is compared, and the difference
    is annualised over the time between them. The measurement is refused when
    there are too few sales on either side, when the two halves are too close
    in time, or when the result is not a rate a market could have produced.
    """
    sales = [t for t in transactions if t.price_per_sqm > 0 and t.area_sqm > 0]
    if len(sales) < 2 * MIN_TREND_HALF:
        return None

    sales.sort(key=lambda t: t.transaction_date)
    midpoint = len(sales) // 2
    early, late = sales[:midpoint], sales[midpoint:]
    if len(early) < MIN_TREND_HALF or len(late) < MIN_TREND_HALF:
        # Unreachable: the split above puts at least four sales on each side
        # whenever the total is eight or more.
        return None  # pragma: no cover - guarded by the check above

    period_start = early[0].transaction_date
    period_end = late[-1].transaction_date
    span_days = (period_end - period_start).days
    if span_days < MIN_TREND_SPAN_DAYS:
        return None

    median_early = statistics.median([t.price_per_sqm for t in early])
    median_late = statistics.median([t.price_per_sqm for t in late])
    if median_early <= 0:
        # Unreachable: every sale in the median is above zero by the filter
        # that opened this function.
        return None  # pragma: no cover - guarded by the filter above

    years = span_days / 365.25
    rate = (median_late / median_early) ** (1 / years) - 1
    if rate > MAX_TREND_RATE or rate < MIN_TREND_RATE:
        return None

    return MarketTrend(
        annual_rate=rate,
        sample_size=len(sales),
        period_start=period_start,
        period_end=period_end,
        median_early=median_early,
        median_late=median_late,
        comparison_area=comparison_area,
    )


def value_transactions(
    transactions: Iterable[RCNTransaction],
    subject: ValuationSubject,
    reference_date: Optional[date] = None,
) -> ValuationResult:
    """Value a flat from the sales the register holds."""
    selected, notes = select_comparables(transactions, subject, reference_date)

    comparison_area = subject.street or subject.city
    if subject.street and subject.city:
        comparison_area = f"{subject.street}, {subject.city}"

    if not selected:
        return ValuationResult(
            estimate=None,
            low=None,
            high=None,
            price_per_sqm_median=None,
            comparables=[],
            sample_size=0,
            comparison_area=comparison_area,
            period_start=None,
            period_end=None,
            notes=notes,
        )

    prices_per_sqm = [t.price_per_sqm for t in selected if t.price_per_sqm > 0]
    first_quartile, median, third_quartile = _quantiles(prices_per_sqm)

    area = subject.area_sqm or statistics.median([t.area_sqm for t in selected])

    estimate = median * area if median is not None else None
    low = first_quartile * area if first_quartile is not None else None
    high = third_quartile * area if third_quartile is not None else None

    comparables = [
        Comparable(
            address=str(t.address),
            area_sqm=t.area_sqm,
            price=t.price,
            price_per_sqm=t.price_per_sqm,
            transaction_date=t.transaction_date,
            rooms=t.rooms,
            floor=t.floor,
            deed_reference=t.deed_reference,
        )
        for t in selected[:20]
    ]

    period_start = min(t.transaction_date for t in selected)
    period_end = max(t.transaction_date for t in selected)

    if len(selected) >= MEDIUM_CONFIDENCE_SAMPLE:
        confidence = "high"
    elif len(selected) >= LOW_CONFIDENCE_SAMPLE:
        confidence = "medium"
    else:
        confidence = "low"

    notes.append(
        f"Based on {len(selected)} registered sale(s) between {period_start.isoformat()} "
        f"and {period_end.isoformat()}."
    )

    return ValuationResult(
        estimate=estimate,
        low=low,
        high=high,
        price_per_sqm_median=median,
        comparables=comparables,
        sample_size=len(selected),
        comparison_area=comparison_area,
        period_start=period_start,
        period_end=period_end,
        confidence=confidence,
        notes=notes,
    )
