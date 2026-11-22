"""The attribution rows carry a visitor id (Task #109).

An arrival that arrives without an id is rejected by the API, and an
outbound click that arrives without one is filed under the literal
"anonymous" - so neither row can be tied to the lead the visitor already
has. The browser therefore sends the id it keeps in a cookie, and both rows
land under the same lead.
"""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from api.deps.auth import get_current_user_optional
from api.routers import analytics_outbound, leads
from db.database import get_db as get_db_dep
from db.models import Lead, LeadInteraction

_test_app = FastAPI()
_test_app.include_router(leads.router)
_test_app.include_router(analytics_outbound.router)


@pytest.fixture(autouse=True)
def auth_none():
    async def _none():
        return None

    _test_app.dependency_overrides[get_current_user_optional] = _none
    yield
    _test_app.dependency_overrides.clear()


@pytest.fixture
async def client(db_session):
    async def _get_db():
        yield db_session

    _test_app.dependency_overrides[get_db_dep] = _get_db
    transport = ASGITransport(app=_test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    _test_app.dependency_overrides.pop(get_db_dep, None)


class TestTheArrivalCarriesTheVisitor:
    """The arrival is accepted, and the id it carries is stored."""

    @pytest.mark.asyncio
    async def test_an_arrival_with_an_id_is_accepted(self, client, db_session):
        response = await client.post(
            "/leads/track",
            json={
                "visitor_id": "visitor-arrival",
                "interaction_type": "navigation",
                "metadata": {"slot": "hero"},
                "locale": "pl",
            },
        )
        assert response.status_code == 204

        leads = await _stored_leads(db_session)
        assert [lead.visitor_id for lead in leads] == ["visitor-arrival"]

        rows = await _stored_interactions(db_session)
        assert len(rows) == 1
        assert rows[0].interaction_type == "navigation"
        assert rows[0].interaction_metadata["slot"] == "hero"

    @pytest.mark.asyncio
    async def test_an_arrival_without_an_id_is_rejected(self, client, db_session):
        response = await client.post(
            "/leads/track",
            json={
                "interaction_type": "navigation",
                "metadata": {"slot": "hero"},
            },
        )
        assert response.status_code == 422

        rows = await _stored_interactions(db_session)
        assert rows == []

    @pytest.mark.asyncio
    async def test_the_arrival_row_hangs_under_the_lead_of_the_visitor(self, client, db_session):
        await client.post(
            "/leads/track",
            json={
                "visitor_id": "visitor-arrival",
                "interaction_type": "navigation",
                "metadata": {"slot": "hero"},
            },
        )
        await db_session.flush()

        leads = await _stored_leads(db_session)
        rows = await _stored_interactions(db_session)
        assert rows[0].lead_id == leads[0].id


class TestTheOutboundClickCarriesTheVisitor:
    """The outbound click is filed under the same lead as the arrival."""

    @pytest.mark.asyncio
    async def test_the_click_lands_under_the_lead_of_the_visitor(self, client, db_session):
        await client.post(
            "/leads/track",
            json={
                "visitor_id": "visitor-shared",
                "interaction_type": "navigation",
                "metadata": {"slot": "hero"},
            },
        )
        response = await client.post(
            "/analytics/outbound",
            json={
                "visitor_id": "visitor-shared",
                "target": "https://studio.example",
                "slot": "hero",
                "campaign": "spring",
            },
        )
        assert response.status_code == 204
        await db_session.flush()

        leads = await _stored_leads(db_session)
        assert len(leads) == 1
        assert leads[0].visitor_id == "visitor-shared"

        rows = await _stored_interactions(db_session)
        assert len(rows) == 2
        assert {row.lead_id for row in rows} == {leads[0].id}

    @pytest.mark.asyncio
    async def test_a_click_without_an_id_is_filed_under_anonymous(self, client, db_session):
        response = await client.post(
            "/analytics/outbound",
            json={
                "target": "https://studio.example",
                "slot": "hero",
            },
        )
        assert response.status_code == 204
        await db_session.flush()

        leads = await _stored_leads(db_session)
        assert [lead.visitor_id for lead in leads] == ["anonymous"]


async def _stored_leads(db_session):
    """The lead rows the endpoints wrote."""
    result = await db_session.execute(select(Lead))
    return list(result.scalars().all())


async def _stored_interactions(db_session):
    """The interaction rows the endpoints wrote."""
    result = await db_session.execute(select(LeadInteraction))
    return list(result.scalars().all())
