"""The visitor-tracking event carries a locale (Task #99).

The locale is parsed from the route in the browser, carried through the
request schema, the router and the service into the stored interaction, and
the aggregation answers "visitors per locale" from those rows.
"""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.deps.auth import get_current_user_optional
from api.routers import analytics_outbound, leads
from db.database import get_db as get_db_dep
from db.schemas import OutboundClickRequest, TrackInteractionRequest
from services.lead_tracking import LeadTrackingService, normalize_locale
from services.user_activity_service import UserActivityService

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


class TestLocaleSchema:
    """The locale is optional: a request without one is a request."""

    def test_the_locale_is_optional(self):
        request = TrackInteractionRequest(visitor_id="v-1", interaction_type="view")
        assert request.locale is None

    def test_the_locale_is_carried_when_given(self):
        request = TrackInteractionRequest(visitor_id="v-1", interaction_type="view", locale="pl")
        assert request.locale == "pl"

    def test_the_outbound_click_carries_a_locale_too(self):
        request = OutboundClickRequest(target="https://studio.example", slot="hero", locale="en")
        assert request.locale == "en"


class TestNormalizeLocale:
    """A malformed locale is dropped - it never costs an interaction."""

    def test_a_locale_is_kept_as_it_is_but_lower_case(self):
        assert normalize_locale("PL") == "pl"
        assert normalize_locale(" pl ") == "pl"

    def test_a_locale_with_a_region_is_kept(self):
        assert normalize_locale("pt-BR") == "pt-br"

    def test_nothing_is_no_locale(self):
        assert normalize_locale(None) is None
        assert normalize_locale("") is None

    def test_a_malformed_locale_is_dropped(self):
        assert normalize_locale("not a locale") is None
        assert normalize_locale("../etc/passwd") is None


class TestTrackingEndpoint:
    """The locale travels from the request into the stored interaction."""

    @pytest.mark.asyncio
    async def test_a_polish_route_records_pl(self, client, db_session):
        response = await client.post(
            "/leads/track",
            json={
                "visitor_id": "visitor-pl",
                "interaction_type": "view",
                "property_id": "prop-1",
                "locale": "pl",
            },
        )
        assert response.status_code == 204

        rows = await _stored_interactions(db_session)
        assert rows[0].interaction_metadata["locale"] == "pl"

    @pytest.mark.asyncio
    async def test_an_english_route_records_en(self, client, db_session):
        response = await client.post(
            "/leads/track",
            json={
                "visitor_id": "visitor-en",
                "interaction_type": "view",
                "property_id": "prop-1",
                "locale": "en",
            },
        )
        assert response.status_code == 204

        rows = await _stored_interactions(db_session)
        assert rows[0].interaction_metadata["locale"] == "en"

    @pytest.mark.asyncio
    async def test_a_request_without_a_locale_is_accepted(self, client, db_session):
        response = await client.post(
            "/leads/track",
            json={
                "visitor_id": "visitor-none",
                "interaction_type": "view",
                "property_id": "prop-1",
            },
        )
        assert response.status_code == 204

        rows = await _stored_interactions(db_session)
        assert "locale" not in (rows[0].interaction_metadata or {})

    @pytest.mark.asyncio
    async def test_the_outbound_click_carries_the_locale(self, client, db_session):
        response = await client.post(
            "/analytics/outbound",
            json={
                "target": "https://studio.example",
                "slot": "hero",
                "campaign": "spring",
                "visitor_id": "visitor-out",
                "locale": "de",
            },
        )
        assert response.status_code == 204

        rows = await _stored_interactions(db_session)
        assert rows[0].interaction_metadata["locale"] == "de"
        assert rows[0].interaction_metadata["slot"] == "hero"


class TestServiceRoundTrip:
    """The value survives the round trip through the service."""

    @pytest.mark.asyncio
    async def test_the_service_stores_the_locale_in_the_metadata(self, db_session):
        service = LeadTrackingService(db_session)

        await service.track_interaction(
            visitor_id="visitor-service",
            interaction_type="view",
            property_id="prop-1",
            metadata={"source": "map"},
            locale="pl",
        )
        await db_session.flush()

        rows = await _stored_interactions(db_session)
        assert rows[0].interaction_metadata == {"source": "map", "locale": "pl"}

    @pytest.mark.asyncio
    async def test_the_service_keeps_the_metadata_of_a_request_without_a_locale(self, db_session):
        service = LeadTrackingService(db_session)

        await service.track_interaction(
            visitor_id="visitor-no-locale",
            interaction_type="view",
            metadata={"source": "map"},
        )
        await db_session.flush()

        rows = await _stored_interactions(db_session)
        assert rows[0].interaction_metadata == {"source": "map"}

    @pytest.mark.asyncio
    async def test_the_service_drops_a_malformed_locale(self, db_session):
        service = LeadTrackingService(db_session)

        await service.track_interaction(
            visitor_id="visitor-bad-locale",
            interaction_type="view",
            locale="not a locale",
        )
        await db_session.flush()

        rows = await _stored_interactions(db_session)
        assert "locale" not in (rows[0].interaction_metadata or {})


class TestVisitorsPerLocale:
    """The aggregation answers "visitors per locale" from the real rows."""

    @pytest.mark.asyncio
    async def test_the_visitors_are_counted_per_locale(self, db_session):
        service = LeadTrackingService(db_session)

        # Two visitors on the Polish pages, one on the English ones, and one
        # whose request carried no locale at all.
        await service.track_interaction(
            visitor_id="visitor-a", interaction_type="view", locale="pl"
        )
        await service.track_interaction(
            visitor_id="visitor-a", interaction_type="search", locale="pl"
        )
        await service.track_interaction(
            visitor_id="visitor-b", interaction_type="view", locale="pl"
        )
        await service.track_interaction(
            visitor_id="visitor-c", interaction_type="view", locale="en"
        )
        await service.track_interaction(visitor_id="visitor-d", interaction_type="view")
        await db_session.flush()

        activity = UserActivityService(db_session)
        summary = await activity.get_activity_summary()

        by_locale = {row["locale"]: row["visitors"] for row in summary.visitors_by_locale}
        assert by_locale["pl"] == 2
        assert by_locale["en"] == 1
        # A request without a locale is not counted under one.
        assert "unknown" not in by_locale
        assert sum(by_locale.values()) == 3

    @pytest.mark.asyncio
    async def test_a_deployment_without_visitors_answers_with_an_empty_list(self, db_session):
        activity = UserActivityService(db_session)

        summary = await activity.get_activity_summary()

        assert summary.visitors_by_locale == []


async def _stored_interactions(db_session):
    """The interaction rows the endpoint wrote."""
    from sqlalchemy import select

    from db.models import LeadInteraction

    result = await db_session.execute(select(LeadInteraction))
    return list(result.scalars().all())
