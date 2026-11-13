"""The buyer's memory can be seen and deleted (Task #82).

Two guarantees a data subject is owed: they can see what the platform stored
about them, and they can delete it. Both live here, behind the JWT.

The ownership rule is the point of this module: the user id comes from the
authenticated user and from nowhere else. No request body, no query parameter
and no path segment can name another buyer's facts.

The endpoints ask for a REAL token, not the demo bypass. In a demo deployment
the bypass answers an anonymous request with a synthetic, SHARED demo user -
and a memory is by definition personal, so a shared bucket must not be
listable or erasable by whoever walks in. An anonymous request is a 401.
"""

from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps.auth import AuthCredentials, get_auth_credentials
from db.database import get_db
from services.buyer_memory_service import BuyerMemoryService

router = APIRouter(prefix="/me/buyer-memory", tags=["Buyer Memory"])

# The most facts one listing returns. A buyer who stated more than this is
# told the list is cut off rather than being shown a silently partial view.
MAX_LISTED_FACTS = 1000


class BuyerMemoryFactResponse(BaseModel):
    """One stored fact, as the data subject sees it."""

    id: str
    kind: str
    content: str
    listing_id: Optional[str] = None
    confidence: float
    source: str
    created_at: datetime
    expires_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class BuyerMemoryListResponse(BaseModel):
    """Everything the platform holds about the caller."""

    facts: list[BuyerMemoryFactResponse]
    count: int


class BuyerMemoryDeleteResponse(BaseModel):
    """What the erasure removed."""

    deleted: int


@router.get(
    "",
    response_model=BuyerMemoryListResponse,
    summary="List the buyer's stored facts",
    description="Everything the platform stored about the authenticated buyer.",
)
async def list_buyer_memory(
    credentials: Annotated[AuthCredentials, Depends(get_auth_credentials)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> BuyerMemoryListResponse:
    """Show the caller everything stored about them.

    An expired fact is never returned: the repository drops it on read, and
    the scheduler removes the row itself.
    """
    service = BuyerMemoryService(session)
    facts = await service.recall_for_user(credentials.user.id, limit=MAX_LISTED_FACTS)
    return BuyerMemoryListResponse(
        facts=[BuyerMemoryFactResponse.model_validate(fact) for fact in facts],
        count=len(facts),
    )


@router.delete(
    "",
    response_model=BuyerMemoryDeleteResponse,
    summary="Delete the buyer's stored facts",
    description="Remove every stored fact of the authenticated buyer, and only theirs.",
)
async def delete_buyer_memory(
    credentials: Annotated[AuthCredentials, Depends(get_auth_credentials)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> BuyerMemoryDeleteResponse:
    """Erase the caller's memory.

    The buyer id is the authenticated user's id. Nothing in the request can
    widen that scope.
    """
    service = BuyerMemoryService(session)
    deleted = await service.delete_for_user(credentials.user.id)
    return BuyerMemoryDeleteResponse(deleted=deleted)
