"""Tests for the DB-backed audit logging system (Task #95)."""

from datetime import UTC, datetime

import pytest

from db.models import AuditLogEntry
from db.repositories import AuditLogRepository
from db.schemas import (
    AuditLogEntryResponse,
    AuditLogListResponse,
    ChainVerificationResponse,
)
from services.audit_service import AuditService


class TestAuditLogEntryModel:
    """Tests for the AuditLogEntry SQLAlchemy model."""

    def test_compute_hash_deterministic(self):
        """compute_hash must produce the same output for the same input."""
        entry = AuditLogEntry(
            id="test-id-1",
            actor_id="u1",
            action="login",
            resource="auth/session",
            ip_address="127.0.0.1",
        )
        h1 = entry.compute_hash("prev123")
        h2 = entry.compute_hash("prev123")
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex digest

    def test_compute_hash_changes_with_prev(self):
        """Different prev_hash must produce different entry_hash."""
        entry = AuditLogEntry(
            id="test-id-2",
            actor_id="u1",
            action="login",
        )
        h1 = entry.compute_hash("aaa")
        h2 = entry.compute_hash("bbb")
        assert h1 != h2


class TestAuditLogRepository:
    """Tests for AuditLogRepository against in-memory SQLite."""

    @pytest.mark.asyncio
    async def test_append_first_entry(self, db_session):
        repo = AuditLogRepository(db_session)
        entry = await repo.append(
            action="user.login",
            actor_id="user-1",
            actor_email="alice@example.com",
            resource="auth/session",
            ip_address="10.0.0.1",
        )
        await db_session.commit()

        assert entry.id is not None
        assert entry.action == "user.login"
        assert entry.prev_hash == ""  # First entry has empty prev_hash
        assert entry.entry_hash is not None
        assert len(entry.entry_hash) == 64

    @pytest.mark.asyncio
    async def test_append_chains_hashes(self, db_session):
        repo = AuditLogRepository(db_session)

        e1 = await repo.append(action="action.a")
        await db_session.commit()

        e2 = await repo.append(action="action.b")
        await db_session.commit()

        assert e2.prev_hash == e1.entry_hash
        assert e2.entry_hash != e1.entry_hash

    @pytest.mark.asyncio
    async def test_query_with_filters(self, db_session):
        repo = AuditLogRepository(db_session)
        await repo.append(action="login", actor_id="u1")
        await repo.append(action="logout", actor_id="u1")
        await repo.append(action="login", actor_id="u2")
        await db_session.commit()

        entries, total = await repo.query(action="login")
        assert total == 2

        entries, total = await repo.query(actor_id="u1")
        assert total == 2

        entries, total = await repo.query(action="login", actor_id="u2")
        assert total == 1

    @pytest.mark.asyncio
    async def test_query_pagination(self, db_session):
        repo = AuditLogRepository(db_session)
        for i in range(5):
            await repo.append(action=f"action.{i}")
        await db_session.commit()

        entries, total = await repo.query(limit=2, offset=0)
        assert total == 5
        assert len(entries) == 2

        entries2, _ = await repo.query(limit=2, offset=2)
        assert len(entries2) == 2
        # Different pages must not overlap
        assert entries[0].id != entries2[0].id

    @pytest.mark.asyncio
    async def test_verify_chain_valid(self, db_session):
        repo = AuditLogRepository(db_session)
        for i in range(5):
            await repo.append(action=f"action.{i}")
        await db_session.commit()

        result = await repo.verify_chain()
        assert result["valid"] is True
        assert result["checked_count"] == 5
        assert result["broken_count"] == 0

    @pytest.mark.asyncio
    async def test_verify_chain_detects_tamper(self, db_session):
        repo = AuditLogRepository(db_session)
        await repo.append(action="original")
        await db_session.commit()

        # Tamper with the entry hash directly
        from sqlalchemy import update

        await db_session.execute(update(AuditLogEntry).values(entry_hash="tampered_hash"))
        await db_session.commit()

        result = await repo.verify_chain()
        assert result["valid"] is False
        assert result["broken_count"] >= 1

    @pytest.mark.asyncio
    async def test_get_by_id(self, db_session):
        repo = AuditLogRepository(db_session)
        entry = await repo.append(action="test.action")
        await db_session.commit()

        found = await repo.get_by_id(entry.id)
        assert found is not None
        assert found.action == "test.action"

        assert await repo.get_by_id("nonexistent") is None


class TestAuditService:
    """Tests for AuditService business logic."""

    @pytest.mark.asyncio
    async def test_log_creates_entry(self, db_session):
        service = AuditService(db_session)
        await service.log(
            action="document.upload",
            actor_id="user-1",
            resource="documents/doc-123",
            details={"filename": "contract.pdf"},
        )

        repo = AuditLogRepository(db_session)
        entries, total = await repo.query()
        assert total == 1
        assert entries[0].action == "document.upload"

    @pytest.mark.asyncio
    async def test_log_failure_does_not_raise(self, db_session):
        """Audit failures must never propagate to callers."""
        service = AuditService(db_session)
        # Force a closed session to trigger an error
        await db_session.close()
        # This should NOT raise
        await service.log(action="should.not.crash")
        # If we reach here, the test passes


class TestAuditSchemas:
    """Tests for audit Pydantic schemas."""

    def test_entry_response_schema(self):
        data = {
            "id": "abc-123",
            "actor_id": "u1",
            "actor_email": "a@b.com",
            "actor_role": "admin",
            "action": "user.login",
            "resource": "auth/session",
            "details": {"ip": "1.2.3.4"},
            "ip_address": "1.2.3.4",
            "user_agent": "TestAgent/1.0",
            "request_id": "req-001",
            "prev_hash": "a" * 64,
            "entry_hash": "b" * 64,
            "created_at": datetime.now(UTC),
        }
        resp = AuditLogEntryResponse(**data)
        assert resp.action == "user.login"
        assert resp.id == "abc-123"

    def test_list_response_schema(self):
        resp = AuditLogListResponse(
            items=[],
            total=0,
            limit=100,
            offset=0,
        )
        assert resp.total == 0
        assert resp.items == []

    def test_chain_verification_schema(self):
        resp = ChainVerificationResponse(
            valid=True,
            checked_count=50,
            broken_count=0,
            broken_entries=[],
        )
        assert resp.valid is True


@pytest.fixture(autouse=True)
async def _the_test_actors_exist(create_test_users):
    """The actors the entries name have to be real rows.

    The deployment enforces foreign keys, and an audit entry names the actor
    that wrote it - so the actor has to exist for the entry to be writable.
    """
    await create_test_users("u1", "u2", "user-1")
