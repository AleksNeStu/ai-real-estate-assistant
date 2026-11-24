"""A data-source sync writes the properties it counted.

The sync used to count lines of a document and the length of a JSON payload
and write nothing at all, so ``total_records`` reported what was read instead
of what landed, and the catalogue never grew.
"""

import asyncio
from typing import Any

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
                return record
        await asyncio.sleep(0.05)
    raise AssertionError("the background sync did not finish in time")


@pytest.mark.asyncio
async def test_sync_writes_the_properties_it_counted(tmp_path, monkeypatch):
    """The rows of the file land in the catalogue, and the count says so."""
    csv_path = tmp_path / "listings.csv"
    csv_path.write_text(CSV_CONTENT, encoding="utf-8")

    # The catalogue cache lives in the temporary directory of the test.
    cache_dir = tmp_path / "app_cache"
    monkeypatch.setattr(property_cache, "CACHE_DIR", cache_dir)
    monkeypatch.setattr(property_cache, "CACHE_FILE", cache_dir / "properties.json")
    monkeypatch.setattr(property_cache, "PREV_CACHE_FILE", cache_dir / "properties_prev.json")

    store = _FakeStore()
    # The routes captured the dependency when they were declared, so the
    # override - not a patched attribute - is what replaces it. The key is
    # the function the routes hold, which the patch below replaces.
    real_get_vector_store = dependencies.get_vector_store
    monkeypatch.setattr(dependencies, "get_vector_store", lambda: store)

    # A database of its own: the background sync opens a session of its own,
    # and an in-memory database is per engine, not per file.
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'sync.db'}"
    monkeypatch.setattr(data_sources, "get_database_url", lambda: db_url, raising=False)
    engine = create_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    # One session for the request and the background work, the way the
    # application hands the same session to both.
    session = session_factory()

    async with session_factory() as setup:
        setup.add(
            DataSourceDB(
                id="src-sync-1",
                name="Listings",
                source_type="file_upload",
                config={"filename": csv_path.name, "file_path": str(csv_path)},
            )
        )
        await setup.commit()

    app = FastAPI()
    app.include_router(data_sources.router, prefix="/api/v1")
    app.include_router(properties.router, prefix="/api/v1")

    async def override_get_db():
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[real_get_vector_store] = lambda: store
    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/data-sources/src-sync-1/sync")
            assert response.status_code == 200

            record = await _wait_for_sync(session_factory)

            catalogue = await client.get("/api/v1/properties")
            assert catalogue.status_code == 200

        # The sync counted what it wrote.
        assert record.status == "success", record.error_message
        assert record.records_processed == CSV_ROWS

        async with session_factory() as read:
            source = await read.get(DataSourceDB, "src-sync-1")
            assert source is not None
            assert source.total_records == CSV_ROWS
            assert source.last_sync_status == "success"

        # The rows are findable.
        assert catalogue.json()["count"] == CSV_ROWS

        # The Chroma collection holds them.
        assert len(store.properties) == CSV_ROWS

        # The JSON cache holds them.
        cached = property_cache.load_collection()
        assert cached is not None
        assert len(cached.properties) == CSV_ROWS
    finally:
        await session.close()
        await engine.dispose()
