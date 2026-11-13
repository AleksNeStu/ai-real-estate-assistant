"""
Service for the buyer's durable memory.

This service owns every read and write of the buyer's memory (Task #77). The
extractor, the write path and the read path all come through here - nothing else
touches the table.

A buyer memory is a set of durable facts: what the buyer has already told us
about their budget, the areas they ruled out, what they liked about a listing.
"""

import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from db.buyer_memory_repo import BuyerMemoryRepository, normalise_fact
from db.models import BuyerMemoryFact

logger = logging.getLogger(__name__)

# The closed set of kinds a fact can carry.
VALID_KINDS = frozenset({"budget", "ruled_out_area", "liked", "disliked", "requirement", "note"})

# The closed set of sources a fact can come from.
VALID_SOURCES = frozenset({"chat", "manual", "derived"})

_WHITESPACE = re.compile(r"\s+")
_TOKEN = re.compile(r"[\w']+", re.UNICODE)


def normalise_content(content: str) -> str:
    """Normalise a fact's content for the duplicate check."""
    return _WHITESPACE.sub(" ", content or "").strip().lower()


def _tokens(text: str) -> set[str]:
    """Split a text into lowercase word tokens."""
    return {t for t in _TOKEN.findall((text or "").lower()) if t}


class BuyerMemoryService:
    """Service for the buyer's durable facts."""

    # How long a fact is kept before it expires.
    DEFAULT_RETENTION_DAYS = 365

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = BuyerMemoryRepository(session)

    async def record_fact(
        self,
        user_id: str,
        kind: str,
        content: str,
        listing_id: Optional[str] = None,
        confidence: float = 1.0,
        source: str = "chat",
        expires_at: Optional[datetime] = None,
    ) -> BuyerMemoryFact:
        """
        Record one durable fact about a buyer.

        A repeated fact does not pile up: when the buyer already has a fact of
        the same kind with the same content, that fact is returned unchanged.

        Args:
            user_id: The buyer's user ID.
            kind: One of VALID_KINDS.
            content: The fact in the buyer's own words.
            listing_id: The property the fact refers to, when it refers to one.
            confidence: How sure the extractor was (0-1).
            source: One of VALID_SOURCES.
            expires_at: When the fact stops being recalled. Defaults to the
                retention window.

        Returns:
            The stored fact.
        """
        if kind not in VALID_KINDS:
            raise ValueError(f"Unknown buyer memory kind: {kind!r}")
        if source not in VALID_SOURCES:
            raise ValueError(f"Unknown buyer memory source: {source!r}")

        normalised = normalise_content(content)
        if not normalised:
            raise ValueError("A buyer memory fact needs content")

        existing = await self._find_duplicate(user_id, kind, normalised)
        if existing is not None:
            logger.debug("Buyer memory fact already recorded, not duplicated")
            return existing

        if expires_at is None:
            expires_at = datetime.now(UTC) + timedelta(days=self.DEFAULT_RETENTION_DAYS)
        else:
            # SQLite keeps no timezone on a DATETIME column, so the wall clock
            # that lands in the column is the one stored. Normalising to UTC
            # here keeps the stored value comparable with datetime.now(UTC).
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            else:
                expires_at = expires_at.astimezone(UTC)

        fact = await self.repo.add_fact(
            user_id=user_id,
            kind=kind,
            content=content,
            listing_id=listing_id,
            confidence=confidence,
            source=source,
            expires_at=expires_at,
        )
        await self.session.commit()
        await self.session.refresh(fact)
        return normalise_fact(fact)

    async def recall_for_user(
        self,
        user_id: str,
        query: Optional[str] = None,
        limit: int = 10,
    ) -> list[BuyerMemoryFact]:
        """
        Recall the facts that matter for this buyer.

        Args:
            user_id: The buyer's user ID.
            query: The current question, used to rank the facts. Optional.
            limit: The maximum number of facts to return.

        Returns:
            The buyer's facts - expired ones dropped, one row per
            (kind, normalised content), newest first.
        """
        facts = await self.repo.list_for_user(user_id)

        # One row per (kind, normalised content). list_for_user is newest first,
        # so the first occurrence is the newest one.
        seen: set[tuple[str, str]] = set()
        unique: list[BuyerMemoryFact] = []
        for fact in facts:
            key = (fact.kind, normalise_content(fact.content))
            if key in seen:
                continue
            seen.add(key)
            unique.append(fact)

        if query:
            query_tokens = _tokens(query)
            unique.sort(key=lambda f: -len(query_tokens & _tokens(f.content)))

        return unique[:limit]

    async def delete_for_user(self, user_id: str) -> int:
        """
        Delete every fact of a buyer.

        Args:
            user_id: The buyer's user ID.

        Returns:
            The number of facts removed.
        """
        removed = await self.repo.delete_for_user(user_id)
        await self.session.commit()
        return removed

    async def purge_expired(self, now: Optional[datetime] = None) -> int:
        """
        Delete every fact whose retention has expired.

        Args:
            now: The moment to judge expiry against. Defaults to now.

        Returns:
            The number of facts removed.
        """
        removed = await self.repo.purge_expired(now)
        await self.session.commit()
        return removed

    async def _find_duplicate(
        self, user_id: str, kind: str, normalised_content: str
    ) -> Optional[BuyerMemoryFact]:
        """Find an existing fact of the same kind with the same content."""
        for fact in await self.repo.list_for_user(user_id, kind=kind):
            if normalise_content(fact.content) == normalised_content:
                return fact
        return None


# Dependency injection helper
def get_buyer_memory_service(session: AsyncSession) -> BuyerMemoryService:
    """Get a BuyerMemoryService instance."""
    return BuyerMemoryService(session)
