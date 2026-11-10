"""The agent list response carries the number of listings an agent has.

The directory shows that number in its Listings column and sorts the catalogue
by it, so the number the API carries has to be the number the catalogue holds:
a count a test can check against the catalogue itself, not a guess.
"""

import uuid

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from api.routers import agents
from db.database import get_db
from db.models import AgentListing, AgentProfile, User


@pytest.fixture
async def client(db_session):
    """A client on the real agents router, over the real test database."""
    app = FastAPI()
    app.include_router(agents.router, prefix="/api/v1")

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client


async def _seed_agent(db_session, *, listings: int, deactivated: int = 0) -> str:
    """Put an agent with a given number of listings into the catalogue."""
    user = User(
        id=str(uuid.uuid4()),
        email=f"agent-{uuid.uuid4().hex}@example.com",
        full_name="Test Agent",
    )
    db_session.add(user)
    await db_session.flush()

    profile = AgentProfile(
        id=str(uuid.uuid4()),
        user_id=user.id,
        agency_name="Test Agency",
        average_rating=4.5,
        total_reviews=10,
        is_active=True,
    )
    db_session.add(profile)
    await db_session.flush()

    for index in range(listings):
        db_session.add(
            AgentListing(
                id=str(uuid.uuid4()),
                agent_id=profile.id,
                property_id=f"property-{index}",
                listing_type="sale",
                is_active=True,
            )
        )
    for index in range(deactivated):
        db_session.add(
            AgentListing(
                id=str(uuid.uuid4()),
                agent_id=profile.id,
                property_id=f"withdrawn-{index}",
                listing_type="sale",
                is_active=False,
            )
        )
    await db_session.flush()

    return profile.id


async def _catalogue_count(db_session, agent_id: str) -> int:
    """The number of that agent's active listings, counted by the catalogue."""
    count = await db_session.scalar(
        select(func.count(AgentListing.id)).where(
            AgentListing.agent_id == agent_id,
            AgentListing.is_active == True,  # noqa: E712
        )
    )
    return count or 0


def _counts(response) -> dict[str, int]:
    """The listing count every item of the response carries, by agent."""
    return {item["id"]: item["listings_count"] for item in response.json()["items"]}


class TestAgentListingCount:
    @pytest.mark.asyncio
    async def test_the_response_carries_the_count_of_the_catalogue(self, db_session, client):
        """The count on the response is the number of the agent's listings."""
        agent_id = await _seed_agent(db_session, listings=3)
        await _seed_agent(db_session, listings=0)

        response = await client.get("/api/v1/agents")

        assert response.status_code == 200
        counts = _counts(response)
        assert counts[agent_id] == 3
        assert counts[agent_id] == await _catalogue_count(db_session, agent_id)

    @pytest.mark.asyncio
    async def test_an_agent_without_listings_carries_zero(self, db_session, client):
        """No listings is a zero, not a blank and not a missing field."""
        agent_id = await _seed_agent(db_session, listings=0)

        response = await client.get("/api/v1/agents")

        counts = _counts(response)
        assert counts[agent_id] == 0

    @pytest.mark.asyncio
    async def test_a_withdrawn_listing_is_not_counted(self, db_session, client):
        """The count is the count of the active listings."""
        agent_id = await _seed_agent(db_session, listings=2, deactivated=3)

        response = await client.get("/api/v1/agents")

        counts = _counts(response)
        assert counts[agent_id] == 2
        assert counts[agent_id] == await _catalogue_count(db_session, agent_id)

    @pytest.mark.asyncio
    async def test_sorting_by_listings_keeps_the_order_of_the_count(self, db_session, client):
        """Sorting by listings orders the rows by the count they show."""
        busiest = await _seed_agent(db_session, listings=5)
        quiet = await _seed_agent(db_session, listings=1)
        empty = await _seed_agent(db_session, listings=0)

        response = await client.get("/api/v1/agents", params={"sort_by": "listings"})

        assert response.status_code == 200
        items = response.json()["items"]
        assert [item["id"] for item in items] == [busiest, quiet, empty]
        assert [item["listings_count"] for item in items] == [5, 1, 0]
