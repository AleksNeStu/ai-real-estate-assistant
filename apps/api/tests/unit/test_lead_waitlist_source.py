"""The waitlist source of a lead.

The landing's waitlist posts to the same public lead endpoint the footer's
form uses, with its own source. The studio has to be able to tell a waitlist
signup from an ordinary contact, so the source has to survive the trip: the
schema has to accept it, the endpoint has to store it, and an address that
came in through the waitlist has to carry its consent.
"""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from api.routers import leads
from db.database import get_db
from db.models import Lead
from db.schemas import LeadCreate, LeadSourceType


class TestLeadSourceType:
    """The set of sources a lead may come from."""

    def test_the_waitlist_is_a_source(self):
        assert "propvector_waitlist" in LeadSourceType.__args__

    def test_the_waitlist_source_is_accepted_by_the_schema(self):
        """The schema has to accept it - a rejected source is a 422."""
        lead = LeadCreate(
            visitor_id="visitor-1",
            email="someone@example.com",
            source="propvector_waitlist",
            consent_given=True,
        )
        assert lead.source == "propvector_waitlist"
        assert lead.consent_given is True

    def test_an_unknown_source_is_still_rejected(self):
        """Adding one source must not open the type to anything."""
        with pytest.raises(ValueError):
            LeadCreate(visitor_id="visitor-1", source="not-a-source")


class TestWaitlistLead:
    """The waitlist signup as the endpoint stores it."""

    async def _client(self, session) -> AsyncClient:
        app = FastAPI()
        app.include_router(leads.router, prefix="/api/v1")
        app.dependency_overrides[get_db] = lambda: session
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    async def test_the_waitlist_source_is_stored_on_the_lead(self, db_session):
        async with await self._client(db_session) as client:
            response = await client.post(
                "/api/v1/leads/visitor",
                json={
                    "visitor_id": "visitor-waitlist-1",
                    "email": "waitlist@example.com",
                    "source": "propvector_waitlist",
                    "consent_given": True,
                },
            )

        assert response.status_code == 201, response.text
        assert response.json()["source"] == "propvector_waitlist"

        stored = (
            await db_session.execute(select(Lead).where(Lead.visitor_id == "visitor-waitlist-1"))
        ).scalar_one()
        assert stored.source == "propvector_waitlist"

    async def test_the_consent_is_stored_with_the_lead(self, db_session):
        """The waitlist form sends the consent; it has to land with the lead."""
        async with await self._client(db_session) as client:
            response = await client.post(
                "/api/v1/leads/visitor",
                json={
                    "visitor_id": "visitor-waitlist-2",
                    "email": "waitlist2@example.com",
                    "source": "propvector_waitlist",
                    "consent_given": True,
                },
            )

        assert response.status_code == 201, response.text

        stored = (
            await db_session.execute(select(Lead).where(Lead.visitor_id == "visitor-waitlist-2"))
        ).scalar_one()
        assert stored.consent_given is True

    async def test_an_ordinary_contact_keeps_its_own_source(self, db_session):
        """The waitlist source does not swallow the other sources."""
        async with await self._client(db_session) as client:
            response = await client.post(
                "/api/v1/leads/visitor",
                json={
                    "visitor_id": "visitor-organic-1",
                    "email": "organic@example.com",
                    "source": "organic",
                },
            )

        assert response.status_code == 201, response.text
        assert response.json()["source"] == "organic"
