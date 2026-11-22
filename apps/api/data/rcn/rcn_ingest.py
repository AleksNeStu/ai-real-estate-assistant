"""Bringing the official price register into the database.

GUGiK republishes the whole export for a voivodeship every week. The ingest
reads that file and stores the sales it holds that are not stored yet — the
register is append-only in practice, so a refresh writes the new deeds and
leaves the old ones alone.

The download and the parse are the slow part, so they run in a worker thread
and the database work stays on the event loop.
"""

import asyncio
import hashlib
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from data.rcn.rcn_client import RCN_VOIVODESHIPS, export_url, fetch_transactions
from data.rcn.rcn_models import RCNTransaction, normalize_text
from db.models import PropertyTransaction
from db.property_transaction_repo import add_rows, known_external_ids

logger = logging.getLogger(__name__)

# The register keeps every deed ever registered. A valuation never looks
# further back than five years, so only the recent ones are stored.
DEFAULT_INGEST_YEARS = 6


@dataclass(frozen=True)
class IngestReport:
    """What one refresh of a voivodeship's export did."""

    voivodeship: str
    fetched: int
    inserted: int
    known: int
    source_url: str


def default_since(years: int = DEFAULT_INGEST_YEARS) -> date:
    """The oldest deed worth storing."""
    return date.today() - timedelta(days=365 * years + 1)


def external_id_for(transaction: RCNTransaction) -> str:
    """The register's own identifier for a flat.

    The register gives every row a feature id, and that id names one flat —
    a deed that sells two flats in the same building still registers two
    rows. A row without an id is keyed by what it says instead: the
    transaction, the deed, the date, the address, the area and the price.
    """
    if transaction.external_id:
        return transaction.external_id
    payload = "|".join(
        [
            transaction.transaction_id,
            transaction.deed_reference,
            transaction.transaction_date.isoformat(),
            transaction.address.street,
            transaction.address.number,
            f"{transaction.area_sqm:.2f}",
            f"{transaction.price:.2f}",
            str(transaction.rooms),
            str(transaction.floor),
        ]
    )
    return "sha256:" + hashlib.sha256(payload.encode()).hexdigest()[:32]


def to_row(transaction: RCNTransaction, source_url: str) -> PropertyTransaction:
    """Turn a transaction into the row that stores it."""
    return PropertyTransaction(
        external_id=external_id_for(transaction),
        transaction_id=transaction.transaction_id or None,
        deed_reference=transaction.deed_reference or None,
        teryt=transaction.teryt or None,
        city=transaction.address.city,
        city_norm=normalize_text(transaction.address.city),
        street=transaction.address.street,
        street_norm=normalize_text(transaction.address.street),
        number=transaction.address.number or None,
        area_sqm=transaction.area_sqm,
        rooms=transaction.rooms,
        floor=transaction.floor,
        price_brutto=transaction.price,
        currency=transaction.currency,
        transaction_date=transaction.transaction_date,
        market_type=transaction.market or None,
        source="rcn",
        source_url=source_url,
        x_2180=transaction.x,
        y_2180=transaction.y,
    )


async def store_transactions(
    session: AsyncSession,
    transactions: list[RCNTransaction],
    source_url: str,
) -> tuple[int, int]:
    """Store the given sales and return how many were written and how many were known.

    The register republishes the whole file every week, so a refresh has to
    know what it already holds. A sale is keyed by the register's own feature
    id, which names one flat — a deed may sell two flats in one building.
    """
    municipalities = {t.teryt for t in transactions if t.teryt}
    known = await known_external_ids(session, sorted(municipalities))

    rows: list[PropertyTransaction] = []
    seen: set[str] = set()
    for transaction in transactions:
        external_id = external_id_for(transaction)
        if external_id in known or external_id in seen:
            continue
        seen.add(external_id)
        rows.append(to_row(transaction, source_url))

    inserted = await add_rows(session, rows)
    return inserted, len(transactions) - len(rows)


async def ingest_voivodeship(
    session: AsyncSession,
    teryt_code: str,
    since: Optional[date] = None,
    cache_dir: Optional[Path] = None,
    force_download: bool = False,
) -> IngestReport:
    """Fetch one voivodeship's export and store the sales it does not hold yet."""
    since = since or default_since()
    url = export_url(teryt_code)

    logger.info("Reading the RCN export for %s (since %s)", teryt_code, since)
    transactions = await asyncio.to_thread(
        fetch_transactions, teryt_code, since, cache_dir, force_download
    )

    inserted, known = await store_transactions(session, transactions, url)
    logger.info(
        "RCN %s: %s sale(s) read, %s already stored, %s written",
        teryt_code,
        len(transactions),
        known,
        inserted,
    )
    return IngestReport(
        voivodeship=teryt_code,
        fetched=len(transactions),
        inserted=inserted,
        known=known,
        source_url=url,
    )


async def ingest_demo_voivodeships(
    session: AsyncSession,
    voivodeships: Optional[list[str]] = None,
    since: Optional[date] = None,
    cache_dir: Optional[Path] = None,
    force_download: bool = False,
) -> list[IngestReport]:
    """Refresh every voivodeship the demo serves."""
    codes = voivodeships or list(RCN_VOIVODESHIPS)
    reports = []
    for code in codes:
        reports.append(
            await ingest_voivodeship(
                session,
                code,
                since=since,
                cache_dir=cache_dir,
                force_download=force_download,
            )
        )
    return reports


async def _run() -> None:
    """Refresh the demo voivodeships from the command line."""
    import argparse

    from db.database import get_db_context

    parser = argparse.ArgumentParser(description="Refresh the official price register.")
    parser.add_argument(
        "--teryt",
        action="append",
        help="The voivodeship to refresh; repeatable. Defaults to every demo voivodeship.",
    )
    parser.add_argument(
        "--years",
        type=int,
        default=DEFAULT_INGEST_YEARS,
        help="How many years of deeds to keep.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Download the export even when the cached copy is current.",
    )
    arguments = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    since = default_since(arguments.years)

    async with get_db_context() as session:
        reports = await ingest_demo_voivodeships(
            session,
            voivodeships=arguments.teryt,
            since=since,
            force_download=arguments.force,
        )

    for report in reports:
        print(
            f"{report.voivodeship}: {report.inserted} written, {report.known} already known, "
            f"{report.fetched} read — {report.source_url}"
        )


if __name__ == "__main__":
    asyncio.run(_run())
