"""A register source is read and tested without a database.

The two functions of this kind are thin adapters over the repository's own
reads: the sales of a city, and the count of them. A unit test replaces
those reads with a recorded answer, so the adapter itself is held to its own
rules - the city it names, the window it reads, the sales it refuses and
the answer it gives when the register holds nothing.

The database is not the boundary this test replaces: the reads are. The
end-to-end path - the ingest, the sync, the write into the cache and the
collection - is held by the integration test.
"""

from datetime import date
from typing import Any, cast

import pytest

import api.routers.data_sources as data_sources
from api.models import DataSourceTestRequest, DataSourceType
from data.rcn.rcn_models import RCNAddress, RCNTransaction


def _deed(**overrides: Any) -> RCNTransaction:
    """One registered sale, as the register writes it."""
    values: dict[str, Any] = {
        "external_id": "5CD7540E-F012-2DDC-E063-0C0A1EAC5265",
        "teryt": "1261",
        "address": RCNAddress(city="KRAKÓW", street="TOPOLOWA", number="48"),
        "area_sqm": 38.72,
        "price": 790_000.0,
        "transaction_date": date(2026, 8, 27),
        "market": "rynekWtorny",
        "rooms": 2,
        "floor": 4,
        "deed_reference": "Rep. A 18806/2026",
        "notary": "NOTARIUSZ NIEMIEC MATEUSZ",
        "source_url": "https://example.org/12_transakcje_ceny_lokale.parquet",
    }
    values.update(overrides)
    return RCNTransaction(**values)


def _session() -> Any:
    """A stand-in for the session.

    The functions under test pass the session straight to the read they
    call, and the read is what this test replaces - so the session itself
    is never touched.
    """
    return cast(Any, object())


def _recorded_read(monkeypatch, deeds: list[RCNTransaction]) -> dict[str, Any]:
    """Replace the read of the register with a recorded answer."""
    seen: dict[str, Any] = {}

    async def fake_transactions_for(
        session: Any,
        city_norm: str,
        since: date | None = None,
        limit: int = 5000,
        **_: Any,
    ) -> list[RCNTransaction]:
        seen["city_norm"] = city_norm
        seen["since"] = since
        seen["limit"] = limit
        return list(deeds)

    monkeypatch.setattr(data_sources, "transactions_for", fake_transactions_for)
    return seen


@pytest.mark.asyncio
async def test_the_sales_of_the_city_become_listings(monkeypatch) -> None:
    """The register's own sales become the listings of the catalogue."""
    seen = _recorded_read(monkeypatch, [_deed()])

    listings = await data_sources._collect_register_properties({"city": "Kraków"}, _session())

    assert len(listings) == 1
    assert listings[0].source_platform == "rcn"
    assert listings[0].price == 790_000.0
    assert listings[0].city == "Kraków"
    # The city is read under the register's own spelling.
    assert seen["city_norm"] == "KRAKOW"


@pytest.mark.asyncio
async def test_the_window_is_read_as_the_config_names_it(monkeypatch) -> None:
    """The source reads the window it names, and no other."""
    seen = _recorded_read(monkeypatch, [_deed()])

    await data_sources._collect_register_properties(
        {"city": "Kraków", "since": "2026-01-01", "limit": 100}, _session()
    )

    assert seen["since"] == date(2026, 1, 1)
    assert seen["limit"] == 100


@pytest.mark.asyncio
async def test_a_register_source_that_holds_nothing_is_refused(monkeypatch) -> None:
    """An empty register is a source that syncs nothing."""
    _recorded_read(monkeypatch, [])

    with pytest.raises(ValueError, match="holds no sale"):
        await data_sources._collect_register_properties({"city": "Kraków"}, _session())


@pytest.mark.asyncio
async def test_a_register_source_needs_a_city() -> None:
    """Without a city there is nothing to read."""
    with pytest.raises(ValueError, match="needs 'city'"):
        await data_sources._collect_register_properties({}, _session())


@pytest.mark.asyncio
async def test_a_register_source_of_an_unknown_city_is_refused() -> None:
    """The register source names a city the site knows."""
    with pytest.raises(ValueError, match="unknown city"):
        await data_sources._collect_register_properties({"city": "Atlantis"}, _session())


@pytest.mark.asyncio
async def test_a_register_source_needs_the_database() -> None:
    """The register is read from the database - never from the request."""
    with pytest.raises(RuntimeError, match="from the database"):
        await data_sources._collect_register_properties({"city": "Kraków"}, None)


@pytest.mark.asyncio
async def test_a_source_of_the_kind_register_is_read_through_the_chain(monkeypatch) -> None:
    """The chain of every other source is the chain of this one too."""
    seen: dict[str, Any] = {}

    async def fake_collect(config: dict[str, Any], session: Any) -> list[Any]:
        seen["config"] = config
        seen["session"] = session
        return ["listing"]

    monkeypatch.setattr(data_sources, "_collect_register_properties", fake_collect)

    class _Source:
        source_type = "register"
        config = {"city": "Kraków"}

    session = _session()
    collected = await data_sources._collect_properties(cast(Any, _Source()), session)

    assert collected == ["listing"]
    assert seen["config"] == {"city": "Kraków"}
    assert seen["session"] is session


@pytest.mark.asyncio
async def test_the_test_of_a_register_source_counts_the_sales(monkeypatch) -> None:
    """The test of a register source is the number of sales behind it."""
    counted: dict[str, Any] = {}

    async def fake_count(session: Any, city_norm: str, **_: Any) -> int:
        counted["city_norm"] = city_norm
        return 42

    monkeypatch.setattr(data_sources, "count_transactions", fake_count)

    answer = await data_sources._test_register_source({"city": "Kraków"}, _session())

    assert answer.success is True
    assert "42" in answer.message
    assert counted["city_norm"] == "KRAKOW"


@pytest.mark.asyncio
async def test_the_test_of_a_register_source_of_an_unknown_city_is_refused() -> None:
    """The test names the city the site does not know."""
    with pytest.raises(ValueError, match="unknown city"):
        await data_sources._test_register_source({"city": "Atlantis"}, _session())


@pytest.mark.asyncio
async def test_the_test_of_a_register_source_reads_the_database(monkeypatch) -> None:
    """The endpoint of the test answers with the register's own count."""
    called: dict[str, Any] = {}

    async def fake_test(config: dict[str, Any], db: Any) -> Any:
        called["config"] = config
        return data_sources.DataSourceTestResponse(
            success=True, message="the register holds 7 registered sale(s) of Kraków.", details=None
        )

    monkeypatch.setattr(data_sources, "_test_register_source", fake_test)

    answer = await data_sources.test_data_source(
        DataSourceTestRequest(source_type=DataSourceType.REGISTER, config={"city": "Kraków"}),
        db=cast(Any, _session()),
    )

    assert answer.success is True
    assert called["config"] == {"city": "Kraków"}
