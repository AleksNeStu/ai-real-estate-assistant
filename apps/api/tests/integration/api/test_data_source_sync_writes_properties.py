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
    """The part of the vector store the sync and the catalogue use."""

    def __init__(self) -> None:
        self.properties: list[Any] = []

    def add_properties(self, properties: list[Any], batch_size: int = 100) -> int:
        self.properties.extend(properties)
        return len(properties)

    def search_by_metadata(
        self, city: str | None = None, k: int = 50, **_: Any
    ) -> list[_FakeDocument]:
        rows = [p for p in self.properties if city is None or p.city == city]
        return [_FakeDocument(p.model_dump()) for p in rows[:k]]


async def _wait_for_sync(session_factory, timeout: float = 20.0) -> DataSourceSyncHistory:
    """Wait until the background sync recorded an outcome."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        async with session_factory() as session:
            result = await session.execute(select(DataSourceSyncHistory))
            record = result.scalar_one_or_none()
            if record is not None and record.status != "running":
                return cast(DataSourceSyncHistory, record)
        await asyncio.sleep(0.05)
    raise AssertionError("the background sync did not finish in time")


class _Harness:
    """The application, the database and the store one sync runs against."""

    def __init__(self, tmp_path, monkeypatch, csv_content: str) -> None:
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
                        "file_path": str(self.csv_path),
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
async def test_a_download_over_the_limit_is_refused():
    """A sync reads a document somebody else controls - under a limit."""
    import httpx
    import respx

    url = "https://example.com/listings.csv"
    over_the_limit = data_sources._MAX_SYNC_DOWNLOAD_BYTES + 1

    with respx.mock:
        respx.get(url).mock(
            return_value=httpx.Response(
                200,
                headers={"content-length": str(over_the_limit)},
                content=b"",
            )
        )
        with pytest.raises(ValueError, match="larger than the import limit"):
            await data_sources._download_url(url)
