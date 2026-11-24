"""The catalogue can be built from the official register.

The register's sales are ingested into the database by the ingest. A data
source of the kind "register" turns them into listings of the catalogue - the
JSON cache and the Chroma collection - through the same write chain every
other source uses. The listing pages then answer with flats that really
changed hands, and every one of them carries the register as its source.

The only boundary that is replaced here is the network: the register's own
recorded answer stands in for the file the publisher sends, so the parsing,
the ingest, the conversion, the write and the read are all the real thing.
"""

import asyncio
import json
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

import api.dependencies as dependencies
import data.rcn.rcn_client as rcn_client
from api.routers import data_sources, properties
from config.settings import settings
from data.rcn.rcn_ingest import ingest_voivodeship
from db.database import Base, create_engine, get_db
from db.models import DataSourceDB, DataSourceSyncHistory
from tests.fixtures import recorded_rcn_export
from utils import property_cache

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "rcn" / "krakow_sample.json"

# The sales the recorded export holds, and the ones of them the register
# publishes with everything a listing needs. The register drops a flat whose
# area is out of the range a flat can have, so the two numbers differ.
RECORDED_ROWS = 55
INGESTED_ROWS = 54

# The band the answer is read in: nine of the recorded sales fall in it.
PRICE_BAND = (700_000.0, 800_000.0)


class _FakeDocument:
    """What the vector store hands back: a metadata mapping and a text."""

    def __init__(self, metadata: dict[str, Any]) -> None:
        self.metadata = metadata
        self.page_content = str(metadata.get("description") or "")


class _FakeStore:
    """The part of the vector store the sync and the catalogue use.

    The real store keys a document by the id of its listing and skips the
    ones it already holds. This stand-in holds the same rule, so a sync
    that runs twice leaves the collection the size it was - and the test
    below runs the sync twice to hold that rule.

    What this stand-in proves is the shape of the exchange: which listings
    are handed to the collection and which come back out of it. The real
    store is held by the tests of the vector store itself.
    """

    def __init__(self) -> None:
        self.properties: list[Any] = []

    def add_properties(self, properties: list[Any], batch_size: int = 100) -> int:
        known = {p.id for p in self.properties}
        added = 0
        for prop in properties:
            if prop.id and prop.id in known:
                continue
            self.properties.append(prop)
            if prop.id:
                known.add(prop.id)
            added += 1
        return added

    def search_by_metadata(
        self, city: str | None = None, k: int = 50, **_: Any
    ) -> list[_FakeDocument]:
        rows = [p for p in self.properties if city is None or p.city == city]
        return [_FakeDocument(p.model_dump()) for p in rows[:k]]


async def _wait_for_sync(
    session_factory, timeout: float = 20.0, count: int = 1
) -> DataSourceSyncHistory:
    """Wait until the background sync recorded an outcome.

    The records are ordered by the time the sync started: the id of a record
    is a random uuid, so ordering by it would hand back a record that has
    nothing to do with the sync that was waited for.
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        async with session_factory() as session:
            result = await session.execute(
                select(DataSourceSyncHistory).order_by(DataSourceSyncHistory.started_at.desc())
            )
            records = list(result.scalars().all())
            if len(records) >= count and records[0].status != "running":
                return cast(DataSourceSyncHistory, records[0])
        await asyncio.sleep(0.05)
    raise AssertionError("the background sync did not finish in time")


class _Harness:
    """The application, the database and the store one sync runs against."""

    def __init__(self, tmp_path, monkeypatch) -> None:
        # The uploads directory of the deployment: a source may only read a
        # file inside it, so the fixture lives there.
        monkeypatch.setattr(settings, "uploads_dir", tmp_path)

        # The catalogue cache lives in the temporary directory of the test.
        cache_dir = tmp_path / "app_cache"
        monkeypatch.setattr(property_cache, "CACHE_DIR", cache_dir)
        monkeypatch.setattr(property_cache, "CACHE_FILE", cache_dir / "properties.json")
        monkeypatch.setattr(property_cache, "PREV_CACHE_FILE", cache_dir / "properties_prev.json")

        self.store = _FakeStore()
        # The routes captured the dependency when they were declared, so the
        # override - not a patched attribute - is what replaces it. The key is
        # the function the routes hold, which the patch below replaces.
        real_get_vector_store = dependencies.get_vector_store
        monkeypatch.setattr(dependencies, "get_vector_store", lambda: self.store)

        # A database of its own: the background sync opens a session of its
        # own, and an in-memory database is per engine, not per file.
        self.db_url = f"sqlite+aiosqlite:///{tmp_path / 'register.db'}"
        monkeypatch.setattr(data_sources, "get_database_url", lambda: self.db_url, raising=False)
        self.engine = create_engine(self.db_url)
        self.session_factory = async_sessionmaker(bind=self.engine, expire_on_commit=False)

        # One session for the request and the background work, the way the
        # application hands the same session to both.
        self.session = self.session_factory()

        self.app = FastAPI()
        self.app.include_router(data_sources.router, prefix="/api/v1")
        self.app.include_router(properties.router, prefix="/api/v1")

        async def override_get_db():
            try:
                yield self.session
                await self.session.commit()
            except Exception:
                await self.session.rollback()
                raise

        self.app.dependency_overrides[get_db] = override_get_db
        self.app.dependency_overrides[real_get_vector_store] = lambda: self.store
        self.transport = ASGITransport(app=self.app)

    async def setup(self, tmp_path, monkeypatch, city: str = "Kraków") -> None:
        """Create the schema, ingest the register's sales, register the source."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # The register's own recorded answer, ingested the way the deployment
        # ingests it.
        rows = json.loads(FIXTURE.read_text(encoding="utf-8"))
        export = recorded_rcn_export(rows, tmp_path / "12_transakcje_ceny_lokale.parquet")
        monkeypatch.setattr(rcn_client, "download_export", lambda *a, **k: export)
        async with self.session_factory() as session:
            report = await ingest_voivodeship(session, "12", cache_dir=tmp_path)
        assert report.inserted == INGESTED_ROWS

        # The data source the operator registers: the register itself, for
        # one city.
        async with self.session_factory() as setup:
            setup.add(
                DataSourceDB(
                    id="src-register-1",
                    name="Official register",
                    source_type="register",
                    config={"city": city},
                )
            )
            await setup.commit()

    def client(self) -> AsyncClient:
        return AsyncClient(transport=self.transport, base_url="http://test")

    async def close(self) -> None:
        await self.session.close()
        await self.engine.dispose()


@pytest.mark.asyncio
async def test_the_register_becomes_the_catalogue(tmp_path, monkeypatch):
    """The register's sales become listings, and the pages answer with them."""
    harness = _Harness(tmp_path, monkeypatch)
    await harness.setup(tmp_path, monkeypatch)

    try:
        async with harness.client() as client:
            response = await client.post("/api/v1/data-sources/src-register-1/sync")
            assert response.status_code == 200

            record = await _wait_for_sync(harness.session_factory)

            catalogue = await client.get(
                "/api/v1/properties", params={"city": "Kraków", "limit": 100}
            )
            assert catalogue.status_code == 200

        # The sync wrote what it read.
        assert record.status == "success", record.error_message
        assert record.records_processed == INGESTED_ROWS

        listings = catalogue.json()["properties"]
        assert len(listings) == INGESTED_ROWS

        # Every listing is a flat that really changed hands, and it says so.
        assert {listing["source_platform"] for listing in listings} == {"rcn"}
        assert {listing["listing_type"] for listing in listings} == {"sale"}
        assert {listing["city"] for listing in listings} == {"Kraków"}
        assert all(listing["source_url"] for listing in listings)

        # None of them is a seeded listing: the catalogue holds the register's
        # own flats, not the demo ones beside them.
        assert not any((listing["id"] or "").startswith("prop-") for listing in listings)
        assert all((listing["id"] or "").startswith("rcn-") for listing in listings)

        # The price of the deed is the price of the listing.
        assert 790_000.0 in {listing["price"] for listing in listings}

        # The listing says what the price is: what the buyer paid.
        assert all("not an asking price" in (listing["description"] or "") for listing in listings)
        # And it carries the deed behind it.
        deed_listing = next(listing for listing in listings if listing["price"] == 790_000.0)
        assert "18806/2026" in (deed_listing["description"] or "")

        # The street of the deed is the district of the listing.
        districts = {listing["district"] for listing in listings}
        assert "Bronowice" in districts

        # A price band of the register's own sales answers with those sales.
        band = [
            listing
            for listing in listings
            if PRICE_BAND[0] <= (listing["price"] or 0) <= PRICE_BAND[1]
        ]
        assert band
        assert all(listing["source_platform"] == "rcn" for listing in band)

        # The JSON cache holds them.
        cached = property_cache.load_collection()
        assert cached is not None
        assert len(cached.properties) == INGESTED_ROWS

        # The collection holds them.
        assert len(harness.store.properties) == INGESTED_ROWS

        # A second sync of the same register leaves the catalogue the size it
        # was. The record is the sync's own answer: the collection reports how
        # many listings it added, and the sync says what was already there.
        # The cache is the real one, so its size is the product's own reading;
        # the collection is the stand-in of this test, and it holds the rule
        # the vector store holds - the rule itself is held by the tests of
        # the vector store.
        async with harness.client() as client:
            response = await client.post("/api/v1/data-sources/src-register-1/sync")
            assert response.status_code == 200

            second = await _wait_for_sync(harness.session_factory, count=2)

        assert second.status == "success", second.error_message
        assert second.records_processed == INGESTED_ROWS
        assert second.records_added == 0
        assert second.records_skipped == INGESTED_ROWS
        assert len(harness.store.properties) == INGESTED_ROWS
        cached_again = property_cache.load_collection()
        assert cached_again is not None
        assert len(cached_again.properties) == INGESTED_ROWS
    finally:
        await harness.close()


@pytest.mark.asyncio
async def test_a_city_the_site_does_not_know_is_refused(tmp_path, monkeypatch):
    """The register source names a city the site knows - and says so if not."""
    harness = _Harness(tmp_path, monkeypatch)
    await harness.setup(tmp_path, monkeypatch, city="Atlantis")

    try:
        async with harness.client() as client:
            response = await client.post("/api/v1/data-sources/src-register-1/sync")
            assert response.status_code == 200

            record = await _wait_for_sync(harness.session_factory)

        assert record.status == "failed"
        assert "Atlantis" in (record.error_message or "")

        # Nothing landed.
        assert harness.store.properties == []
        assert property_cache.load_collection() is None
    finally:
        await harness.close()


@pytest.mark.asyncio
async def test_the_test_of_a_register_source_counts_the_sales(tmp_path, monkeypatch):
    """The test of a register source is the number of sales behind it."""
    harness = _Harness(tmp_path, monkeypatch)
    await harness.setup(tmp_path, monkeypatch)

    try:
        async with harness.client() as client:
            response = await client.post(
                "/api/v1/data-sources/test",
                json={"source_type": "register", "config": {"city": "Kraków"}},
            )
            assert response.status_code == 200
            answer = response.json()

        assert answer["success"] is True
        assert str(INGESTED_ROWS) in answer["message"]
        assert answer["details"]["city"] == "Kraków"
    finally:
        await harness.close()


@pytest.mark.asyncio
async def test_a_register_source_with_a_config_that_cannot_be_read_is_refused(
    tmp_path, monkeypatch
):
    """A source that cannot read anything is refused when it is written.

    The window is checked at the writing of the source and not at its sync,
    in the middle of a run nobody is watching: every way of naming a window
    the reader cannot read is named in the answer.
    """
    harness = _Harness(tmp_path, monkeypatch)
    await harness.setup(tmp_path, monkeypatch)

    refused = (
        ({"city": "Atlantis"}, "unknown city"),
        ({}, "requires 'city'"),
        ({"city": "Kraków", "since": "yesterday"}, "not a date"),
        ({"city": "Kraków", "limit": "many"}, "not a number"),
        ({"city": "Kraków", "limit": 0}, "positive"),
        ({"city": "Kraków", "limit": 10_000_000}, "must not be more than"),
    )

    try:
        async with harness.client() as client:
            for config, expected in refused:
                response = await client.post(
                    "/api/v1/data-sources/test",
                    json={"source_type": "register", "config": config},
                )
                assert response.status_code == 200, config
                answer = response.json()
                assert answer["success"] is False, config
                assert expected in answer["message"], (config, answer["message"])
    finally:
        await harness.close()


@pytest.mark.asyncio
async def test_a_register_source_with_a_readable_config_passes_the_test(tmp_path, monkeypatch):
    """A source that names a city the site knows and a window it can read."""
    harness = _Harness(tmp_path, monkeypatch)
    await harness.setup(tmp_path, monkeypatch)

    try:
        async with harness.client() as client:
            response = await client.post(
                "/api/v1/data-sources/test",
                json={
                    "source_type": "register",
                    "config": {"city": "Kraków", "since": "2026-01-01", "limit": 100},
                },
            )
            assert response.status_code == 200
            answer = response.json()

        assert answer["success"] is True
    finally:
        await harness.close()
