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
from tools.rcn_valuation_tool import RcnValuationTool

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


def _recorded_export(tmp_path: Path) -> Path:
    """The recorded answer of the real service, as the parquet it sends."""
    rows = json.loads(FIXTURE.read_text(encoding="utf-8"))
    values: dict[str, list] = {}
    for column in EXPORT_COLUMNS:
        if column == "dok_data":
            values[column] = [date.fromisoformat(row["dok_data"]) for row in rows]
        else:
            values[column] = [row.get(column) for row in rows]
    path = tmp_path / "12_transakcje_ceny_lokale.parquet"
    pq.write_table(pa.table(values), path)
    return path


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
