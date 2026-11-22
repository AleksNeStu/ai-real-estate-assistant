"""Tests for valuing a flat through the stored register.

The records behind these tests are a recorded answer of the real service, so
the provider is exercised against the numbers Poland's notaries actually
wrote down — not against an invented market.
"""

import json
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import select

from agents.services.valuation import (
    RcnValuationProvider,
    RegisterContext,
    read_register_context,
    read_register_context_sync,
)
from data.rcn.rcn_client import read_export
from data.rcn.rcn_ingest import store_transactions
from db.models import PropertyTransaction

pytest.importorskip("pyarrow")
import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "rcn" / "krakow_sample.json"

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


def _recorded_transactions(tmp_path: Path):
    rows = json.loads(FIXTURE.read_text(encoding="utf-8"))
    values: dict[str, list] = {}
    for column in EXPORT_COLUMNS:
        if column == "dok_data":
            values[column] = [date.fromisoformat(row["dok_data"]) for row in rows]
        else:
            values[column] = [row.get(column) for row in rows]
    path = tmp_path / "12.parquet"
    pq.write_table(pa.table(values), path)
    return list(read_export(path))


@pytest.fixture
async def stored_register(db_session, tmp_path):
    """The recorded register, stored the way the ingest stores it."""
    transactions = _recorded_transactions(tmp_path)
    await store_transactions(db_session, transactions, "https://example.invalid/12.parquet")
    return db_session


class TestRcnValuationProvider:
    async def test_it_values_an_address_from_the_registered_sales(self, stored_register):
        provider = RcnValuationProvider(stored_register)

        outcome = await provider.outcome({"city": "Kraków", "street": "Topolowa", "area_sqm": 50})

        assert outcome.estimated_value is not None
        assert outcome.estimated_value == pytest.approx(710732.05, rel=1e-4)
        assert outcome.price_per_sqm_median == pytest.approx(14214.64, rel=1e-4)
        assert outcome.sample_size == 15
        assert outcome.confidence == "medium"
        assert outcome.source == "rcn"
        assert outcome.comparison_area == "Topolowa, Kraków"

    async def test_the_result_says_what_it_rests_on(self, stored_register):
        provider = RcnValuationProvider(stored_register)

        outcome = await provider.outcome({"city": "Kraków", "area_sqm": 50})

        assert outcome.period_start is not None and outcome.period_end is not None
        assert any("registered sale" in note for note in outcome.notes)
        assert outcome.comparables
        assert all(comparable["deed_reference"] for comparable in outcome.comparables)

    async def test_a_street_with_too_little_trading_falls_back_to_the_city(self, stored_register):
        provider = RcnValuationProvider(stored_register)

        outcome = await provider.outcome({"city": "Kraków", "street": "Topolowa", "area_sqm": 50})

        assert any("fell back to the whole city" in note for note in outcome.notes)

    async def test_an_address_nobody_sold_on_is_told_so(self, stored_register):
        provider = RcnValuationProvider(stored_register)

        outcome = await provider.outcome(
            {"city": "Kraków", "street": "ULICA KTÓREJ NIE MA", "area_sqm": 50}
        )

        assert outcome.estimated_value is not None
        assert any("fell back to the whole city" in note for note in outcome.notes)

    async def test_a_city_without_a_name_is_not_valued(self, stored_register):
        provider = RcnValuationProvider(stored_register)

        outcome = await provider.outcome({"area_sqm": 50})

        assert outcome.estimated_value is None
        assert outcome.notes

    async def test_a_city_that_sold_nothing_is_not_valued(self, stored_register):
        provider = RcnValuationProvider(stored_register)

        outcome = await provider.outcome({"city": "Gdańsk", "area_sqm": 50})

        assert outcome.estimated_value is None
        assert outcome.sample_size == 0


class TestTheRegisterContext:
    """What the register says about a place: its prices and their movement."""

    async def test_it_reads_the_prices_and_their_movement(self, stored_register):
        provider = RcnValuationProvider(stored_register)

        context = await provider.context("Kraków")

        assert context.has_data
        assert context.median_price_per_sqm is not None
        assert context.sample_size > 0
        assert context.comparison_area == "Kraków"
        # The rate is measured, not assumed: the recorded prices moved.
        assert context.trend is not None
        assert context.trend.annual_rate > 0
        assert context.period_start is not None and context.period_end is not None

    async def test_a_street_that_is_too_thin_is_measured_on_the_city(self, stored_register):
        provider = RcnValuationProvider(stored_register)

        context = await provider.context("Kraków", "Topolowa")

        assert context.has_data
        assert context.trend is not None

    async def test_a_place_nobody_sold_in_reads_as_empty(self, stored_register):
        provider = RcnValuationProvider(stored_register)

        context = await provider.context("Gdańsk")

        assert not context.has_data
        assert context.median_price_per_sqm is None
        assert context.trend is None


class TestTheRegisterReaders:
    """The two ways a caller reads the register."""

    async def test_a_place_without_a_name_reads_as_nothing(self):
        assert await read_register_context("   ") is None
        assert read_register_context_sync("   ") is None

    async def test_it_reads_the_register_in_a_session_of_its_own(
        self, monkeypatch, stored_register
    ):
        @asynccontextmanager
        async def _session():
            yield stored_register

        monkeypatch.setattr("db.database.standalone_session", _session)

        context = await read_register_context("Kraków")

        assert context is not None
        assert context.has_data
        assert context.median_price_per_sqm is not None

    def test_it_reads_the_register_from_sync_code(self, monkeypatch):
        async def _fake(city: str, _street: str = ""):
            return RegisterContext(
                median_price_per_sqm=14316.0,
                sample_size=312,
                comparison_area=city,
            )

        monkeypatch.setattr("agents.services.valuation.read_register_context", _fake)

        context = read_register_context_sync("Kraków")

        assert context is not None
        assert context.median_price_per_sqm == 14316.0


class TestStoredRegister:
    async def test_the_stored_rows_keep_the_register_numbers(self, stored_register):
        result = await stored_register.execute(select(PropertyTransaction).limit(5))
        rows = result.scalars().all()

        assert rows
        assert all(row.currency == "PLN" for row in rows)
        assert all(row.price_brutto > 0 for row in rows)
        assert all(row.source == "rcn" for row in rows)
        assert all(row.source_url for row in rows)
