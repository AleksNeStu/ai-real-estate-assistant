"""Outbound clicks.

A click that leaves the site cannot be measured on the server: the browser
is gone before the request could be counted. The browser therefore reports
the click here, before it follows the link, and the record lands in the same
lead pipeline as every other interaction - so "which line of the landing
brought the studio inquiry" is a question the data can answer.
"""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db.schemas import OutboundClickRequest
from services.lead_tracking import LeadTrackingService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.post(
    "/outbound",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Record an outbound click",
    description="Records a click that leaves the site: the target, the slot and the campaign.",
)
async def record_outbound_click(
    body: OutboundClickRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> None:
    """Record the click."""
    tracking_service = LeadTrackingService(session)

    await tracking_service.track_interaction(
        visitor_id=body.visitor_id,
        interaction_type="navigation",
        metadata={"target": body.target, "slot": body.slot, "campaign": body.campaign},
        page_url=body.page_url,
        referrer=request.headers.get("referer"),
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
