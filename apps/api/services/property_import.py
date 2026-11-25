"""The one property-import chain: read a file into properties, write them to the catalogue.

Two callers land properties in this product - the bulk-job import and the
data-source sync. Both read through the same loaders and write through the same
catalogue, so a record a sync counted is a record the product can find. A second
copy of this chain is a second truth about what the product holds.
"""

import logging
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import pandas as pd

from data.schemas import Property, PropertyCollection
from utils.property_cache import load_collection, save_collection

logger = logging.getLogger(__name__)

# The spreadsheet formats the loaders read.
EXCEL_SUFFIXES = {".xlsx", ".xls", ".ods"}

# The formats an import accepts. Anything else is counted as a failed source
# instead of being handed to the loaders.
SUPPORTED_SUFFIXES = EXCEL_SUFFIXES | {".csv"}


def source_suffix(source: str) -> str:
    """The file suffix of a path or an http(s) URL, lowercased."""
    parsed = urlparse(str(source))
    path = parsed.path if parsed.scheme and parsed.netloc else str(source)
    return Path(path).suffix.lower()


def is_missing(value: Any) -> bool:
    """True when a record carries no value for a field (absent, None or NaN)."""
    if value is None:
        return True
    if isinstance(value, float):
        return bool(pd.isna(value))
    return False


def properties_from_records(
    records: list[dict[str, Any]],
    *,
    source_name: Optional[str] = None,
    source_type: Optional[str] = None,
) -> tuple[list[Property], list[str]]:
    """Build properties from plain records - a JSON document, a portal answer.

    Returns the properties that were built and the records that were skipped.
    """
    properties: list[Property] = []
    errors: list[str] = []
    for record in records:
        try:
            if is_missing(record.get("source_url")):
                record["source_url"] = source_name
            if is_missing(record.get("source_platform")):
                record["source_platform"] = source_type
            properties.append(Property(**record))
        except Exception as e:
            record_id = record.get("id", record.get("title", "unknown"))
            logger.warning(
                "Skipped invalid property record during import",
                extra={
                    "record_id": str(record_id)[:50],
                    "error_type": type(e).__name__,
                    "error": str(e)[:200],
                },
            )
            errors.append(f"Record {record_id}: {type(e).__name__}")
    return properties, errors


def load_properties(
    source: str,
    *,
    sheet_name: Optional[str] = None,
    header_row: int = 0,
    max_rows: Optional[int] = None,
    source_name: Optional[str] = None,
    source_type: Optional[str] = None,
) -> tuple[list[Property], list[str]]:
    """Read a CSV or Excel file (a path or an http(s) URL) into properties.

    This is the chain the admin upload endpoint uses: the loader reads the
    sheet, the shared normalization formats it, and every record becomes a
    Property. The bulk-job path used to import a module that does not exist
    (``data.loaders``) and to call the loaders with keyword arguments they do
    not accept, so the route raised ImportError the moment a job ran.

    Returns the properties that were read and the records that were skipped.
    """
    from data.csv_loader import DataLoaderCsv
    from data.excel_loader import ExcelDataLoader

    suffix = source_suffix(source)
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(
            f"unsupported file type '{suffix}' - the import reads {sorted(SUPPORTED_SUFFIXES)}"
        )

    if suffix in EXCEL_SUFFIXES:
        loader = ExcelDataLoader(
            source,
            sheet_name=sheet_name,
            header_row=header_row,
            max_rows=max_rows,
        )
        df = loader.load_normalized()
    else:
        csv_loader = DataLoaderCsv(source)
        df = csv_loader.load_format_df(csv_loader.load_df(), rows_count=max_rows)

    return properties_from_records(
        df.to_dict(orient="records"),
        source_name=source_name,
        source_type=source_type,
    )


def save_imported_properties(
    properties: list[Property],
    source_name: Optional[str],
    source_type: Optional[str],
    refresh: bool = False,
) -> int:
    """Add the imported properties to the cached collection.

    The cache is what ``/admin/reindex`` re-indexes into the collection the
    product reads, so an import that did not write here would leave the
    product showing rows the import never brought in.

    The collection is a set of listings, not a log of imports: a listing that
    is already in it - one that carries an id - is left as it is, and the
    one that came in is not added beside it. The vector store holds the same
    rule (it skips an id it already has), so the cache and the store carry
    the same listings with the same data; a cache that replaced a listing the
    store kept would make a reindex show something the product never showed.
    A listing without an id cannot be recognised, so it is added beside the
    others.

    The catalogue is keyed by id, the way the vector store is: a listing of
    another source that carries the same id is the same listing of the
    catalogue, and the one that was there first stays.

    A source of record is the exception. The register publishes the prices
    people paid, and the starosta corrects a deed where it stands, so the
    register publishes the same flat again with the price it was registered
    under. A source that is of record therefore refreshes the listing it
    already published: the newer listing takes the place of the one that was
    there, under the same id, so the catalogue says what the register says.
    The number that comes back is still the number of listings that were not
    there before - a listing that was refreshed is not a new listing.

    Returns the number of properties that were added to the collection - the
    ones the collection did not hold yet.

    The number is the catalogue's own answer, and the cache is the
    catalogue's record: the cache is what a reindex re-indexes, so it knows
    what the catalogue held before the sync and what the sync added to it.
    The count is therefore the same in a deployment that restarted since the
    last sync - it comes from the cache and not from the memory of the
    process.
    """
    existing = load_collection()
    merged = list(existing.properties) if existing else []

    # Where the catalogue holds a listing: the id of the listing is its key,
    # so the place of a listing is looked up once and not looked for again.
    positions = {prop.id: index for index, prop in enumerate(merged) if prop.id}
    known = set(positions)

    added = 0
    seen: set[str] = set()
    for prop in properties:
        if prop.id and prop.id in seen:
            # The same listing came in twice. The register reads its sales
            # most recent first, so the first one of the two is the listing
            # and the second one is the same listing again.
            continue
        if prop.id:
            seen.add(prop.id)
        if prop.id and prop.id in known:
            # The catalogue holds this listing already. A source of record
            # publishes the newer listing in its place; every other source
            # leaves the listing as it is.
            if refresh:
                merged[positions[prop.id]] = prop
            continue
        if prop.id:
            known.add(prop.id)
            positions[prop.id] = len(merged)
        merged.append(prop)
        added += 1

    save_collection(
        PropertyCollection(
            properties=merged,
            total_count=len(merged),
            source=source_name,
            source_type=source_type,
        )
    )
    return added
