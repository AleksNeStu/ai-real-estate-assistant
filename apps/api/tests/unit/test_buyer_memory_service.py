"""Tests for the buyer-memory service (Task #77)."""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import User
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
    """The buyer memory service."""
    return BuyerMemoryService(db_session)


class TestRecallForUser:
    """What the buyer remembers."""

    @pytest.mark.asyncio
    async def test_a_written_fact_comes_back(self, service, buyer):
        await service.record_fact(user_id=buyer, kind="budget", content="up to 500k")

        recalled = await service.recall_for_user(user_id=buyer)

        assert len(recalled) == 1
        assert recalled[0].kind == "budget"
        assert recalled[0].content == "up to 500k"

    @pytest.mark.asyncio
    async def test_a_fact_of_another_user_never_comes_back(self, service, buyer, other_buyer):
        await service.record_fact(user_id=buyer, kind="budget", content="up to 500k")
        await service.record_fact(user_id=other_buyer, kind="budget", content="up to 900k")

        recalled = await service.recall_for_user(user_id=buyer)

        assert len(recalled) == 1
        assert recalled[0].content == "up to 500k"

    @pytest.mark.asyncio
    async def test_an_expired_fact_is_dropped(self, service, buyer):
        await service.record_fact(
            user_id=buyer,
            kind="note",
            content="looked at a loft",
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )
        await service.record_fact(user_id=buyer, kind="budget", content="up to 500k")

        recalled = await service.recall_for_user(user_id=buyer)

        assert [f.content for f in recalled] == ["up to 500k"]

    @pytest.mark.asyncio
    async def test_no_facts_gives_an_empty_recall(self, service, buyer):
        assert await service.recall_for_user(user_id=buyer) == []

    @pytest.mark.asyncio
    async def test_the_newest_fact_comes_first(self, service, buyer):
        first = await service.record_fact(
            user_id=buyer, kind="requirement", content="needs a balcony"
        )
        second = await service.record_fact(
            user_id=buyer, kind="requirement", content="needs a parking spot"
        )
        # The two facts share a created_at second - pin the order explicitly.
        first.created_at = datetime(2026, 1, 1, tzinfo=UTC)
        second.created_at = datetime(2026, 1, 2, tzinfo=UTC)
        await service.session.commit()

        recalled = await service.recall_for_user(user_id=buyer)

        assert [f.content for f in recalled] == [
            "needs a parking spot",
            "needs a balcony",
        ]

    @pytest.mark.asyncio
    async def test_the_limit_is_respected(self, service, buyer):
        for i in range(5):
            await service.record_fact(user_id=buyer, kind="note", content=f"note {i}")

        assert len(await service.recall_for_user(user_id=buyer, limit=2)) == 2

    @pytest.mark.asyncio
    async def test_a_query_ranks_the_matching_fact_first(self, service, buyer):
        await service.record_fact(user_id=buyer, kind="budget", content="up to 500k")
        await service.record_fact(user_id=buyer, kind="requirement", content="needs a balcony")

        recalled = await service.recall_for_user(user_id=buyer, query="balcony")

        assert recalled[0].content == "needs a balcony"


class TestRecordFact:
    """What the buyer said."""

    @pytest.mark.asyncio
    async def test_a_repeated_fact_does_not_pile_up(self, service, buyer):
        first = await service.record_fact(user_id=buyer, kind="budget", content="up to 500k")
        second = await service.record_fact(user_id=buyer, kind="budget", content="up to 500k")

        assert first.id == second.id
        assert len(await service.recall_for_user(user_id=buyer)) == 1

    @pytest.mark.asyncio
    async def test_a_repeated_fact_with_different_spelling_is_the_same_fact(self, service, buyer):
        first = await service.record_fact(user_id=buyer, kind="budget", content="up to 500k")
        second = await service.record_fact(user_id=buyer, kind="budget", content="  Up   to 500K ")

        assert first.id == second.id
        assert len(await service.recall_for_user(user_id=buyer)) == 1

    @pytest.mark.asyncio
    async def test_the_same_content_in_another_kind_is_another_fact(self, service, buyer):
        await service.record_fact(user_id=buyer, kind="budget", content="500k")
        await service.record_fact(user_id=buyer, kind="note", content="500k")

        assert len(await service.recall_for_user(user_id=buyer)) == 2

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
    async def test_the_fact_carries_its_listing_and_confidence(self, service, buyer):
        fact = await service.record_fact(
            user_id=buyer,
            kind="liked",
            content="the loft with the view",
            listing_id="listing-123",
            confidence=0.8,
        )

        assert fact.listing_id == "listing-123"
        assert fact.confidence == 0.8
        assert fact.source == "chat"

    @pytest.mark.asyncio
    async def test_a_fact_carries_the_retention_window(self, service, buyer):
        fact = await service.record_fact(user_id=buyer, kind="budget", content="up to 500k")

        assert fact.expires_at is not None
        assert fact.expires_at > datetime.now(UTC)

    @pytest.mark.asyncio
    async def test_an_explicit_expiry_wins_over_the_retention_window(self, service, buyer):
        expiry = datetime.now(UTC) + timedelta(days=7)

        fact = await service.record_fact(
            user_id=buyer, kind="budget", content="up to 500k", expires_at=expiry
        )

        assert fact.expires_at == expiry


class TestDeleteForUser:
    """What the buyer can take back."""

    @pytest.mark.asyncio
    async def test_delete_for_user_empties_the_set(self, service, buyer):
        await service.record_fact(user_id=buyer, kind="budget", content="up to 500k")
        await service.record_fact(user_id=buyer, kind="requirement", content="needs a balcony")

        removed = await service.delete_for_user(user_id=buyer)

        assert removed == 2
        assert await service.recall_for_user(user_id=buyer) == []

    @pytest.mark.asyncio
    async def test_delete_for_user_removes_only_the_callers_facts(
        self, service, buyer, other_buyer
    ):
        await service.record_fact(user_id=buyer, kind="budget", content="up to 500k")
        await service.record_fact(user_id=other_buyer, kind="budget", content="up to 900k")

        removed = await service.delete_for_user(user_id=buyer)

        assert removed == 1
        assert await service.recall_for_user(user_id=other_buyer) != []


class TestPurgeExpired:
    """The retention rule."""

    @pytest.mark.asyncio
    async def test_purge_expired_removes_only_what_expired(self, service, buyer):
        await service.record_fact(
            user_id=buyer,
            kind="note",
            content="looked at a loft",
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )
        await service.record_fact(
            user_id=buyer,
            kind="budget",
            content="up to 500k",
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )
        await service.record_fact(user_id=buyer, kind="requirement", content="needs a balcony")

        removed = await service.purge_expired()

        assert removed == 1
        recalled = await service.recall_for_user(user_id=buyer)
        assert [f.content for f in recalled] == ["needs a balcony", "up to 500k"]


class TestRepository:
    """The repository under the service."""

    @pytest.mark.asyncio
    async def test_get_fact_returns_the_fact(self, service, buyer):
        recorded = await service.record_fact(user_id=buyer, kind="budget", content="up to 500k")

        found = await service.repo.get_fact(recorded.id)

        assert found is not None
        assert found.id == recorded.id

    @pytest.mark.asyncio
    async def test_get_fact_scoped_to_a_user_keeps_the_others_out(
        self, service, buyer, other_buyer
    ):
        recorded = await service.record_fact(user_id=buyer, kind="budget", content="up to 500k")

        assert await service.repo.get_fact(recorded.id, user_id=other_buyer) is None
        assert await service.repo.get_fact(recorded.id, user_id=buyer) is not None

    @pytest.mark.asyncio
    async def test_get_fact_of_an_unknown_id_is_none(self, service):
        assert await service.repo.get_fact("does-not-exist") is None

    @pytest.mark.asyncio
    async def test_a_fact_without_an_expiry_is_kept(self, service, buyer):
        fact = await service.repo.add_fact(
            user_id=buyer, kind="note", content="no expiry on this one"
        )
        await service.session.commit()

        recalled = await service.repo.list_for_user(buyer)

        assert [f.id for f in recalled] == [fact.id]

    @pytest.mark.asyncio
    async def test_expired_facts_are_kept_when_asked_for(self, service, buyer):
        await service.record_fact(
            user_id=buyer,
            kind="note",
            content="looked at a loft",
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )

        assert len(await service.repo.list_for_user(buyer, include_expired=True)) == 1


class TestNormalisation:
    """The timestamps the callers receive."""

    @pytest.mark.asyncio
    async def test_a_recalled_fact_carries_utc_aware_timestamps(self, service, buyer):
        await service.record_fact(user_id=buyer, kind="budget", content="up to 500k")

        recalled = await service.recall_for_user(user_id=buyer)

        assert recalled[0].created_at.tzinfo is not None
        assert recalled[0].expires_at.tzinfo is not None

    @pytest.mark.asyncio
    async def test_a_naive_expiry_is_read_as_utc(self, service, buyer):
        naive = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=30)

        fact = await service.record_fact(
            user_id=buyer, kind="budget", content="up to 500k", expires_at=naive
        )

        assert fact.expires_at.tzinfo is not None
        assert fact.expires_at.replace(tzinfo=None) == naive

    @pytest.mark.asyncio
    async def test_an_expiry_in_another_zone_is_converted_to_utc(self, service, buyer):
        other_zone = timezone(timedelta(hours=2))
        expiry = datetime.now(other_zone) + timedelta(days=30)

        fact = await service.record_fact(
            user_id=buyer, kind="budget", content="up to 500k", expires_at=expiry
        )

        assert fact.expires_at.utcoffset() == timedelta(0)


class TestDeduplication:
    """Two rows with the same content are one fact."""

    @pytest.mark.asyncio
    async def test_a_duplicate_row_in_the_database_is_recalled_once(self, service, buyer):
        # A row written by an earlier version of the writer, before the service
        # deduplicated on the way in.
        await service.repo.add_fact(user_id=buyer, kind="budget", content="up to 500k")
        await service.repo.add_fact(user_id=buyer, kind="budget", content="up to 500k")
        await service.session.commit()

        recalled = await service.recall_for_user(user_id=buyer)

        assert len(recalled) == 1


class TestDependency:
    """The wiring the routers use."""

    def test_the_dependency_returns_a_service(self, db_session):
        from api.dependencies import get_buyer_memory_service

        assert isinstance(get_buyer_memory_service(db_session), BuyerMemoryService)

    def test_the_service_module_factory_returns_a_service(self, db_session):
        from services.buyer_memory_service import get_buyer_memory_service

        assert isinstance(get_buyer_memory_service(db_session), BuyerMemoryService)
