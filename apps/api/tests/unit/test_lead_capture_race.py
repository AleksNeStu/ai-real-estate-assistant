"""Two requests for one visitor must not end in a 500.

The lead capture is a read-then-write: the landing page tracks an interaction
and the waitlist form captures the same visitor, and two requests for one
visitor can arrive at the same time. Both read "no row yet", both write, and
the loser of the race dies on the UNIQUE constraint - a 500 for a visitor who
did nothing wrong. The demo's own log carried those 500s (about two in ten
minutes) before this was fixed.

The fix reads back the row the other request wrote and returns it, so the
loser of the race answers the visitor normally.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.routers import leads
from db.database import get_db
from db.lead_repos import LeadRepository
from db.models import Lead
from services.lead_tracking import LeadTrackingService


def _collision() -> IntegrityError:
    """The error the second write of one visitor raises."""
    return IntegrityError("INSERT", {}, Exception("UNIQUE constraint failed: leads.visitor_id"))


@pytest.fixture
def mock_session():
    session = MagicMock(spec=AsyncSession)
    session.flush = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def mock_lead_repo():
    repo = MagicMock()
    repo.get_or_create_by_visitor_id = AsyncMock()
    repo.get_by_visitor_id = AsyncMock()
    repo.get_by_user_id = AsyncMock()
    repo.get_by_email = AsyncMock()
    repo.create = AsyncMock()
    repo.link_to_user = AsyncMock()
    repo.set_consent = AsyncMock()
    repo.update_last_activity = AsyncMock()
    return repo


@pytest.fixture
def service(mock_session, mock_lead_repo):
    with (
        patch("services.lead_tracking.LeadRepository", return_value=mock_lead_repo),
        patch("services.lead_tracking.LeadInteractionRepository", return_value=MagicMock()),
    ):
        instance = LeadTrackingService(mock_session)
    instance.lead_repo = mock_lead_repo
    return instance


class TestTheRepository:
    """The row that the other request wrote is read back."""

    async def test_the_loser_of_the_race_returns_the_winner_row(self, mock_session):
        repo = LeadRepository(mock_session)
        winner = Lead(id="lead-winner", visitor_id="visitor-race")
        repo.get_by_visitor_id = AsyncMock(side_effect=[None, winner])
        repo.create = AsyncMock(side_effect=_collision())

        lead = await repo.get_or_create_by_visitor_id("visitor-race")

        assert lead is winner
        mock_session.rollback.assert_awaited_once()

    async def test_a_collision_without_a_row_still_raises(self, mock_session):
        """Nothing to fall back to: the error is the honest answer."""
        repo = LeadRepository(mock_session)
        repo.get_by_visitor_id = AsyncMock(return_value=None)
        repo.create = AsyncMock(side_effect=_collision())

        with pytest.raises(IntegrityError):
            await repo.get_or_create_by_visitor_id("visitor-race")


class TestTheService:
    """A capture that collides with a tracking call is still a capture."""

    async def test_a_capture_that_brings_the_address_is_still_announced(
        self, service, mock_lead_repo
    ):
        """The other request created the row without an address; this one has it."""
        winner = Lead(id="lead-winner", visitor_id="visitor-race", email=None)
        mock_lead_repo.get_by_visitor_id = AsyncMock(side_effect=[None, winner])
        mock_lead_repo.get_by_user_id = AsyncMock(return_value=None)
        mock_lead_repo.get_by_email = AsyncMock(return_value=None)
        mock_lead_repo.create = AsyncMock(side_effect=_collision())

        lead, is_new = await service.get_or_create_visitor(
            visitor_id="visitor-race",
            email="capture@example.com",
            source="propvector_waitlist",
            consent_given=True,
        )

        assert lead is winner
        # The address arrived with this request, so nobody has been told about
        # it yet - the operator still hears about this capture.
        assert is_new is True
        assert lead.email == "capture@example.com"

    async def test_a_capture_that_the_winner_already_had_is_not_announced_twice(
        self, service, mock_lead_repo
    ):
        winner = Lead(id="lead-winner", visitor_id="visitor-race", email="known@example.com")
        mock_lead_repo.get_by_visitor_id = AsyncMock(side_effect=[None, winner])
        mock_lead_repo.get_by_user_id = AsyncMock(return_value=None)
        mock_lead_repo.get_by_email = AsyncMock(return_value=None)
        mock_lead_repo.create = AsyncMock(side_effect=_collision())

        lead, is_new = await service.get_or_create_visitor(
            visitor_id="visitor-race",
            email="known@example.com",
            source="propvector_waitlist",
            consent_given=True,
        )

        assert lead is winner
        assert is_new is False


class TestTheEndpoint:
    """The visitor sees a normal answer, not a server error."""

    async def test_the_tracking_endpoint_does_not_answer_500(self, db_session):
        winner = Lead(id="lead-winner", visitor_id="visitor-race")
        db_session.add(winner)
        await db_session.commit()

        with (
            patch(
                "db.lead_repos.LeadRepository.get_by_visitor_id",
                new=AsyncMock(side_effect=[None, winner]),
            ),
            patch("db.lead_repos.LeadRepository.create", new=AsyncMock(side_effect=_collision())),
        ):
            app = FastAPI()
            app.include_router(leads.router, prefix="/api/v1")
            app.dependency_overrides[get_db] = lambda: db_session

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/leads/track",
                    json={"visitor_id": "visitor-race", "interaction_type": "view"},
                )

        assert response.status_code == 204, response.text
