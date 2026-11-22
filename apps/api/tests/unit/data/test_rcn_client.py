"""Tests for the RCN (Rejestr Cen Nieruchomości) client.

The register is read from the GeoParquet files GUGiK publishes, so the tests
read a real parquet file written by the test itself rather than a stubbed
reader — the parsing, the filtering and the address format are the contract.
"""

import io
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

import pytest
import requests

import data.rcn.rcn_client as rcn_client
from data.rcn.rcn_client import (
    RCN_VOIVODESHIPS,
    export_url,
    parse_rcn_address,
    read_export,
)

pytest.importorskip("pyarrow")
import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

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


def _row(
    external_id="a1",
    gid: Optional[str] = None,
    teryt="1261",
    tran_price: Optional[float] = 640000.0,
    deed_date=date(2026, 3, 27),
    market="rynekWtorny",
    kind="nieruchomoscLokalowa",
    function="mieszkalna",
    area=50.0,
    rooms=2,
    floor=3,
    price: Optional[float] = 640000.0,
    address="MSC:KRAKÓW;UL:TOPOLOWA;NR_PORZ:47",
):
    return {
        "gid": gid or f"gid-{external_id}",
        "tran_lokalny_id_iip": external_id,
        "teryt": teryt,
        "tran_cena_brutto": tran_price,
        "dok_data": deed_date,
        "dok_oznaczenie": "1234/2026",
        "dok_tworca": "MAREK HRYMAK",
        "tran_rodzaj_rynku": market,
        "nier_rodzaj": kind,
        "lok_funkcja": function,
        "lok_pow_uzyt": area,
        "lok_liczba_izb": rooms,
        "lok_nr_kond": floor,
        "lok_cena_brutto": price,
        "lok_adres": address,
        "geometry_bbox": {
            "xmin": 651000.0,
            "ymin": 561000.0,
            "xmax": 651000.0,
            "ymax": 561000.0,
        },
    }


def _write_export(path: Path, rows: list[dict]) -> Path:
    table = pa.table({column: [row[column] for row in rows] for column in EXPORT_COLUMNS})
    pq.write_table(table, path)
    return path


class TestParseAddress:
    def test_reads_the_packed_format(self):
        parsed = parse_rcn_address("MSC:KRAKÓW;UL:RACIBORSKA;NR_PORZ:17")
        assert parsed == {"city": "KRAKÓW", "street": "RACIBORSKA", "number": "17"}

    def test_street_is_required(self):
        assert parse_rcn_address("MSC:KRAKÓW;NR_PORZ:17") is None
        assert parse_rcn_address("") is None
        assert parse_rcn_address(None) is None

    def test_keeps_what_is_there(self):
        parsed = parse_rcn_address("MSC:KRAKÓW;UL:OSIEDLE SZKOLNE")
        assert parsed is not None
        assert parsed["street"] == "OSIEDLE SZKOLNE"
        assert "number" not in parsed


class TestExportUrl:
    def test_addresses_one_voivodeship(self):
        assert export_url("12").endswith("/PARQUET/12_transakcje_ceny_lokale.parquet")

    def test_serves_the_demo_cities(self):
        assert set(RCN_VOIVODESHIPS.values()) == {
            "dolnoslaskie",
            "malopolskie",
            "mazowieckie",
            "pomorskie",
            "wielkopolskie",
        }


class TestReadExport:
    def test_reads_a_sold_flat(self, tmp_path):
        path = _write_export(tmp_path / "12.parquet", [_row()])

        transactions = list(read_export(path))

        assert len(transactions) == 1
        transaction = transactions[0]
        assert transaction.address.city == "KRAKÓW"
        assert transaction.address.street == "TOPOLOWA"
        assert transaction.address.number == "47"
        assert transaction.area_sqm == 50.0
        assert transaction.price == 640000.0
        assert transaction.transaction_date == date(2026, 3, 27)
        assert transaction.market == "rynekWtorny"
        assert transaction.rooms == 2
        assert transaction.floor == 3
        assert transaction.notary == "MAREK HRYMAK"
        assert transaction.currency == "PLN"
        assert transaction.price_per_sqm == 12800.0

    def test_keeps_the_register_id_and_the_transaction_id_apart(self, tmp_path):
        # One deed may sell two flats in one building, so the id that names a
        # flat and the id that names the transaction are not the same.
        path = _write_export(tmp_path / "12.parquet", [_row(external_id="deed-1", gid="flat-1")])

        transaction = list(read_export(path))[0]

        assert transaction.external_id == "flat-1"
        assert transaction.transaction_id == "deed-1"

    def test_skips_what_is_not_a_flat(self, tmp_path):
        rows = [
            _row(external_id="flat"),
            _row(external_id="garage", function="garaz"),
            _row(external_id="plot", kind="nieruchomoscGruntowaZabudowana"),
            _row(external_id="shop", function="handlowoUslugowa"),
            _row(external_id="office", function="biurowa"),
        ]
        path = _write_export(tmp_path / "12.parquet", rows)

        transactions = list(read_export(path))

        assert [t.transaction_id for t in transactions] == ["flat"]

    def test_skips_an_impossible_area(self, tmp_path):
        rows = [
            _row(external_id="ok", area=50.0),
            _row(external_id="tiny", area=3.0),
            _row(external_id="huge", area=681800.0),
        ]
        path = _write_export(tmp_path / "12.parquet", rows)

        assert [t.transaction_id for t in list(read_export(path))] == ["ok"]

    def test_falls_back_to_the_transaction_price(self, tmp_path):
        path = _write_export(tmp_path / "12.parquet", [_row(price=None, tran_price=500000.0)])

        transactions = list(read_export(path))

        assert transactions[0].price == 500000.0

    def test_skips_a_row_without_a_price(self, tmp_path):
        path = _write_export(tmp_path / "12.parquet", [_row(price=None, tran_price=None)])

        assert list(read_export(path)) == []

    def test_skips_a_row_without_an_address(self, tmp_path):
        path = _write_export(tmp_path / "12.parquet", [_row(address="")])

        assert list(read_export(path)) == []

    def test_drops_the_deeds_older_than_the_window(self, tmp_path):
        rows = [
            _row(external_id="old", deed_date=date(2019, 1, 1)),
            _row(external_id="new", deed_date=date(2026, 1, 1)),
        ]
        path = _write_export(tmp_path / "12.parquet", rows)

        transactions = list(read_export(path, since=date(2025, 1, 1)))

        assert [t.transaction_id for t in transactions] == ["new"]

    def test_reads_the_coordinates(self, tmp_path):
        path = _write_export(tmp_path / "12.parquet", [_row()])

        transaction = list(read_export(path))[0]

        assert transaction.x == pytest.approx(651000.0)
        assert transaction.y == pytest.approx(561000.0)

    def test_an_unknown_floor_is_not_a_floor(self, tmp_path):
        path = _write_export(tmp_path / "12.parquet", [_row(floor=-1)])

        assert list(read_export(path))[0].floor is None


class _FakeResponse:
    """What the publisher answers with, without the network."""

    def __init__(self, *, headers=None, content=b""):
        self.headers = headers or {}
        self.content = content
        self.raw = io.BytesIO(content)

    def raise_for_status(self):
        return None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


PUBLISHED = "Wed, 19 Nov 2026 10:00:00 GMT"


class TestTheRemoteTimestamp:
    """When the publisher last wrote the file."""

    def test_it_reads_the_publisher_timestamp(self, monkeypatch):
        monkeypatch.setattr(
            rcn_client.requests,
            "head",
            lambda *args, **kwargs: _FakeResponse(headers={"Last-Modified": PUBLISHED}),
        )

        moment = rcn_client._remote_timestamp("https://example.invalid/12.parquet")

        assert moment == datetime(2026, 11, 19, 10, 0, tzinfo=timezone.utc)

    def test_a_publisher_that_cannot_be_asked_has_no_timestamp(self, monkeypatch):
        def _unreachable(*args, **kwargs):
            raise requests.RequestException("no route to host")

        monkeypatch.setattr(rcn_client.requests, "head", _unreachable)

        assert rcn_client._remote_timestamp("https://example.invalid/12.parquet") is None

    def test_a_response_without_a_timestamp_has_none(self, monkeypatch):
        monkeypatch.setattr(rcn_client.requests, "head", lambda *a, **k: _FakeResponse())

        assert rcn_client._remote_timestamp("https://example.invalid/12.parquet") is None

    def test_an_unreadable_timestamp_is_not_a_timestamp(self, monkeypatch):
        monkeypatch.setattr(
            rcn_client.requests,
            "head",
            lambda *a, **k: _FakeResponse(headers={"Last-Modified": "yesterday-ish"}),
        )

        assert rcn_client._remote_timestamp("https://example.invalid/12.parquet") is None


class TestTheDownload:
    """Fetching the export, and the copy that is kept on disk."""

    def test_it_fetches_the_export_and_stamps_it(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            rcn_client.requests,
            "head",
            lambda *a, **k: _FakeResponse(headers={"Last-Modified": PUBLISHED}),
        )
        monkeypatch.setattr(
            rcn_client.requests,
            "get",
            lambda *a, **k: _FakeResponse(content=b"PAR1-the-export"),
        )

        target = rcn_client.download_export("12", cache_dir=tmp_path)

        assert target.read_bytes() == b"PAR1-the-export"
        # The copy is stamped with the publisher's timestamp, so the next
        # refresh knows whether it is current without asking again.
        assert target.stat().st_mtime == pytest.approx(
            datetime(2026, 11, 19, 10, 0, tzinfo=timezone.utc).timestamp()
        )

    def test_a_download_that_fails_says_so(self, monkeypatch, tmp_path):
        monkeypatch.setattr(rcn_client.requests, "head", lambda *a, **k: _FakeResponse())

        def _unreachable(*args, **kwargs):
            raise requests.RequestException("no route to host")

        monkeypatch.setattr(rcn_client.requests, "get", _unreachable)

        with pytest.raises(rcn_client.RcnExportError):
            rcn_client.download_export("12", cache_dir=tmp_path)

    def test_a_cached_copy_that_is_current_is_not_fetched_again(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            rcn_client.requests,
            "head",
            lambda *a, **k: _FakeResponse(headers={"Last-Modified": PUBLISHED}),
        )
        target = tmp_path / "12_transakcje_ceny_lokale.parquet"
        target.write_bytes(b"the-copy-we-already-have")

        def _never(*args, **kwargs):
            raise AssertionError("the copy is current, nothing should be fetched")

        monkeypatch.setattr(rcn_client.requests, "get", _never)

        assert rcn_client.download_export("12", cache_dir=tmp_path) == target


class TestOneRow:
    """The rows the register sends, and the ones it must not."""

    def test_a_row_without_a_date_is_refused(self):
        row = _row()
        row["dok_data"] = None

        assert rcn_client._row_to_transaction(row) is None

    def test_a_timestamp_is_read_as_its_day(self):
        row = _row()
        row["dok_data"] = datetime(2026, 3, 27, 14, 30)

        transaction = rcn_client._row_to_transaction(row)

        assert transaction is not None
        assert transaction.transaction_date == date(2026, 3, 27)

    def test_a_date_that_is_not_a_date_is_refused(self):
        row = _row()
        row["dok_data"] = "2026-03-27"

        assert rcn_client._row_to_transaction(row) is None

    def test_a_cell_that_is_not_a_number_is_refused(self):
        row = _row()
        row["lok_pow_uzyt"] = "not a number"

        assert rcn_client._row_to_transaction(row) is None

    def test_a_file_that_is_not_an_export_is_refused(self, tmp_path):
        broken = tmp_path / "broken.parquet"
        broken.write_bytes(b"this is not a parquet file")

        with pytest.raises(rcn_client.RcnExportError):
            list(rcn_client.read_export(broken))


# The live register is read once by the integration suite
# (tests/integration/test_rcn_register_slice.py): it is a network test, not
# a unit test, and it skips when the network is not there.
