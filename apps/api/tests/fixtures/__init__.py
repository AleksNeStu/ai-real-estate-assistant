"""Test fixtures for the neighbourhood data adapters and the register's export."""

from datetime import date
from pathlib import Path
from typing import Any

# The columns the official register's export carries. The recorded answers
# are kept as the rows the publisher sent, and the export is the parquet
# those rows are written into - the same file the register itself serves.
RCN_EXPORT_COLUMNS = [
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


def recorded_rcn_export(rows: list[dict[str, Any]], path: Path) -> Path:
    """Write the recorded answer of the register as the parquet it sends.

    The rows are the ones the publisher sent; the file is the one the
    register serves. Everything that reads the export - the parse, the
    ingest, the catalogue - reads this file, so only the network is out of
    the test.

    PyArrow is imported here and not at the top of the module: the fixture
    is the only thing that needs it, and a machine without it should skip
    the test that uses it rather than fail to collect the whole suite.
    """
    import pyarrow as pa
    import pyarrow.parquet as pq

    values: dict[str, list] = {}
    for column in RCN_EXPORT_COLUMNS:
        if column == "dok_data":
            values[column] = [date.fromisoformat(row["dok_data"]) for row in rows]
        else:
            values[column] = [row.get(column) for row in rows]
    pq.write_table(pa.table(values), path)
    return path
