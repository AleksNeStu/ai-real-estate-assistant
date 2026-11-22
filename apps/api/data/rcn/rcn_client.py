"""Client for the Rejestr Cen Nieruchomości (RCN) GeoParquet exports.

Główny Urząd Geodezji i Kartografii publishes the register as one GeoParquet
file per voivodeship, refreshed weekly:

    .../PARQUET/<TERYT>_transakcje_ceny_lokale.parquet

``TERYT`` is the two-digit voivodeship code (02 = dolnośląskie, 12 = małopolskie,
14 = mazowieckie, 22 = pomorskie, 28 = wielkopolskie). The files carry every
notarial deed the starostas registered in that voivodeship, with the price, the
area, the number of rooms, the floor, the deed date and the notary's name.

The download is unconditional and free of charge: no key, no licence, no terms
to accept. The only cost is the bandwidth, so the file is cached on disk and
re-downloaded only when GUGiK publishes a newer one.
"""

import logging
import shutil
from datetime import date, datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Iterator, Optional

if TYPE_CHECKING:
    # The models are imported inside the functions that need them, so the
    # client stays importable without the whole data package; the type is
    # still known to the checker.
    from data.rcn.rcn_models import RCNTransaction  # pragma: no cover - type only

import requests

logger = logging.getLogger(__name__)

RCN_EXPORT_URL = "https://opendata.geoportal.gov.pl/InneDane/latest_exports/rcn_transakcje_ceny"

# The voivodeships the demo cities live in. GUGiK names them by TERYT code.
RCN_VOIVODESHIPS: dict[str, str] = {
    "02": "dolnoslaskie",
    "12": "malopolskie",
    "14": "mazowieckie",
    "22": "pomorskie",
    "28": "wielkopolskie",
}

# A flat, not a garage, a shop or a plot.
UNIT_PROPERTY_KIND = "nieruchomoscLokalowa"
RESIDENTIAL_FUNCTION = "mieszkalna"

# The register carries whole buildings and land as well; a flat's usable area
# outside this band is a data error, not a home.
MIN_AREA_SQM = 15.0
MAX_AREA_SQM = 300.0

# Rows dated before the register existed are artefacts, not transactions.
EARLIEST_YEAR = 2000

DEFAULT_CACHE_DIR = Path("cache/rcn")
DOWNLOAD_TIMEOUT_SECONDS = 300
USER_AGENT = "ai-real-estate-assistant/5.4 (RCN client; open-source property assistant)"

# The columns of an export this client reads. An export that lacks one of them
# is still read — the register's own id is the only column that was not
# always there.
EXPORT_COLUMNS = [
    "gid",
    "tran_lokalny_id_iip",
    "teryt",
    "tran_cena_brutto",
    "dok_data",
    "dok_oznaczenie",
    "dok_tworca",
    "tran_rodzaj_rynku",
    "nier_rodzaj",
    "lok_funkcja",
    "lok_pow_uzyt",
    "lok_liczba_izb",
    "lok_nr_kond",
    "lok_cena_brutto",
    "lok_adres",
    "geometry_bbox",
]

_ADDRESS_KEYS = {
    "MSC": "city",
    "UL": "street",
    "NR_PORZ": "number",
}


class RcnExportError(RuntimeError):
    """The export could not be fetched or read."""


def parse_rcn_address(raw: Optional[str]) -> Optional[dict[str, str]]:
    """Split the register's packed address into its parts.

    ``"MSC:KRAKÓW;UL:RACIBORSKA;NR_PORZ:17"`` becomes
    ``{"city": "KRAKÓW", "street": "RACIBORSKA", "number": "17"}``.

    The register is not consistent about which parts it carries — a plot has no
    street and a village address has no number — so every part is optional and
    an address with nothing readable in it is rejected rather than guessed at.
    """
    if not raw or not isinstance(raw, str):
        return None

    parts: dict[str, str] = {}
    for chunk in raw.split(";"):
        if ":" not in chunk:
            continue
        key, _, value = chunk.partition(":")
        field = _ADDRESS_KEYS.get(key.strip().upper())
        if field and value.strip():
            parts[field] = value.strip()

    if not parts.get("street"):
        return None
    return parts


def export_url(teryt_code: str) -> str:
    """The GeoParquet URL of one voivodeship's flats."""
    return f"{RCN_EXPORT_URL}/PARQUET/{teryt_code}_transakcje_ceny_lokale.parquet"


def _remote_timestamp(url: str) -> Optional[datetime]:
    """When the publisher last wrote this file, or None if it cannot be read."""
    try:
        response = requests.head(url, timeout=30, allow_redirects=True)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("RCN export HEAD failed for %s: %s", url, exc)
        return None

    last_modified = response.headers.get("Last-Modified")
    if not last_modified:
        return None
    try:
        return datetime.strptime(last_modified, "%a, %d %b %Y %H:%M:%S %Z").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        logger.warning("RCN export carries an unreadable Last-Modified: %r", last_modified)
        return None


def download_export(
    teryt_code: str,
    cache_dir: Optional[Path] = None,
    force: bool = False,
) -> Path:
    """Fetch a voivodeship's export, reusing the cached copy when it is current.

    The publisher writes a new file whenever the starostas registers a new
    deed, so the cached copy is compared against the remote timestamp before
    anything is downloaded.
    """
    target_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{teryt_code}_transakcje_ceny_lokale.parquet"

    url = export_url(teryt_code)
    remote = None if force else _remote_timestamp(url)

    if target.exists() and remote is not None:
        local = datetime.fromtimestamp(target.stat().st_mtime, tz=timezone.utc)
        if local >= remote:
            logger.info("RCN export for %s is current (%s)", teryt_code, target)
            return target

    logger.info("Downloading the RCN export for %s: %s", teryt_code, url)
    try:
        with requests.get(url, stream=True, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
            response.raise_for_status()
            with target.open("wb") as handle:
                shutil.copyfileobj(response.raw, handle)
    except requests.RequestException as exc:
        raise RcnExportError(f"Could not download the RCN export for {teryt_code}: {exc}") from exc

    if remote is not None:
        timestamp = remote.timestamp()
        import os

        os.utime(target, (timestamp, timestamp))
    return target


def _number(value) -> Optional[float]:
    """The number a cell holds, or None when the cell holds nothing.

    An empty column in a parquet file arrives as NaN, which is a float and
    compares false against zero, so it has to be recognised explicitly.
    """
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:  # NaN
        return None
    return number


def _row_to_transaction(row: dict) -> Optional["RCNTransaction"]:
    """Turn one parquet row into an ``RCNTransaction``, or None if it is not one."""
    from data.rcn.rcn_models import RCNAddress, RCNTransaction

    address_parts = parse_rcn_address(row.get("lok_adres"))
    if not address_parts:
        return None

    area = _number(row.get("lok_pow_uzyt"))
    if area is None or not (MIN_AREA_SQM <= area <= MAX_AREA_SQM):
        return None

    price = _number(row.get("lok_cena_brutto"))
    if price is None:
        # The price of the flat itself is missing for some deeds; the price of
        # the whole transaction is the next best thing.
        price = _number(row.get("tran_cena_brutto"))
    if price is None or price <= 0:
        return None

    deed_date = row.get("dok_data")
    if deed_date is None:
        return None
    if isinstance(deed_date, datetime):
        deed_date = deed_date.date()
    if not isinstance(deed_date, date) or deed_date.year < EARLIEST_YEAR:
        return None

    rooms = _number(row.get("lok_liczba_izb"))
    floor = _number(row.get("lok_nr_kond"))

    x = y = None
    bbox = row.get("geometry_bbox")
    if isinstance(bbox, dict):
        xmin = _number(bbox.get("xmin"))
        ymin = _number(bbox.get("ymin"))
        xmax = _number(bbox.get("xmax"))
        ymax = _number(bbox.get("ymax"))
        if xmin is not None and xmax is not None:
            x = (xmin + xmax) / 2
        if ymin is not None and ymax is not None:
            y = (ymin + ymax) / 2

    return RCNTransaction(
        external_id=str(row.get("gid") or ""),
        teryt=str(row.get("teryt") or ""),
        address=RCNAddress(
            city=address_parts.get("city", ""),
            street=address_parts["street"],
            number=address_parts.get("number", ""),
        ),
        area_sqm=area,
        price=price,
        transaction_date=deed_date,
        market=str(row.get("tran_rodzaj_rynku") or ""),
        rooms=int(rooms) if rooms is not None and rooms > 0 else None,
        floor=int(floor) if floor is not None and floor > 0 else None,
        deed_reference=str(row.get("dok_oznaczenie") or ""),
        notary=str(row.get("dok_tworca") or ""),
        x=x,
        y=y,
        transaction_id=str(row.get("tran_lokalny_id_iip") or ""),
    )


def read_export(
    path: Path,
    since: Optional[date] = None,
) -> Iterator["RCNTransaction"]:
    """Read a downloaded export and yield the flats it holds.

    ``since`` drops the deeds older than the given date — the register keeps
    every transaction ever registered, and a valuation only cares about the
    recent ones.
    """
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:  # pragma: no cover - the dependency is declared
        raise RcnExportError("pyarrow is required to read the RCN exports") from exc

    try:
        # The register's own id (``gid``) names one flat; an export without it
        # is still read, and the ingest falls back to a digest of the deed.
        available = set(pq.read_schema(path).names)
        columns = [column for column in EXPORT_COLUMNS if column in available]
        table = pq.read_table(path, columns=columns)
    except Exception as exc:
        raise RcnExportError(f"Could not read the RCN export {path}: {exc}") from exc

    frame = table.to_pandas()
    residential = frame[
        (frame["nier_rodzaj"] == UNIT_PROPERTY_KIND)
        & (frame["lok_funkcja"] == RESIDENTIAL_FUNCTION)
    ]
    if since is not None:
        residential = residential[residential["dok_data"] >= since]

    for row in residential.to_dict("records"):
        transaction = _row_to_transaction(row)
        if transaction is not None:
            yield transaction


def fetch_transactions(
    teryt_code: str,
    since: Optional[date] = None,
    cache_dir: Optional[Path] = None,
    force: bool = False,
) -> list:
    """Download (if needed) and read one voivodeship's flats."""
    path = download_export(teryt_code, cache_dir=cache_dir, force=force)
    return list(read_export(path, since=since))
