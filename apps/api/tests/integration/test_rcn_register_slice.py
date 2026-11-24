"""The tracer bullet, end to end.

One address in Kraków goes in, the median of the prices people actually paid
comes out, and the sales it stands on come with it. The only boundary that is
replaced here is the network: the register's own recorded answer stands in
for the file the publisher sends, so the parsing, the storage, the comparison
and the answer are all the real thing.

The last test reads the live register once and skips when it is not there —
skipped, never mocked.
"""

import json
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

import pytest

import data.rcn.rcn_client as rcn_client
from agents.services.valuation import RcnValuationProvider
from data.rcn.rcn_ingest import ingest_voivodeship
from tests.fixtures import recorded_rcn_export
from tools.rcn_valuation_tool import RcnValuationTool

pytest.importorskip("pyarrow")

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "rcn" / "krakow_sample.json"
POZNAN_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "rcn" / "poznan_sample.json"


def _recorded_export(tmp_path: Path) -> Path:
    """The recorded answer of the real service, as the parquet it sends."""
    rows = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return recorded_rcn_export(rows, tmp_path / "12_transakcje_ceny_lokale.parquet")


def _recorded_poznan_export(tmp_path: Path) -> Path:
    """The recorded answer for a municipality the register does not name.

    Poznań's starosta files the sales of the city without an address, so the
    rows of the export carry no place and no street.
    """
    rows = json.loads(POZNAN_FIXTURE.read_text(encoding="utf-8"))
    return recorded_rcn_export(rows, tmp_path / "30_transakcje_ceny_lokale.parquet")


class TestTheSlice:
    async def test_an_address_is_valued_from_the_registered_sales(
        self, db_session, tmp_path, monkeypatch
    ):
        export = _recorded_export(tmp_path)
        monkeypatch.setattr(rcn_client, "download_export", lambda *a, **k: export)

        report = await ingest_voivodeship(db_session, "12", cache_dir=tmp_path)
        assert report.inserted == 54

        provider = RcnValuationProvider(db_session)
        outcome = await provider.outcome({"city": "Kraków", "street": "Topolowa", "area_sqm": 50})

        # A number, and the evidence under it.
        assert outcome.estimated_value is not None
        assert outcome.price_per_sqm_median is not None
        assert outcome.sample_size > 0
        assert outcome.comparison_area
        assert outcome.period_start is not None and outcome.period_end is not None
        assert outcome.comparables
        assert all(comparable["deed_reference"] for comparable in outcome.comparables)

    async def test_the_tool_answers_with_the_number_and_the_sales(
        self, db_session, tmp_path, monkeypatch
    ):
        export = _recorded_export(tmp_path)
        monkeypatch.setattr(rcn_client, "download_export", lambda *a, **k: export)
        await ingest_voivodeship(db_session, "12", cache_dir=tmp_path)

        @asynccontextmanager
        async def _session():
            yield db_session

        monkeypatch.setattr("db.database.standalone_session", _session)

        text = await RcnValuationTool()._arun(city="Kraków", street="Topolowa", area_sqm=50)

        assert "PLN" in text
        assert "registered sale(s)" in text
        assert "Comparison area:" in text

    async def test_a_place_nobody_sold_in_is_not_invented(self, db_session, tmp_path, monkeypatch):
        export = _recorded_export(tmp_path)
        monkeypatch.setattr(rcn_client, "download_export", lambda *a, **k: export)
        await ingest_voivodeship(db_session, "12", cache_dir=tmp_path)

        provider = RcnValuationProvider(db_session)
        outcome = await provider.outcome({"city": "Gdańsk", "area_sqm": 50})

        assert outcome.estimated_value is None
        assert outcome.notes


class TestTheCityTheRegisterDoesNotName:
    """Poznań, priced from the register like every other city.

    The starosta of the city files its sales without an address, so the code
    of the municipality is the only place those rows carry. The city is
    priced from them anyway: the price a square metre costs, the sample that
    figure is measured on, the period it covers and the sales themselves -
    and the comparison is the city, not a street.
    """

    async def test_the_city_is_priced_from_its_own_sales(self, db_session, tmp_path, monkeypatch):
        export = _recorded_poznan_export(tmp_path)
        monkeypatch.setattr(rcn_client, "download_export", lambda *a, **k: export)

        report = await ingest_voivodeship(db_session, "30", cache_dir=tmp_path)
        assert report.inserted == 55

        provider = RcnValuationProvider(db_session)
        outcome = await provider.place_outcome("Poznań")

        # The figures, and the evidence under them.
        assert outcome.has_figures
        assert outcome.median_price_per_sqm is not None
        assert outcome.comparison_area == "Poznań"
        assert outcome.sample_size > 0
        assert outcome.period_start is not None and outcome.period_end is not None
        assert outcome.registered_count is not None
        assert outcome.registered_count >= outcome.sample_size
        # The sales themselves, with the deeds the register gave them.
        assert outcome.comparables
        assert all(comparable["deed_reference"] for comparable in outcome.comparables)

    async def test_a_flat_there_is_priced_from_the_city(self, db_session, tmp_path, monkeypatch):
        export = _recorded_poznan_export(tmp_path)
        monkeypatch.setattr(rcn_client, "download_export", lambda *a, **k: export)
        await ingest_voivodeship(db_session, "30", cache_dir=tmp_path)

        provider = RcnValuationProvider(db_session)
        outcome = await provider.outcome({"city": "Poznań", "street": "Długa", "area_sqm": 50})

        # The register holds no sale of that street, so the comparison is the
        # city - and the answer says so.
        assert outcome.estimated_value is not None
        assert outcome.sample_size > 0
        assert any("city" in note.lower() for note in outcome.notes)
        assert all(comparable["deed_reference"] for comparable in outcome.comparables)


@pytest.mark.integration
@pytest.mark.requires_api
async def test_the_live_register_answers():
    """The real register, read once: a flat in Kraków with a real price."""
    try:
        transactions = rcn_client.fetch_transactions("12", since=date(2025, 1, 1))
    except Exception as exc:  # pragma: no cover - the network is not always there
        pytest.skip(f"The RCN export is not reachable: {exc}")

    assert transactions, "The live export holds no transactions"
    sample = transactions[0]
    assert sample.price > 0
    assert sample.area_sqm >= 15
    assert sample.address.street
