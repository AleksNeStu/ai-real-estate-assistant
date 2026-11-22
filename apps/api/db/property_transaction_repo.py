"""Repository for the registered sales — the official price register (RCN).

Every read and write of ``property_transactions`` goes through here, so the
rules about what a transaction looks like and how it is keyed live in one
place. The rows are turned back into :class:`RCNTransaction` objects on the
way out, so the valuation service never has to know that a database exists.
"""

from datetime import date
from typing import Optional, Sequence

from sqlalchemy import select
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
) -> list[RCNTransaction]:
    """The sales registered in one city, most recent first.

    The comparison never needs the whole history, and a busy city registers
    tens of thousands of sales in a couple of years, so the read is bounded
    by both the window and the row limit. The street narrows it further when
    the address names one.
    """
    query = select(PropertyTransaction).where(PropertyTransaction.city_norm == city_norm)
    if street_norm:
        query = query.where(PropertyTransaction.street_norm == street_norm)
    if since is not None:
        query = query.where(PropertyTransaction.transaction_date >= since)
    query = query.order_by(PropertyTransaction.transaction_date.desc()).limit(limit)
    result = await session.execute(query)
    return [to_transaction(row) for row in result.scalars().all()]
