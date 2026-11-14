"""Integration tests for the buyer's memory erasure (Task #82).

The guarantee under test: a buyer can see what the platform stored about
them, they can delete it, and stored facts do not live forever. The ownership
rule is the load-bearing part - the DELETE removes the caller's facts and
nobody else's.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from api.deps.auth import AuthCredentials, get_auth_credentials
from api.routers import buyer_memory
from db.database import Base, create_engine, get_db
from db.models import BuyerMemoryFact, User
from services.buyer_memory_service import BuyerMemoryService


@pytest.fixture
async def fk_session() -> AsyncGenerator[AsyncSession, None]:
    """A session whose SQLite connection enforces foreign keys.

    SQLite ignores ON DELETE CASCADE unless PRAGMA foreign_keys=ON is set per
    connection, so the account-deletion cascade cannot be proved without it.
    """
    engine = create_engine(
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


async def _create_user(session: AsyncSession, email: str) -> User:
    """Create a buyer and return it."""
    user = User(email=email, full_name=email.split("@")[0], is_active=True)
    session.add(user)
    await session.flush()
    return user


async def _count_facts(session: AsyncSession, user_id: str) -> int:
    """Count the facts of one buyer."""
    count = await session.scalar(
        select(func.count()).select_from(BuyerMemoryFact).where(BuyerMemoryFact.user_id == user_id)
    )
    return int(count or 0)


def _scheduler():
    """A scheduler without the notification services this test does not use.

    The constructor wires the mail service, the preferences manager and the
    alert history; the retention job needs none of them.
    """
    from notifications.scheduler import NotificationScheduler

    scheduler = NotificationScheduler.__new__(NotificationScheduler)
    scheduler._buyer_memory_purge_interval_seconds = 3600
    scheduler._last_buyer_memory_purge = None
    return scheduler


@asynccontextmanager
async def _client(session: AsyncSession, user: User):
    """A client whose authenticated caller is `user`."""
    from fastapi import FastAPI

    test_app = FastAPI()
    test_app.include_router(buyer_memory.router, prefix="/api/v1")

    async def override_get_db():
        yield session

    async def override_get_auth_credentials():
        return AuthCredentials(user, {"roles": ["user"]})

    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[get_auth_credentials] = override_get_auth_credentials

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@asynccontextmanager
async def _unauthenticated_client(session: AsyncSession):
    """A client with the REAL authentication dependency - no override.

    The demo bypass is deliberately LEFT ON: the self-hosted demo stack sets
    DEMO_MODE without DEMO_USER_BYPASS, so the bypass follows it and the
    synthetic demo user answers an anonymous request everywhere else. A
    personal memory must not be listable or erasable by whoever walks in, so
    the endpoints ask for a real token - and this client proves it.
    """
    from fastapi import FastAPI

    from api.routers import settings as settings_router
    from config.settings import get_settings

    settings = get_settings()
    previous_bypass = settings.demo_user_bypass
    previous_sessions = dict(settings_router._DEMO_MODE_SESSIONS)
    settings.demo_user_bypass = True
    settings_router._DEMO_MODE_SESSIONS.clear()

    test_app = FastAPI()
    test_app.include_router(buyer_memory.router, prefix="/api/v1")

    async def override_get_db():
        yield session

    test_app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=test_app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        settings.demo_user_bypass = previous_bypass
        settings_router._DEMO_MODE_SESSIONS.clear()
        settings_router._DEMO_MODE_SESSIONS.update(previous_sessions)


class TestBuyerMemoryAuthentication:
    """The endpoints are behind a real token - an anonymous caller gets nothing."""

    @pytest.mark.asyncio
    async def test_an_unauthenticated_request_gets_401(self, fk_session: AsyncSession):
        async with _unauthenticated_client(fk_session) as client:
            listing = await client.get("/api/v1/me/buyer-memory")
            deletion = await client.delete("/api/v1/me/buyer-memory")

        assert listing.status_code == 401
        assert deletion.status_code == 401


class TestBuyerMemoryErasure:
    """The DELETE removes the caller's facts and nobody else's."""

    @pytest.mark.asyncio
    async def test_delete_removes_only_the_callers_facts(self, fk_session: AsyncSession):
        """The caller's facts go; the other buyer's facts stay."""
        caller = await _create_user(fk_session, "caller@example.com")
        other = await _create_user(fk_session, "other@example.com")

        service = BuyerMemoryService(fk_session)
        await service.record_fact(caller.id, "budget", "up to 500k")
        await service.record_fact(caller.id, "ruled_out_area", "no Wola")
        await service.record_fact(other.id, "budget", "up to 900k")
        await fk_session.commit()

        async with _client(fk_session, caller) as client:
            # The buyer sees what is stored before deleting it.
            listing = await client.get("/api/v1/me/buyer-memory")
            assert listing.status_code == 200
            listed = listing.json()
            assert listed["count"] == 2
            assert {fact["content"] for fact in listed["facts"]} == {"up to 500k", "no Wola"}

            response = await client.delete("/api/v1/me/buyer-memory")

        assert response.status_code == 200
        assert response.json()["deleted"] == 2

        assert await _count_facts(fk_session, caller.id) == 0
        assert await _count_facts(fk_session, other.id) == 1

    @pytest.mark.asyncio
    async def test_delete_ignores_a_user_id_in_the_request(self, fk_session: AsyncSession):
        """A user id in the query or the body cannot widen the scope."""
        caller = await _create_user(fk_session, "caller@example.com")
        other = await _create_user(fk_session, "other@example.com")

        service = BuyerMemoryService(fk_session)
        await service.record_fact(caller.id, "budget", "up to 500k")
        await service.record_fact(other.id, "budget", "up to 900k")
        await fk_session.commit()

        async with _client(fk_session, caller) as client:
            response = await client.request(
                "DELETE",
                "/api/v1/me/buyer-memory",
                params={"user_id": other.id},
                json={"user_id": other.id},
            )

        assert response.status_code == 200
        # Only the caller's one fact is removed.
        assert response.json()["deleted"] == 1
        assert await _count_facts(fk_session, caller.id) == 0
        assert await _count_facts(fk_session, other.id) == 1


class TestBuyerMemoryExpiry:
    """Stored facts do not live forever."""

    @pytest.mark.asyncio
    async def test_expired_fact_is_never_returned(self, fk_session: AsyncSession):
        """A fact past its retention is never shown."""
        caller = await _create_user(fk_session, "caller@example.com")

        service = BuyerMemoryService(fk_session)
        await service.record_fact(caller.id, "budget", "up to 500k")
        await service.record_fact(
            caller.id,
            "note",
            "the flat with the green door",
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )
        await fk_session.commit()

        async with _client(fk_session, caller) as client:
            response = await client.get("/api/v1/me/buyer-memory")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert [fact["content"] for fact in data["facts"]] == ["up to 500k"]

    @pytest.mark.asyncio
    async def test_expired_fact_is_removed_by_the_purge(self, fk_session: AsyncSession):
        """The retention job removes the row itself."""
        caller = await _create_user(fk_session, "caller@example.com")

        service = BuyerMemoryService(fk_session)
        await service.record_fact(
            caller.id,
            "note",
            "the flat with the green door",
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )
        await fk_session.commit()
        assert await _count_facts(fk_session, caller.id) == 1

        purged = await service.purge_expired()

        assert purged == 1
        assert await _count_facts(fk_session, caller.id) == 0


class TestBuyerMemoryPurgeJob:
    """The scheduler removes what is past its retention."""

    @pytest.mark.asyncio
    async def test_purge_job_removes_expired_facts(
        self, fk_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ):
        """The retention job deletes the expired row and keeps the live one."""
        from db import database as db_database

        user = await _create_user(fk_session, "caller@example.com")

        service = BuyerMemoryService(fk_session)
        await service.record_fact(user.id, "budget", "up to 500k")
        await service.record_fact(
            user.id,
            "note",
            "the flat with the green door",
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )
        await fk_session.commit()

        @asynccontextmanager
        async def _fake_db_context():
            yield fk_session

        monkeypatch.setattr(db_database, "get_db_context", _fake_db_context)

        scheduler = _scheduler()
        stats = await scheduler._purge_buyer_memory_async()

        assert stats["purged"] == 1
        assert await _count_facts(fk_session, user.id) == 1

    def test_purge_job_waits_for_its_interval(self):
        """The job skips a second run inside its hour."""
        scheduler = _scheduler()
        scheduler._last_buyer_memory_purge = datetime.now()

        stats = scheduler._run_buyer_memory_purge(datetime.now())

        assert stats["purged"] == 0
        assert stats["reason"] == "interval_not_elapsed"


class TestBuyerMemoryAccountDeletion:
    """Deleting the account takes the memory with it."""

    @pytest.mark.asyncio
    async def test_account_deletion_removes_the_facts(self, fk_session: AsyncSession):
        """The cascade removes the facts, and the endpoint shows nothing."""
        user = await _create_user(fk_session, "gone@example.com")

        service = BuyerMemoryService(fk_session)
        await service.record_fact(user.id, "budget", "up to 500k")
        await fk_session.commit()
        assert await _count_facts(fk_session, user.id) == 1

        await fk_session.delete(user)
        await fk_session.commit()

        assert await _count_facts(fk_session, user.id) == 0

        # And through the endpoints: there is nothing left to show or delete.
        async with _client(fk_session, user) as client:
            listing = await client.get("/api/v1/me/buyer-memory")
            assert listing.status_code == 200
            assert listing.json() == {"facts": [], "count": 0}

            response = await client.delete("/api/v1/me/buyer-memory")
            assert response.status_code == 200
            assert response.json()["deleted"] == 0
