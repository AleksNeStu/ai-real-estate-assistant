"""Repository for the registered sales — the official price register (RCN).

Every read and write of ``property_transactions`` goes through here, so the
rules about what a transaction looks like and how it is keyed live in one
place. The rows are turned back into :class:`RCNTransaction` objects on the
way out, so the valuation service never has to know that a database exists.
"""

from datetime import date
from typing import Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from data.rcn.rcn_models import RCNAddress, RCNTransaction
from db.models import PropertyTransaction


def to_transaction(row: PropertyTransaction) -> RCNTransaction:
    """Turn a stored row back into a transaction."""
    return RCNTransaction(
        external_id=row.external_id,
        teryt=row.teryt or "",
        address=RCNAddress(
            city=row.city,
            street=row.street,
            number=row.number or "",
        ),
        area_sqm=row.area_sqm,
        price=row.price_brutto,
        transaction_date=row.transaction_date,
        market=row.market_type or "",
        rooms=row.rooms,
        floor=row.floor,
        deed_reference=row.deed_reference or "",
        x=row.x_2180,
        y=row.y_2180,
        transaction_id=row.transaction_id or "",
        source_url=row.source_url or "",
    )


async def known_external_ids(session: AsyncSession, teryt_codes: Sequence[str]) -> set[str]:
    """The transactions already stored for the given municipalities.

    The register republishes the whole file every week, so the ingest has to
    know what it already holds — otherwise every refresh would write the
    entire history again.
    """
    if not teryt_codes:
        return set()
    result = await session.execute(
        select(PropertyTransaction.external_id).where(
            PropertyTransaction.teryt.in_(list(teryt_codes))
        )
    )
    return set(result.scalars().all())


async def add_rows(session: AsyncSession, rows: Sequence[PropertyTransaction]) -> int:
    """Store the given transactions and return how many were written."""
    if not rows:
        return 0
    session.add_all(rows)
    await session.commit()
    return len(rows)


async def transactions_for(
    session: AsyncSession,
    city_norm: str,
    street_norm: Optional[str] = None,
    since: Optional[date] = None,
    limit: int = 5000,
    until: Optional[date] = None,
) -> list[RCNTransaction]:
    """The sales registered in one city, most recent first.

    The comparison never needs the whole history, and a busy city registers
    tens of thousands of sales in a couple of years, so the read is bounded
    by both the window and the row limit. The street narrows it further when
    the address names one.

    The upper bound is today. The register carries the occasional deed dated
    in the future - a typo in the starosta's register, not a sale that has
    not happened yet - and the read is ordered by date descending, so such a
    row would sit at the top of the result set and count against the limit
    that the real sales have to share.
    """
    query = select(PropertyTransaction).where(PropertyTransaction.city_norm == city_norm)
    if street_norm:
        query = query.where(PropertyTransaction.street_norm == street_norm)
    if since is not None:
        query = query.where(PropertyTransaction.transaction_date >= since)
    query = query.where(PropertyTransaction.transaction_date <= (until or date.today()))
    query = query.order_by(PropertyTransaction.transaction_date.desc()).limit(limit)
    result = await session.execute(query)
    return [to_transaction(row) for row in result.scalars().all()]


async def transactions_for_streets(
    session: AsyncSession,
    city_norm: str,
    street_norms: Sequence[str],
    since: Optional[date] = None,
    limit: int = 5000,
    until: Optional[date] = None,
) -> list[RCNTransaction]:
    """The sales registered on several streets of one city.

    A district holds no column of its own in the register - the register knows
    streets - so the district's sales are the sales of the streets it stands
    on. The read is the street read with more than one street in it.
    """
    if not street_norms:
        return []
    query = select(PropertyTransaction).where(PropertyTransaction.city_norm == city_norm)
    query = query.where(PropertyTransaction.street_norm.in_(list(street_norms)))
    if since is not None:
        query = query.where(PropertyTransaction.transaction_date >= since)
    query = query.where(PropertyTransaction.transaction_date <= (until or date.today()))
    query = query.order_by(PropertyTransaction.transaction_date.desc()).limit(limit)
    result = await session.execute(query)
    return [to_transaction(row) for row in result.scalars().all()]


async def count_transactions(
    session: AsyncSession,
    city_norm: str,
    street_norms: Optional[Sequence[str]] = None,
    since: Optional[date] = None,
    until: Optional[date] = None,
) -> int:
    """How many sales the register holds for a place, counted in the database.

    A busy city registers tens of thousands of sales in a year, so the pages
    cannot read them all to count them - the count is asked of the database,
    which answers it without building a row object for every sale.
    """
    query = select(func.count()).select_from(PropertyTransaction)
    query = query.where(PropertyTransaction.city_norm == city_norm)
    if street_norms is not None:
        if not street_norms:
            return 0
        query = query.where(PropertyTransaction.street_norm.in_(list(street_norms)))
    if since is not None:
        query = query.where(PropertyTransaction.transaction_date >= since)
    query = query.where(PropertyTransaction.transaction_date <= (until or date.today()))
    result = await session.execute(query)
    return int(result.scalar() or 0)


async def usable_sales_by_city_street(
    session: AsyncSession,
    since: Optional[date] = None,
    until: Optional[date] = None,
) -> dict[tuple[str, str], int]:
    """How many usable sales the register holds, per city and per street.

    A sale is usable when it carries a price and an area - the two things a
    price per square metre is computed from. The read is one grouped query,
    because the question it answers is asked of every city and every district
    at once: which places the register covers at all.
    """
    query = select(
        PropertyTransaction.city_norm,
        PropertyTransaction.street_norm,
        func.count(),
    ).where(
        PropertyTransaction.price_brutto > 0,
        PropertyTransaction.area_sqm > 0,
        PropertyTransaction.transaction_date <= (until or date.today()),
    )
    if since is not None:
        query = query.where(PropertyTransaction.transaction_date >= since)
    query = query.group_by(PropertyTransaction.city_norm, PropertyTransaction.street_norm)
    result = await session.execute(query)
    return {(city, street): int(count) for city, street, count in result.all()}
