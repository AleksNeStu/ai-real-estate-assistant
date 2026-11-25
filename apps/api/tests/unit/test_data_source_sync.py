"""The sync of a data source, at unit level.

The machinery of the sync lives in the router, and the product gate asks the
unit suite for the coverage of the lines a change touches - so the download
guard, the file guard and the write of the listings are exercised here,
without a server in front of them.
"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

import api.dependencies as dependencies
from api.routers import data_sources
from config.settings import settings
from db.database import Base, create_engine
from db.models import DataSourceDB, DataSourceSyncHistory
from utils import property_cache

CSV_ROWS = 3

CSV_CONTENT = """id,title,city,price,area_sqm,rooms
p-1,Flat on Marszalkowska,Warsaw,2500,55,2
p-2,Flat on Karmelicka,Krakow,3000,60,3
p-3,Flat on Dluga,Gdansk,2000,45,1
"""


class _FakeStore:
    """The part of the vector store the sync writes to."""

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


class _FakeResponse:
    """The answer of a download, without a server behind it."""

    def __init__(self, *, headers: dict[str, str], chunks: list[bytes]) -> None:
        self.headers = headers
        self._chunks = chunks

    def raise_for_status(self) -> None:
        return None

    async def aiter_bytes(self):
        for chunk in self._chunks:
            yield chunk


class _FakeStream:
    """The stream of a download - it answers after the delay it was given."""

    def __init__(self, response: _FakeResponse, delay: float = 0.0) -> None:
        self._response = response
        self._delay = delay

    async def __aenter__(self) -> _FakeResponse:
        if self._delay:
            await asyncio.sleep(self._delay)
        return self._response

    async def __aexit__(self, *exc: object) -> bool:
        return False


class _FakeClient:
    """The client of a download - it hands back the response it was given."""

    def __init__(self, response: _FakeResponse, delay: float = 0.0) -> None:
        self._response = response
        self._delay = delay

    async def __aenter__(self) -> "_FakeClient":
        return self

    async def __aexit__(self, *exc: object) -> bool:
        return False

    def stream(self, method: str, url: str) -> _FakeStream:
        return _FakeStream(self._response, self._delay)


def _fake_httpx(
    monkeypatch: pytest.MonkeyPatch, response: _FakeResponse, delay: float = 0.0
) -> None:
    """Make every download of the router answer with the given response."""
    monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: _FakeClient(response, delay))


def _cache_in_tmp_path(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The catalogue cache of the test lives in the temporary directory."""
    cache_dir = tmp_path / "app_cache"
    monkeypatch.setattr(property_cache, "CACHE_DIR", cache_dir)
    monkeypatch.setattr(property_cache, "CACHE_FILE", cache_dir / "properties.json")
    monkeypatch.setattr(property_cache, "PREV_CACHE_FILE", cache_dir / "properties_prev.json")


# ---------------------------------------------------------------------------
# The file of a source
# ---------------------------------------------------------------------------


def test_a_source_may_only_read_a_file_of_the_uploads_directory(tmp_path, monkeypatch) -> None:
    """The config of a source names a file of the machine - so it is bounded."""
    monkeypatch.setattr(settings, "uploads_dir", tmp_path)

    inside = tmp_path / "listings.csv"
    inside.write_text("id,title\n", encoding="utf-8")
    assert data_sources._resolve_source_file("listings.csv") == inside.resolve()

    outside = tmp_path.parent / "outside.csv"
    outside.write_text("id,title\n", encoding="utf-8")
    with pytest.raises(ValueError, match="outside the uploads directory"):
        data_sources._resolve_source_file(str(outside))

    with pytest.raises(ValueError, match="is not there"):
        data_sources._resolve_source_file("missing.csv")


async def test_a_file_upload_source_reads_the_file_it_names(tmp_path, monkeypatch) -> None:
    """The file of the source is read, and its rows become listings."""
    monkeypatch.setattr(settings, "uploads_dir", tmp_path)
    csv_path = tmp_path / "listings.csv"
    csv_path.write_text(CSV_CONTENT, encoding="utf-8")

    source = DataSourceDB(
        id="src-1",
        name="Listings",
        source_type="file_upload",
        config={"filename": csv_path.name, "file_path": csv_path.name},
    )

    properties = await data_sources._collect_properties(source)

    assert len(properties) == CSV_ROWS
    assert {p.id for p in properties} == {"p-1", "p-2", "p-3"}


async def test_a_url_source_reads_the_document_it_downloads(monkeypatch) -> None:
    """The url says what the document is, and the document is read."""
    monkeypatch.setattr(data_sources, "_validate_url_no_ssrf", lambda url: None)

    async def _download(url: str) -> tuple[bytes, str]:
        return CSV_CONTENT.encode("utf-8"), "text/csv"

    monkeypatch.setattr(data_sources, "_download_url", _download)

    source = DataSourceDB(
        id="src-2",
        name="Remote listings",
        source_type="url",
        config={"url": "https://example.com/listings.csv"},
    )

    properties = await data_sources._collect_properties(source)

    assert len(properties) == CSV_ROWS
    assert {p.id for p in properties} == {"p-1", "p-2", "p-3"}


# ---------------------------------------------------------------------------
# The size of a document
# ---------------------------------------------------------------------------


def test_the_size_limit_refuses_a_document_over_it() -> None:
    """The limit is the one the upload carries, and it refuses a document."""
    limit = settings.max_upload_bytes

    with pytest.raises(ValueError, match="larger than the import limit"):
        data_sources._check_download_size(str(limit + 1), 0)

    with pytest.raises(ValueError, match="larger than the import limit"):
        data_sources._check_download_size(None, limit + 1)

    # The limit is a limit, not a ban.
    data_sources._check_download_size(str(limit), limit)


async def test_a_download_that_declares_too_much_is_refused(monkeypatch) -> None:
    """A document that announces a size over the limit is not read."""
    limit = settings.max_upload_bytes
    _fake_httpx(
        monkeypatch,
        _FakeResponse(
            headers={"content-length": str(limit + 1), "content-type": "text/csv"},
            chunks=[b"id,title\n"],
        ),
    )

    with pytest.raises(ValueError, match="larger than the import limit"):
        await data_sources._download_url("https://example.com/listings.csv")


async def test_a_download_that_trickles_is_cut_off(monkeypatch) -> None:
    """A download that keeps trickling is cut off, not held open."""
    monkeypatch.setattr(data_sources, "_MAX_SYNC_DOWNLOAD_SECONDS", 0.05)
    _fake_httpx(
        monkeypatch,
        _FakeResponse(headers={"content-type": "text/csv"}, chunks=[b"id,title\n"]),
        delay=5.0,
    )

    with pytest.raises(ValueError, match="took longer than"):
        await data_sources._download_url("https://example.com/listings.csv")


async def test_a_download_answers_with_the_document_and_its_content_type(
    monkeypatch,
) -> None:
    """The document arrives with the type the server serves it under."""
    _fake_httpx(
        monkeypatch,
        _FakeResponse(headers={"content-type": "text/csv"}, chunks=[b"id,title\n"]),
    )

    payload, content_type = await data_sources._download_url("https://example.com/listings.csv")

    assert payload == b"id,title\n"
    assert content_type == "text/csv"


# ---------------------------------------------------------------------------
# The write of the listings
# ---------------------------------------------------------------------------


async def _write_source(db_url: str) -> None:
    """The source and its sync record, in a database of their own."""
    engine = create_engine(db_url)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as setup:
        setup.add(
            DataSourceDB(
                id="src-1",
                name="Listings",
                source_type="file_upload",
                config={"filename": "listings.csv", "file_path": "listings.csv"},
            )
        )
        setup.add(
            DataSourceSyncHistory(
                id="sync-1",
                data_source_id="src-1",
                started_at=datetime.now(timezone.utc),
                status="running",
            )
        )
        await setup.commit()
    await engine.dispose()


async def test_the_sync_writes_the_listings_it_counted(tmp_path, monkeypatch) -> None:
    """The sync writes what it read, and the count says so."""
    monkeypatch.setattr(settings, "uploads_dir", tmp_path)
    _cache_in_tmp_path(tmp_path, monkeypatch)
    csv_path = tmp_path / "listings.csv"
    csv_path.write_text(CSV_CONTENT, encoding="utf-8")

    db_url = f"sqlite+aiosqlite:///{tmp_path / 'sync.db'}"
    await _write_source(db_url)

    store = _FakeStore()
    monkeypatch.setattr(dependencies, "get_vector_store", lambda: store)

    await data_sources._run_sync("src-1", "sync-1", db_url)

    # The catalogue holds the listings - in the store the product reads and
    # in the cache a reindex reads.
    assert len(store.properties) == CSV_ROWS
    cached = property_cache.load_collection()
    assert cached is not None
    assert len(cached.properties) == CSV_ROWS
    assert {p.id for p in cached.properties} == {"p-1", "p-2", "p-3"}

    engine = create_engine(db_url)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    try:
        async with session_factory() as read:
            source = await read.get(DataSourceDB, "src-1")
            record = await read.get(DataSourceSyncHistory, "sync-1")
        assert source is not None
        assert record is not None
        assert source.total_records == CSV_ROWS
        assert source.last_records_synced == CSV_ROWS
        assert source.last_sync_status == "success"
        assert record.status == "success"
        assert record.records_processed == CSV_ROWS
        assert record.records_added == CSV_ROWS
    finally:
        await engine.dispose()


async def test_a_second_sync_of_the_same_source_adds_nothing(tmp_path, monkeypatch) -> None:
    """The catalogue is a set: the listings are there, they are not written twice."""
    monkeypatch.setattr(settings, "uploads_dir", tmp_path)
    _cache_in_tmp_path(tmp_path, monkeypatch)
    csv_path = tmp_path / "listings.csv"
    csv_path.write_text(CSV_CONTENT, encoding="utf-8")

    db_url = f"sqlite+aiosqlite:///{tmp_path / 'sync.db'}"
    await _write_source(db_url)

    store = _FakeStore()
    monkeypatch.setattr(dependencies, "get_vector_store", lambda: store)

    await data_sources._run_sync("src-1", "sync-1", db_url)
    await data_sources._run_sync("src-1", "sync-1", db_url)

    assert len(store.properties) == CSV_ROWS
    cached = property_cache.load_collection()
    assert cached is not None
    assert len(cached.properties) == CSV_ROWS

    engine = create_engine(db_url)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    try:
        async with session_factory() as read:
            source = await read.get(DataSourceDB, "src-1")
            record = await read.get(DataSourceSyncHistory, "sync-1")
        assert source is not None
        assert record is not None
        # The source still carries its listings; the second sync wrote none.
        assert source.total_records == CSV_ROWS
        assert record.records_added == 0
        assert record.records_skipped == CSV_ROWS
    finally:
        await engine.dispose()


def test_a_file_over_the_limit_is_refused(tmp_path, monkeypatch) -> None:
    """The file of a source is bounded by the same limit a download is."""
    monkeypatch.setattr(settings, "uploads_dir", tmp_path)
    monkeypatch.setattr(type(settings), "max_upload_bytes", property(lambda self: 16))

    path = tmp_path / "listings.csv"
    path.write_text(CSV_CONTENT, encoding="utf-8")

    with pytest.raises(ValueError, match="larger than the import limit"):
        with data_sources._read_source_file(path):
            pass


def test_the_file_of_a_source_is_read_through_a_copy(tmp_path, monkeypatch) -> None:
    """The loader reads a copy - the file itself is not touched by the loader."""
    monkeypatch.setattr(settings, "uploads_dir", tmp_path)

    path = tmp_path / "listings.csv"
    path.write_text(CSV_CONTENT, encoding="utf-8")

    with data_sources._read_source_file(path) as readable:
        assert Path(readable) != path
        assert Path(readable).read_text(encoding="utf-8") == CSV_CONTENT

    # The copy does not outlive the read.
    assert not Path(readable).exists()
