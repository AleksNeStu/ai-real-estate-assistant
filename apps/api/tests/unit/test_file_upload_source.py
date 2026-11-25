"""An uploaded file becomes a data source that can be synced again.

The upload endpoint used to write the bytes to a temporary file, read them,
put the listings into the catalogue and delete the file. The other half of
the product already existed - a data source of type ``file_upload`` names a
file, and the sync reads it - but the two halves did not meet: an operator
who uploaded a spreadsheet got its listings once, and a source of that type
could only be created by hand, with the name of a file that had to be put
into the uploads directory by hand as well.

These tests pin the meeting point: the file is kept, the source that names
it is created, and the sync reads that file.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Sequence
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.routers import admin as admin_router
from api.routers.data_sources import _collect_properties, _run_sync
from config.settings import settings
from data.uploaded_sources import (
    register_file_upload_source,
    safe_source_filename,
    store_uploaded_source_file,
)
from db.database import create_engine, get_db
from db.models import Base, DataSourceDB, DataSourceSyncHistory

CSV_BODY = b"city,price,rooms\nKrakow,500000,2\nGdansk,300000,1\n"


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """A client for the admin router, with the test database behind it."""
    app = FastAPI()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.include_router(admin_router.router, prefix="/api/v1")

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


async def _upload(client: AsyncClient, name: str | None = "Krakow listings") -> dict:
    """Upload the sheet and answer the body of the response."""
    data = {"source_name": name} if name else {}
    response = await client.post(
        "/api/v1/admin/ingest/upload",
        files={"file": ("listings.csv", CSV_BODY, "text/csv")},
        data=data,
    )
    assert response.status_code == 200, response.text
    body: dict = response.json()
    return body


class TestTheFileIsKeptWhereASourceCanReadIt:
    def test_the_name_of_the_source_becomes_a_safe_file_name(self):
        assert safe_source_filename("Krakow listings", ".csv") == "krakow-listings.csv"
        assert safe_source_filename("Q1/2024 .. Katalog", ".xlsx") == "q1-2024-katalog.xlsx"

    def test_the_file_is_written_under_the_uploads_directory(self, tmp_path: Path):
        relative = store_uploaded_source_file(
            CSV_BODY, uploads_root=tmp_path / "uploads", name="Krakow listings", suffix=".csv"
        )

        # The path is relative: the directory of the deployment is not the
        # same on every machine.
        assert relative == "sources/krakow-listings.csv"
        kept = tmp_path / "uploads" / relative
        assert kept.is_file()
        assert kept.read_bytes() == CSV_BODY

    def test_a_second_upload_of_that_name_replaces_the_file(self, tmp_path: Path):
        root = tmp_path / "uploads"
        first = store_uploaded_source_file(
            b"city\nKrakow\n", uploads_root=root, name="Krakow listings", suffix=".csv"
        )
        second = store_uploaded_source_file(
            b"city\nGdansk\n", uploads_root=root, name="Krakow listings", suffix=".csv"
        )

        # The upload is the creation of a source, not a copy of one: the
        # same name is the same source.
        assert first == second
        assert (root / first).read_bytes() == b"city\nGdansk\n"


class TestTheSourceIsCreated:
    @pytest.mark.asyncio
    async def test_the_source_names_the_file_and_the_sheet(self, db_session: AsyncSession) -> None:
        source = await register_file_upload_source(
            db_session,
            name="Krakow listings",
            filename="listings.csv",
            file_path="sources/krakow-listings.csv",
            sheet_name="Listings",
            header_row=0,
            size_bytes=len(CSV_BODY),
            records=2,
        )

        assert source.source_type == "file_upload"
        assert source.config["file_path"] == "sources/krakow-listings.csv"
        assert source.config["filename"] == "listings.csv"
        assert source.config["sheet_name"] == "Listings"
        assert source.config["size_bytes"] == len(CSV_BODY)
        assert source.total_records == 2

    @pytest.mark.asyncio
    async def test_a_second_upload_of_that_name_updates_the_same_source(
        self, db_session: AsyncSession
    ) -> None:
        first = await register_file_upload_source(
            db_session,
            name="Krakow listings",
            filename="listings.csv",
            file_path="sources/krakow-listings.csv",
            sheet_name=None,
            header_row=0,
            size_bytes=len(CSV_BODY),
            records=2,
        )
        second = await register_file_upload_source(
            db_session,
            name="Krakow listings",
            filename="listings.csv",
            file_path="sources/krakow-listings.csv",
            sheet_name=None,
            header_row=0,
            size_bytes=len(CSV_BODY),
            records=3,
        )

        assert first.id == second.id

        rows: Sequence[DataSourceDB] = (
            (await db_session.execute(_all_file_upload_sources())).scalars().all()
        )
        assert [row.name for row in rows] == ["Krakow listings"]


def _all_file_upload_sources():
    from sqlalchemy import select

    return select(DataSourceDB).where(DataSourceDB.source_type == "file_upload")


class TestTheUploadCreatesTheSource:
    @pytest.mark.asyncio
    async def test_the_upload_creates_a_source_that_reads_the_file(
        self, client: AsyncClient, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        uploads = tmp_path / "uploads"
        with (
            patch.object(settings, "uploads_dir", uploads),
            patch("api.routers.admin.save_collection"),
        ):
            body = await _upload(client)

            assert body["properties_processed"] == 2
            assert body["data_source_error"] is None
            assert body["data_source_id"]
            assert body["data_source_name"] == "Krakow listings"

            source = await db_session.get(DataSourceDB, body["data_source_id"])
            assert source is not None
            assert source.source_type == "file_upload"

            # The file is there, and it is inside the directory a source may
            # read from.
            kept = uploads / source.config["file_path"]
            assert kept.is_file()
            assert kept.read_bytes() == CSV_BODY

            # And the sync reads it - the source is not a name that points
            # at nothing.
            properties = await _collect_properties(source)
            assert len(properties) == 2
            assert {prop.city for prop in properties} == {"Krakow", "Gdansk"}

    @pytest.mark.asyncio
    async def test_a_file_that_cannot_be_kept_is_reported(
        self, client: AsyncClient, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        """The ingest succeeded, so the upload is not a failure - but the
        answer says that there is no source, and why."""
        with (
            patch.object(settings, "uploads_dir", tmp_path / "uploads"),
            patch("api.routers.admin.save_collection"),
            patch(
                "api.routers.admin.store_uploaded_source_file",
                side_effect=OSError("the disk is full"),
            ),
        ):
            body = await _upload(client)

        assert body["properties_processed"] == 2
        assert body["data_source_id"] is None
        assert body["data_source_error"]
        assert "the disk is full" in body["data_source_error"]

        rows: Sequence[DataSourceDB] = (
            (await db_session.execute(_all_file_upload_sources())).scalars().all()
        )
        assert rows == []


class TestTheSyncOfTheSource:
    """The rows of the file land in the catalogue, and the source counts them."""

    @pytest.mark.asyncio
    async def test_the_sync_reads_the_file_and_counts_the_rows(self, tmp_path: Path) -> None:
        db_url, session = await _a_database_on_disk(tmp_path)

        uploads = tmp_path / "uploads"
        with (
            patch.object(settings, "uploads_dir", uploads),
            patch("api.routers.admin.save_collection"),
        ):
            source = await register_file_upload_source(
                session,
                name="Krakow listings",
                filename="listings.csv",
                file_path=store_uploaded_source_file(
                    CSV_BODY, uploads_root=uploads, name="Krakow listings", suffix=".csv"
                ),
                sheet_name=None,
                header_row=0,
                size_bytes=len(CSV_BODY),
                records=2,
            )
            await session.commit()

        sync = DataSourceSyncHistory(
            data_source_id=source.id,
            started_at=datetime.now(UTC),
            status="running",
        )
        session.add(sync)
        await session.commit()

        store = MagicMock()
        with (
            patch.object(settings, "uploads_dir", uploads),
            patch("api.dependencies.get_vector_store", return_value=store),
            patch(
                "api.routers.data_sources.save_imported_properties",
                return_value=2,
            ),
        ):
            await _run_sync(source.id, sync.id, db_url)

        written = store.add_properties.call_args.args[0]
        assert len(written) == 2
        assert {prop.city for prop in written} == {"Krakow", "Gdansk"}

        # The sync ran on a session of its own, so the row is read back
        # from the database rather than from this session's memory of it.
        read_back = (
            await session.execute(
                select(DataSourceDB)
                .where(DataSourceDB.id == source.id)
                .execution_options(populate_existing=True)
            )
        ).scalar_one()
        assert read_back.status == "active"
        assert read_back.last_sync_status == "success"
        # The count is the number of rows the file carried.
        assert read_back.total_records == 2
        await session.close()


async def _a_database_on_disk(tmp_path: Path) -> tuple[str, AsyncSession]:
    """A database on disk, with a session on it.

    The sync opens a session of its own on the url it is given, so a
    database in memory would be a different database for it.
    """
    db_path = tmp_path / "sources.db"
    url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    session = factory()
    return url, session
