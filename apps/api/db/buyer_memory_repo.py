"""
Buyer-memory repository.

Provides repository access to the BuyerMemoryFact model (Task #76): the durable
facts the assistant learned about a signed-in buyer. Every read and write of the
table goes through here, so the expiry rule and the ownership rule live in one
place.
"""

from datetime import UTC, datetime
from typing import Any, Optional, cast

from sqlalchemy import delete, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import attributes

from db.models import BuyerMemoryFact


def _utc_aware(value: Optional[datetime]) -> Optional[datetime]:
    """Return a datetime that is always timezone-aware and in UTC.

    SQLite keeps no timezone on a DATETIME column, so a value read back from
    SQLite is naive while the same value read from Postgres is aware. Every
    timestamp this repository hands out is UTC-aware, so a caller can compare
    it with `datetime.now(UTC)` on either backend.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def normalise_fact(fact: BuyerMemoryFact) -> BuyerMemoryFact:
    """Give a freshly read fact its UTC-aware timestamps back."""
    attributes.set_committed_value(fact, "created_at", _utc_aware(fact.created_at))
    attributes.set_committed_value(fact, "updated_at", _utc_aware(fact.updated_at))
    attributes.set_committed_value(fact, "expires_at", _utc_aware(fact.expires_at))
    return fact


class BuyerMemoryRepository:
    """Repository for BuyerMemoryFact model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_fact(
        self,
        user_id: str,
        kind: str,
        content: str,
        listing_id: Optional[str] = None,
        confidence: float = 1.0,
        source: str = "chat",
        expires_at: Optional[datetime] = None,
    ) -> BuyerMemoryFact:
        """Create a new buyer memory fact."""
        fact = BuyerMemoryFact(
            user_id=user_id,
            kind=kind,
            content=content,
            listing_id=listing_id,
            confidence=confidence,
            source=source,
            expires_at=expires_at,
        )
        self.session.add(fact)
        await self.session.flush()
        return fact

    async def get_fact(
        self, fact_id: str, user_id: Optional[str] = None
    ) -> Optional[BuyerMemoryFact]:
        """Get a fact by its ID, optionally scoped to one user."""
        stmt = select(BuyerMemoryFact).where(BuyerMemoryFact.id == fact_id)
        if user_id is not None:
            stmt = stmt.where(BuyerMemoryFact.user_id == user_id)
        result = await self.session.execute(stmt)
        fact = result.scalar_one_or_none()
        return normalise_fact(fact) if fact is not None else None

    async def list_for_user(
        self,
        user_id: str,
        kind: Optional[str] = None,
        include_expired: bool = False,
    ) -> list[BuyerMemoryFact]:
        """List a user's facts, newest first."""
        stmt = select(BuyerMemoryFact).where(BuyerMemoryFact.user_id == user_id)
        if kind is not None:
            stmt = stmt.where(BuyerMemoryFact.kind == kind)
        if not include_expired:
            stmt = stmt.where(
                (BuyerMemoryFact.expires_at.is_(None))
                | (BuyerMemoryFact.expires_at > datetime.now(UTC))
            )
        stmt = stmt.order_by(BuyerMemoryFact.created_at.desc())
        result = await self.session.execute(stmt)
        return [normalise_fact(fact) for fact in result.scalars().all()]

    async def delete_for_user(self, user_id: str) -> int:
        """Delete every fact of a user. Returns the number removed."""
        result = await self.session.execute(
            delete(BuyerMemoryFact).where(BuyerMemoryFact.user_id == user_id)
        )
        await self.session.flush()
        return cast(CursorResult, result).rowcount or 0

    async def purge_expired(self, now: Optional[datetime] = None) -> int:
        """Delete every fact whose retention has expired. Returns the number removed."""
        cutoff = now or datetime.now(UTC)
        result = await self.session.execute(
            delete(BuyerMemoryFact).where(
                BuyerMemoryFact.expires_at.is_not(None),
                BuyerMemoryFact.expires_at <= cutoff,
            )
        )
        await self.session.flush()
        return cast("CursorResult[Any]", result).rowcount or 0
