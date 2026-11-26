"""A data-source sync writes the properties it counted.

The sync used to count lines of a document and the length of a JSON payload
and write nothing at all, so ``total_records`` reported what was read instead
of what landed, and the catalogue never grew.
"""

import asyncio
from typing import Any, cast

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

import api.dependencies as dependencies
from api.routers import data_sources, properties
from config.settings import settings
from db.database import Base, create_engine, get_db
from db.models import DataSourceDB, DataSourceSyncHistory
from utils import property_cache

CSV_ROWS = 3

CSV_CONTENT = """id,title,city,price,area_sqm,rooms
p-1,Flat on Marszalkowska,Warsaw,2500,55,2
p-2,Flat on Karmelicka,Krakow,3000,60,3
p-3,Flat on Dluga,Gdansk,2000,45,1
"""

CSV_WITHOUT_ROWS = """id,title,city,price,area_sqm,rooms
"""


class _FakeDocument:
    """What the vector store hands back: a metadata mapping and a text."""

    def __init__(self, metadata: dict[str, Any]) -> None:
        self.metadata = metadata
        self.page_content = str(metadata.get("title") or "")


class _FakeStore:
    """The part of the vector store the sync and the catalogue use.

    The real store keys a document by the id of its listing and skips the
    ones it already holds, so a source that syncs twice leaves the
    collection the size it was.
    """

    def __init__(self) -> None:
        self.properties: list[Any] = []

    def add_properties(
        self, properties: list[Any], batch_size: int = 100, refresh: bool = False
    ) -> int:
        known = {p.id for p in self.properties}
        added = 0
        for prop in properties:
            if prop.id and prop.id in known:
                # A source of record writes the newer listing under the id of
                # the one the collection holds; every other source leaves it.
                if refresh:
                    index = next(i for i, p in enumerate(self.properties) if p.id == prop.id)
                    self.properties[index] = prop
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

    def __init__(self, tmp_path, monkeypatch, csv_content: str) -> None:
        # The uploads directory of the deployment: a source may only read a
        # file inside it, so the fixture lives there.
        monkeypatch.setattr(settings, "uploads_dir", tmp_path)
        self.csv_path = tmp_path / "listings.csv"
        self.csv_path.write_text(csv_content, encoding="utf-8")

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
        self.db_url = f"sqlite+aiosqlite:///{tmp_path / 'sync.db'}"
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

    async def setup(self, source_id: str = "src-sync-1") -> None:
        """Create the schema and the data source the sync reads."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with self.session_factory() as setup:
            setup.add(
                DataSourceDB(
                    id=source_id,
                    name="Listings",
                    source_type="file_upload",
                    config={
                        "filename": self.csv_path.name,
                        "file_path": self.csv_path.name,
                    },
                )
            )
            await setup.commit()

    def client(self) -> AsyncClient:
        return AsyncClient(transport=self.transport, base_url="http://test")

    async def close(self) -> None:
        await self.session.close()
        await self.engine.dispose()


@pytest.mark.asyncio
async def test_sync_writes_the_properties_it_counted(tmp_path, monkeypatch):
    """The rows of the file land in the catalogue, and the count says so."""
    harness = _Harness(tmp_path, monkeypatch, CSV_CONTENT)
    await harness.setup()

    try:
        async with harness.client() as client:
            response = await client.post("/api/v1/data-sources/src-sync-1/sync")
            assert response.status_code == 200

            record = await _wait_for_sync(harness.session_factory)

            catalogue = await client.get("/api/v1/properties")
            assert catalogue.status_code == 200

        # The sync counted what it wrote.
        assert record.status == "success", record.error_message
        assert record.records_processed == CSV_ROWS

        async with harness.session_factory() as read:
            source = await read.get(DataSourceDB, "src-sync-1")
            assert source is not None
            assert source.total_records == CSV_ROWS
            assert source.last_records_synced == CSV_ROWS
            assert source.last_sync_status == "success"

        # The rows are findable.
        assert catalogue.json()["count"] == CSV_ROWS

        # The Chroma collection holds them.
        assert len(harness.store.properties) == CSV_ROWS

        # The JSON cache holds them.
        cached = property_cache.load_collection()
        assert cached is not None
        assert len(cached.properties) == CSV_ROWS
    finally:
        await harness.close()


@pytest.mark.asyncio
async def test_sync_of_a_source_with_no_rows_fails(tmp_path, monkeypatch):
    """A source that yields nothing is a failure, not a success with zero."""
    harness = _Harness(tmp_path, monkeypatch, CSV_WITHOUT_ROWS)
    await harness.setup()

    try:
        async with harness.client() as client:
            response = await client.post("/api/v1/data-sources/src-sync-1/sync")
            assert response.status_code == 200

            record = await _wait_for_sync(harness.session_factory)

        assert record.status == "failed"
        assert "no valid properties" in (record.error_message or "")

        async with harness.session_factory() as read:
            source = await read.get(DataSourceDB, "src-sync-1")
            assert source is not None
            assert source.total_records == 0
            assert source.last_sync_status == "failed"

        # Nothing landed.
        assert harness.store.properties == []
        assert property_cache.load_collection() is None
    finally:
        await harness.close()


@pytest.mark.asyncio
async def test_two_syncs_of_the_same_file_leave_one_set_of_listings(tmp_path, monkeypatch):
    """A source that syncs twice carries the same listings - the catalogue is a set."""
    harness = _Harness(tmp_path, monkeypatch, CSV_CONTENT)
    await harness.setup()

    try:
        async with harness.client() as client:
            await client.post("/api/v1/data-sources/src-sync-1/sync")
            first = await _wait_for_sync(harness.session_factory)

            response = await client.post("/api/v1/data-sources/src-sync-1/sync")
            assert response.status_code == 200
            second = await _wait_for_sync(harness.session_factory, count=2)

            catalogue = await client.get("/api/v1/properties")
            assert catalogue.status_code == 200

        # The first sync wrote the listings.
        assert first.status == "success", first.error_message
        assert first.records_added == CSV_ROWS

        # The second sync found them where they were: it wrote nothing.
        assert second.status == "success", second.error_message
        assert second.records_added == 0
        assert second.records_skipped == CSV_ROWS
        assert second.records_processed == CSV_ROWS

        # The catalogue holds the listings once, not twice.
        assert catalogue.json()["count"] == CSV_ROWS

        cached = property_cache.load_collection()
        assert cached is not None
        assert len(cached.properties) == CSV_ROWS
    finally:
        await harness.close()


@pytest.mark.asyncio
async def test_a_source_that_recovers_is_healthy_again(tmp_path, monkeypatch):
    """A source that failed and then synced says so.

    The health of a source is computed from the failures it has had. The
    counter is reset by a successful sync, and the error of the failed run
    is cleared by it too - a source that recovered carries neither, so the
    panel shows a healthy source instead of a healthy source with the
    message of a failure that no longer describes it.
    """
    harness = _Harness(tmp_path, monkeypatch, CSV_WITHOUT_ROWS)
    await harness.setup()

    try:
        async with harness.client() as client:
            await client.post("/api/v1/data-sources/src-sync-1/sync")
            failed = await _wait_for_sync(harness.session_factory)

            assert failed.status == "failed"

            async with harness.session_factory() as read:
                broken = await read.get(DataSourceDB, "src-sync-1")
                assert broken is not None
                assert broken.status == "error"
                assert broken.last_error
                assert broken.consecutive_failures == 1

            # The source has something to read now.
            harness.csv_path.write_text(CSV_CONTENT, encoding="utf-8")

            await client.post("/api/v1/data-sources/src-sync-1/sync")
            await _wait_for_sync(harness.session_factory, count=2)

        async with harness.session_factory() as read:
            source = await read.get(DataSourceDB, "src-sync-1")
            assert source is not None

            assert source.status == "active"
            assert source.last_sync_status == "success"
            # The failure it recovered from is not a part of it any more.
            assert source.last_error is None
            assert source.consecutive_failures == 0
            # The health is computed from the counter and the last outcome,
            # so a source that recovered is healthy - not healthy in a cycle.
            assert source.health_score == 100.0
    finally:
        await harness.close()
