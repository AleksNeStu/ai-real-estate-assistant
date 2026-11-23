"""Tests for bringing the official price register into the database.

The fixture is a recorded answer of the real service — 55 flats that were
registered in Kraków — so the test runs against the shape the publisher
actually sends, not against an invented one.
"""

import json
import sys
from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import Path

import pytest
from sqlalchemy import func, select

import data.rcn.rcn_ingest as rcn_ingest
from data.rcn.rcn_client import RCN_VOIVODESHIPS, read_export
from data.rcn.rcn_ingest import external_id_for, store_transactions, to_row
from data.rcn.rcn_models import RCNAddress, RCNTransaction
from db.models import PropertyTransaction
from db.property_transaction_repo import transactions_for

pytest.importorskip("pyarrow")
import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "rcn" / "krakow_sample.json"
POZNAN_FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "rcn" / "poznan_sample.json"

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


def _recorded_rows() -> list[dict]:
    rows: list[dict] = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return rows


def _write_export(path: Path, rows: list[dict]) -> Path:
    """Write the recorded rows as the parquet the publisher sends."""
    values: dict[str, list] = {}
    for column in EXPORT_COLUMNS:
        if column == "dok_data":
            values[column] = [date.fromisoformat(row["dok_data"]) for row in rows]
        else:
            values[column] = [row.get(column) for row in rows]
    pq.write_table(pa.table(values), path)
    return path


def _recorded_transactions(tmp_path: Path) -> list[RCNTransaction]:
    return list(read_export(_write_export(tmp_path / "12.parquet", _recorded_rows())))


def _recorded_poznan_transactions(tmp_path: Path) -> list[RCNTransaction]:
    """The recorded sales of a municipality the register publishes without a street."""
    rows = json.loads(POZNAN_FIXTURE.read_text(encoding="utf-8"))
    return list(read_export(_write_export(tmp_path / "30.parquet", rows)))


class TestRecordedRegister:
    """The recorded answer of the real service."""

    def test_it_reads_the_recorded_sales(self, tmp_path):
        transactions = _recorded_transactions(tmp_path)

        # 54 of the 55 recorded rows: the register also lists a 12 m² flat on
        # Osiedle Kolorowe, which is too small to be a flat and is dropped.
        assert len(transactions) == 54
        assert all(t.address.city == "KRAKÓW" for t in transactions)
        assert all(t.price > 0 for t in transactions)
        assert all(t.area_sqm >= 15 for t in transactions)

    def test_every_flat_keeps_its_own_id(self, tmp_path):
        transactions = _recorded_transactions(tmp_path)

        assert len({t.external_id for t in transactions}) == len(transactions)


class TestAMunicipalityWithoutAddresses:
    """A sale the register published without a street.

    The row is stored with the city the code of the municipality names and
    with no street: a read of the city finds the sale, a read of a street
    does not.
    """

    def test_the_row_is_stored_with_the_city_and_no_street(self, tmp_path):
        transaction = _recorded_poznan_transactions(tmp_path)[0]

        row = to_row(transaction, "https://example.invalid/30.parquet")

        assert row.city == "POZNAŃ"
        assert row.city_norm == "POZNAN"
        assert row.street == ""
        assert row.street_norm == ""
        assert row.teryt == "3064"

    async def test_the_city_read_finds_the_sale_and_a_street_read_does_not(
        self, db_session, tmp_path
    ):
        transactions = _recorded_poznan_transactions(tmp_path)
        await store_transactions(db_session, transactions, "https://example.invalid/30.parquet")

        city = await transactions_for(db_session, "POZNAN")
        street = await transactions_for(db_session, "POZNAN", "DŁUGA")

        assert len(city) == len(transactions)
        assert street == []


class TestExternalId:
    def test_the_register_feature_id_names_the_flat(self):
        transaction = RCNTransaction(
            external_id="11562464",
            teryt="1262",
            address=RCNAddress(city="NOWY SĄCZ", street="BANACHA", number="11K"),
            area_sqm=78.1,
            price=420680.0,
            transaction_date=date(2025, 6, 2),
        )

        assert external_id_for(transaction) == "11562464"

    def test_two_flats_of_one_deed_are_two_sales(self):
        first = RCNTransaction(
            external_id="",
            teryt="1262",
            address=RCNAddress(city="NOWY SĄCZ", street="BANACHA", number="11K"),
            area_sqm=78.1,
            price=420680.0,
            transaction_date=date(2025, 6, 2),
            transaction_id="deed-1",
        )
        second = RCNTransaction(
            external_id="",
            teryt="1262",
            address=RCNAddress(city="NOWY SĄCZ", street="BANACHA", number="11K"),
            area_sqm=73.2,
            price=420680.0,
            transaction_date=date(2025, 6, 2),
            transaction_id="deed-1",
        )

        assert external_id_for(first) != external_id_for(second)

    def test_a_row_without_an_id_is_keyed_by_what_it_says(self):
        transaction = RCNTransaction(
            external_id="",
            teryt="1262",
            address=RCNAddress(city="NOWY SĄCZ", street="BANACHA", number="11K"),
            area_sqm=78.1,
            price=420680.0,
            transaction_date=date(2025, 6, 2),
        )

        assert external_id_for(transaction).startswith("sha256:")


class TestStoreTransactions:
    async def test_it_stores_the_sales_and_remembers_them(self, db_session, tmp_path):
        transactions = _recorded_transactions(tmp_path)

        inserted, known = await store_transactions(
            db_session, transactions, "https://example.invalid/12.parquet"
        )

        assert inserted == 54
        assert known == 0

        stored = await db_session.execute(select(func.count(PropertyTransaction.id)))
        assert stored.scalar_one() == 54

        # A second pass finds nothing new to write.
        inserted_again, known_again = await store_transactions(
            db_session, transactions, "https://example.invalid/12.parquet"
        )
        assert inserted_again == 0
        assert known_again == 54

    async def test_the_row_keeps_the_names_as_the_register_wrote_them(self, db_session, tmp_path):
        transactions = _recorded_transactions(tmp_path)
        await store_transactions(db_session, transactions, "https://example.invalid/12.parquet")

        result = await db_session.execute(
            select(PropertyTransaction).where(PropertyTransaction.street == "TOPOLOWA")
        )
        streets = result.scalars().all()

        assert streets
        assert all(row.city == "KRAKÓW" for row in streets)
        assert all(row.city_norm == "KRAKOW" for row in streets)
        assert all(row.street_norm == "TOPOLOWA" for row in streets)
        assert all(row.source == "rcn" for row in streets)
        assert all(row.currency == "PLN" for row in streets)


class TestToRow:
    def test_it_keeps_the_source_and_the_position(self):
        transaction = RCNTransaction(
            external_id="1",
            teryt="1261",
            address=RCNAddress(city="KRAKÓW", street="TOPOLOWA", number="47"),
            area_sqm=50.0,
            price=650000.0,
            transaction_date=date(2026, 3, 27),
            market="rynekWtorny",
            rooms=2,
            floor=3,
            deed_reference="1234/2026",
            x=651000.0,
            y=561000.0,
            transaction_id="deed-9",
        )

        row = to_row(transaction, "https://example.invalid/12.parquet")

        assert row.external_id == "1"
        assert row.transaction_id == "deed-9"
        assert row.price_brutto == 650000.0
        assert row.source == "rcn"
        assert row.source_url == "https://example.invalid/12.parquet"
        assert row.x_2180 == 651000.0
        assert row.y_2180 == 561000.0


class TestDefaultSince:
    """How far back the register is worth keeping."""

    def test_it_keeps_six_years_of_deeds(self):
        assert rcn_ingest.default_since() == date.today() - timedelta(days=365 * 6 + 1)

    def test_the_window_can_be_chosen(self):
        assert rcn_ingest.default_since(2) == date.today() - timedelta(days=365 * 2 + 1)


class TestIngestVoivodeship:
    """One refresh of one voivodeship's export."""

    async def test_it_reads_the_export_and_writes_what_is_new(
        self, monkeypatch, db_session, tmp_path
    ):
        transactions = _recorded_transactions(tmp_path)
        monkeypatch.setattr(rcn_ingest, "fetch_transactions", lambda *a, **k: transactions)

        report = await rcn_ingest.ingest_voivodeship(db_session, "12", cache_dir=tmp_path)

        assert report.voivodeship == "12"
        assert report.fetched == len(transactions)
        assert report.inserted == len(transactions)
        assert report.known == 0
        assert report.source_url.endswith("12_transakcje_ceny_lokale.parquet")

    async def test_a_second_refresh_writes_nothing_new(self, monkeypatch, db_session, tmp_path):
        transactions = _recorded_transactions(tmp_path)
        monkeypatch.setattr(rcn_ingest, "fetch_transactions", lambda *a, **k: transactions)
        await rcn_ingest.ingest_voivodeship(db_session, "12", cache_dir=tmp_path)

        report = await rcn_ingest.ingest_voivodeship(db_session, "12", cache_dir=tmp_path)

        assert report.inserted == 0
        assert report.known == len(transactions)


class TestIngestDemoVoivodeships:
    async def test_it_refreshes_the_voivodeships_it_was_given(
        self, monkeypatch, db_session, tmp_path
    ):
        monkeypatch.setattr(rcn_ingest, "fetch_transactions", lambda *a, **k: [])

        reports = await rcn_ingest.ingest_demo_voivodeships(
            db_session, voivodeships=["12", "14"], cache_dir=tmp_path
        )

        assert [report.voivodeship for report in reports] == ["12", "14"]

    async def test_it_refreshes_every_demo_voivodeship_by_default(
        self, monkeypatch, db_session, tmp_path
    ):
        monkeypatch.setattr(rcn_ingest, "fetch_transactions", lambda *a, **k: [])

        reports = await rcn_ingest.ingest_demo_voivodeships(db_session, cache_dir=tmp_path)

        assert [report.voivodeship for report in reports] == list(RCN_VOIVODESHIPS)


class TestTheCommandLine:
    async def test_it_refreshes_and_reports(self, monkeypatch, capsys):
        @asynccontextmanager
        async def _db_context():
            yield object()

        async def _refresh(
            session, voivodeships=None, since=None, cache_dir=None, force_download=False
        ):
            return [
                rcn_ingest.IngestReport(
                    voivodeship="12",
                    fetched=10,
                    inserted=3,
                    known=7,
                    source_url="https://example.invalid/12.parquet",
                )
            ]

        monkeypatch.setattr("db.database.get_db_context", _db_context)
        monkeypatch.setattr(rcn_ingest, "ingest_demo_voivodeships", _refresh)
        monkeypatch.setattr(sys, "argv", ["rcn_ingest", "--teryt", "12", "--years", "3"])

        await rcn_ingest._run()

        assert "12: 3 written, 7 already known, 10 read" in capsys.readouterr().out
