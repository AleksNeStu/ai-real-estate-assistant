"""Tests for the buyer-memory table (Task #76)."""

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import DateTime, Float, String, Text, event, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from db.database import Base
from db.models import BuyerMemoryFact, User


@pytest.fixture
async def fk_session() -> AsyncGenerator[AsyncSession, None]:
    """A session whose SQLite connection enforces foreign keys.

    SQLite ignores ON DELETE CASCADE unless PRAGMA foreign_keys=ON is set per
    connection, and the shared `db_session` fixture does not set it.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


class TestBuyerMemoryFactTable:
    """The table and its columns exist as the task specifies."""

    def test_table_exists(self):
        table = Base.metadata.tables["buyer_memory_facts"]
        assert table.name == "buyer_memory_facts"

    def test_columns_and_types(self):
        columns = Base.metadata.tables["buyer_memory_facts"].columns

        assert set(columns.keys()) == {
            "id",
            "user_id",
            "kind",
            "content",
            "listing_id",
            "confidence",
            "source",
            "created_at",
            "updated_at",
            "expires_at",
        }

        assert isinstance(columns["id"].type, String)
        assert columns["id"].type.length == 36
        assert columns["id"].primary_key

        assert isinstance(columns["user_id"].type, String)
        assert columns["user_id"].type.length == 36
        assert not columns["user_id"].nullable

        assert isinstance(columns["kind"].type, String)
        assert columns["kind"].type.length == 32
        assert not columns["kind"].nullable

        assert isinstance(columns["content"].type, Text)
        assert not columns["content"].nullable

        assert isinstance(columns["listing_id"].type, String)
        assert columns["listing_id"].type.length == 36
        assert columns["listing_id"].nullable

        assert isinstance(columns["confidence"].type, Float)
        assert not columns["confidence"].nullable

        assert isinstance(columns["source"].type, String)
        assert columns["source"].type.length == 32
        assert not columns["source"].nullable

        assert isinstance(columns["created_at"].type, DateTime)
        assert columns["created_at"].type.timezone
        assert isinstance(columns["updated_at"].type, DateTime)
        assert columns["updated_at"].type.timezone
        assert isinstance(columns["expires_at"].type, DateTime)
        assert columns["expires_at"].nullable

    def test_user_id_foreign_key_cascades(self):
        table = Base.metadata.tables["buyer_memory_facts"]
        foreign_keys = list(table.foreign_keys)
        assert len(foreign_keys) == 1
        fk = foreign_keys[0]
        assert fk.target_fullname == "users.id"
        assert fk.ondelete == "CASCADE"

    def test_user_id_index_exists(self):
        table = Base.metadata.tables["buyer_memory_facts"]
        index_names = {index.name for index in table.indexes}
        assert "ix_buyer_memory_facts_user_id" in index_names
        assert table.columns["user_id"].index

    def test_defaults(self):
        # Column defaults are applied at INSERT time, so they are asserted on the
        # column definitions (and on the persisted rows in the cascade test).
        columns = Base.metadata.tables["buyer_memory_facts"].columns
        confidence_default = columns["confidence"].default
        source_default = columns["source"].default
        assert confidence_default is not None
        assert source_default is not None
        assert getattr(confidence_default, "arg", None) == 1.0
        assert getattr(source_default, "arg", None) == "chat"


class TestBuyerMemoryFactCascade:
    """Deleting a user takes its facts with it."""

    @pytest.mark.asyncio
    async def test_delete_user_cascades_facts(self, fk_session):
        user = User(email="buyer@example.com", full_name="Buyer")
        fk_session.add(user)
        await fk_session.flush()

        fact = BuyerMemoryFact(
            user_id=user.id,
            kind="budget",
            content="up to 500k",
        )
        fk_session.add(fact)
        fk_session.add(
            BuyerMemoryFact(
                user_id=user.id,
                kind="ruled_out_area",
                content="no Wola",
            )
        )
        await fk_session.commit()

        # Defaults land on the persisted row
        assert fact.confidence == 1.0
        assert fact.source == "chat"
        assert fact.listing_id is None
        assert fact.expires_at is None
        assert fact.created_at is not None

        count = await fk_session.scalar(
            select(func.count())
            .select_from(BuyerMemoryFact)
            .where(BuyerMemoryFact.user_id == user.id)
        )
        assert count == 2

        await fk_session.delete(user)
        await fk_session.commit()

        remaining = await fk_session.scalar(
            select(func.count())
            .select_from(BuyerMemoryFact)
            .where(BuyerMemoryFact.user_id == user.id)
        )
        assert remaining == 0
