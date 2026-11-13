"""Integration tests for the buyer-memory service (Task #77).

These exercise the service through the real database session and the real
dependency wiring - the path the routers take - rather than through the
in-memory unit fixture.
"""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_buyer_memory_service
from db.models import BuyerMemoryFact, User
from services.buyer_memory_service import BuyerMemoryService


@pytest.fixture
async def buyer(db_session: AsyncSession) -> str:
    """A signed-in buyer."""
    user = User(email="buyer@example.com", full_name="Buyer")
    db_session.add(user)
    await db_session.flush()
    await db_session.commit()
    return user.id


@pytest.fixture
async def other_buyer(db_session: AsyncSession) -> str:
    """Another buyer, who must never see the first one's facts."""
    user = User(email="other@example.com", full_name="Other Buyer")
    db_session.add(user)
    await db_session.flush()
    await db_session.commit()
    return user.id


@pytest.fixture
def service(db_session: AsyncSession) -> BuyerMemoryService:
    """The service, wired the way a router wires it."""
    return get_buyer_memory_service(db_session)


class TestThroughTheDependency:
    """The service as the routers get it."""

    @pytest.mark.asyncio
    async def test_the_dependency_yields_a_service_on_the_session(self, db_session):
        service = get_buyer_memory_service(db_session)

        assert isinstance(service, BuyerMemoryService)
        assert service.session is db_session

    @pytest.mark.asyncio
    async def test_a_fact_survives_the_round_trip_to_the_database(self, service, buyer):
        await service.record_fact(
            user_id=buyer,
            kind="budget",
            content="up to 500k",
            listing_id="listing-123",
            confidence=0.9,
        )

        stored = await service.session.scalar(
            select(BuyerMemoryFact).where(BuyerMemoryFact.user_id == buyer)
        )

        assert stored is not None
        assert stored.kind == "budget"
        assert stored.content == "up to 500k"
        assert stored.listing_id == "listing-123"
        assert stored.confidence == 0.9
        assert stored.source == "chat"

    @pytest.mark.asyncio
    async def test_recalling_reads_the_database(self, service, buyer):
        await service.record_fact(user_id=buyer, kind="budget", content="up to 500k")

        recalled = await service.recall_for_user(user_id=buyer)

        assert [f.content for f in recalled] == ["up to 500k"]

    @pytest.mark.asyncio
    async def test_a_buyer_only_sees_their_own_facts(self, service, buyer, other_buyer):
        await service.record_fact(user_id=buyer, kind="budget", content="up to 500k")
        await service.record_fact(user_id=other_buyer, kind="budget", content="up to 900k")

        assert [f.content for f in await service.recall_for_user(user_id=buyer)] == ["up to 500k"]
        assert [f.content for f in await service.recall_for_user(user_id=other_buyer)] == [
            "up to 900k"
        ]

    @pytest.mark.asyncio
    async def test_deleting_removes_the_rows_from_the_database(self, service, buyer):
        await service.record_fact(user_id=buyer, kind="budget", content="up to 500k")

        removed = await service.delete_for_user(user_id=buyer)

        assert removed == 1
        remaining = await service.session.scalar(
            select(BuyerMemoryFact).where(BuyerMemoryFact.user_id == buyer)
        )
        assert remaining is None

    @pytest.mark.asyncio
    async def test_purging_removes_the_expired_rows(self, service, buyer):
        await service.record_fact(
            user_id=buyer,
            kind="note",
            content="looked at a loft",
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )
        await service.record_fact(user_id=buyer, kind="budget", content="up to 500k")

        removed = await service.purge_expired()

        assert removed == 1
        remaining = await service.session.scalar(
            select(BuyerMemoryFact).where(BuyerMemoryFact.user_id == buyer)
        )
        assert remaining is not None
        assert remaining.content == "up to 500k"

    @pytest.mark.asyncio
    async def test_a_repeated_fact_does_not_add_a_row(self, service, buyer):
        await service.record_fact(user_id=buyer, kind="budget", content="up to 500k")
        await service.record_fact(user_id=buyer, kind="budget", content="up to 500k")

        count = await service.session.scalar(
            select(BuyerMemoryFact).where(BuyerMemoryFact.user_id == buyer)
        )
        assert count is not None
        assert len(await service.repo.list_for_user(buyer)) == 1

    @pytest.mark.asyncio
    async def test_the_fact_is_found_by_its_id(self, service, buyer):
        recorded = await service.record_fact(user_id=buyer, kind="budget", content="up to 500k")

        found = await service.repo.get_fact(recorded.id, user_id=buyer)

        assert found is not None
        assert found.content == "up to 500k"

    @pytest.mark.asyncio
    async def test_an_expired_fact_is_not_recalled(self, service, buyer):
        await service.record_fact(
            user_id=buyer,
            kind="note",
            content="looked at a loft",
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )

        assert await service.recall_for_user(user_id=buyer) == []

    @pytest.mark.asyncio
    async def test_a_query_ranks_the_matching_fact_first(self, service, buyer):
        await service.record_fact(user_id=buyer, kind="budget", content="up to 500k")
        await service.record_fact(user_id=buyer, kind="requirement", content="needs a balcony")

        recalled = await service.recall_for_user(user_id=buyer, query="balcony")

        assert recalled[0].content == "needs a balcony"

    @pytest.mark.asyncio
    async def test_a_duplicate_row_in_the_database_is_recalled_once(self, service, buyer):
        await service.repo.add_fact(user_id=buyer, kind="budget", content="up to 500k")
        await service.repo.add_fact(user_id=buyer, kind="budget", content="up to 500k")
        await service.session.commit()

        assert len(await service.recall_for_user(user_id=buyer)) == 1

    @pytest.mark.asyncio
    async def test_a_fact_without_an_expiry_is_kept(self, service, buyer):
        await service.repo.add_fact(user_id=buyer, kind="note", content="no expiry on this one")
        await service.session.commit()

        recalled = await service.repo.list_for_user(buyer)

        assert [f.content for f in recalled] == ["no expiry on this one"]

    @pytest.mark.asyncio
    async def test_an_unknown_kind_is_refused(self, service, buyer):
        with pytest.raises(ValueError, match="kind"):
            await service.record_fact(user_id=buyer, kind="vibes", content="good vibes")

    @pytest.mark.asyncio
    async def test_an_unknown_source_is_refused(self, service, buyer):
        with pytest.raises(ValueError, match="source"):
            await service.record_fact(
                user_id=buyer, kind="note", content="a note", source="telepathy"
            )

    @pytest.mark.asyncio
    async def test_an_empty_fact_is_refused(self, service, buyer):
        with pytest.raises(ValueError, match="content"):
            await service.record_fact(user_id=buyer, kind="note", content="   ")

    @pytest.mark.asyncio
    async def test_a_naive_expiry_is_read_as_utc(self, service, buyer):
        naive = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=30)

        fact = await service.record_fact(
            user_id=buyer, kind="budget", content="up to 500k", expires_at=naive
        )

        assert fact.expires_at.tzinfo is not None

    @pytest.mark.asyncio
    async def test_an_expiry_in_another_zone_is_converted_to_utc(self, service, buyer):
        other_zone = timezone(timedelta(hours=2))
        expiry = datetime.now(other_zone) + timedelta(days=30)

        fact = await service.record_fact(
            user_id=buyer, kind="budget", content="up to 500k", expires_at=expiry
        )

        assert fact.expires_at.utcoffset() == timedelta(0)

    @pytest.mark.asyncio
    async def test_the_service_module_factory_yields_a_service(self, db_session):
        from services.buyer_memory_service import get_buyer_memory_service as factory

        assert isinstance(factory(db_session), BuyerMemoryService)
