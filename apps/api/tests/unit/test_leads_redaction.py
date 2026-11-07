"""Tests for the lead contact-detail redaction in the leads router.

In demo mode `api.deps.auth.get_current_user` resolves EVERY caller to the
synthetic admin account (id="demo-user-id"), so an anonymous visitor would
otherwise be able to list every lead and read every lead's real email address.
The router must redact the contact fields for that actor.

A genuinely authenticated admin must still see the unmasked contact details —
that view has to stay usable.

Task #30 — make the demo capture leads.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.deps.auth import get_current_active_user
from api.routers import leads
from db.database import get_db as get_db_dep
from db.schemas import LeadWithScoreResponse

# The sentinels of the synthetic demo identity (api/deps/auth.py::_get_demo_user).
DEMO_USER_ID = "demo-user-id"
DEMO_USER_EMAIL = "demo@example.com"

LEAD_EMAIL = "lead@test.com"
LEAD_PHONE = "+48123456789"
LEAD_NAME = "Test Lead"
MASKED_EMAIL = "l***@test.com"
MASKED_PHONE = "***89"
MASKED_NAME = "T***"

_app = FastAPI()
_app.include_router(leads.router)


def _make_user(role="admin", user_id="admin-1", email="admin@test.com"):
    user = MagicMock()
    user.id = user_id
    user.role = role
    user.email = email
    user.is_active = True
    return user


def _make_lead(email=LEAD_EMAIL, phone=LEAD_PHONE, status="new", name=LEAD_NAME):
    lead = MagicMock()
    lead.id = "lead-1"
    lead.visitor_id = "vis-1"
    lead.user_id = None
    lead.email = email
    lead.phone = phone
    lead.name = name
    lead.budget_min = 100000
    lead.budget_max = 500000
    lead.preferred_locations = ["Krakow"]
    lead.status = status
    lead.source = "organic"
    lead.current_score = 50
    lead.first_seen_at = datetime.now(UTC)
    lead.last_activity_at = datetime.now(UTC)
    lead.created_at = datetime.now(UTC)
    lead.updated_at = datetime.now(UTC)
    lead.consent_given = True
    lead.consent_at = datetime.now(UTC)
    # MagicMock invents any attribute on access, so these have to be set
    # explicitly: LeadResponse validates them as Optional[str].
    lead.assigned_agent_id = None
    lead.assigned_agent_name = None
    return lead


def _score_result():
    result = MagicMock()
    result.score = 55
    result.budget_fit = 50
    result.urgency = 60
    result.engagement = 55
    result.priority_tier = "warm"
    result.factors = {}
    result.recommendations = []
    return result


@contextmanager
def _patched_repos(lead=None, leads_list=None, count=1) -> Iterator[None]:
    """Patch every repository the leads router reads from."""
    with (
        patch("api.routers.leads.LeadRepository") as repo_cls,
        patch("api.routers.leads.LeadScoreRepository") as score_cls,
        patch("api.routers.leads.LeadInteractionRepository") as interaction_cls,
        patch("api.routers.leads.AgentAssignmentRepository") as assignment_cls,
    ):
        repo = MagicMock()
        repo.get_list = AsyncMock(return_value=leads_list if leads_list is not None else [lead])
        repo.count = AsyncMock(return_value=count)
        repo.get_by_id = AsyncMock(return_value=lead)
        repo.update = AsyncMock(return_value=lead)
        repo_cls.return_value = repo

        score = MagicMock()
        score.get_latest_for_lead = AsyncMock(return_value=None)
        score.get_history_for_lead = AsyncMock(return_value=[])
        score_cls.return_value = score

        interaction = MagicMock()
        interaction.get_by_lead = AsyncMock(return_value=[])
        interaction_cls.return_value = interaction

        assignment = MagicMock()
        assignment.get_primary_for_lead = AsyncMock(return_value=None)
        assignment_cls.return_value = assignment

        yield


@contextmanager
def _patched_tracking(lead, is_new=True) -> Iterator[None]:
    """Patch the lead tracking service used by the public visitor endpoints."""
    with patch("api.routers.leads.LeadTrackingService") as tracking_cls:
        tracking = MagicMock()
        tracking.get_or_create_visitor = AsyncMock(return_value=(lead, is_new))
        tracking_cls.return_value = tracking
        yield


@contextmanager
def _patched_scoring(lead) -> Iterator[None]:
    """Patch the tracking + scoring services used by `POST /leads`."""
    with (
        patch("api.routers.leads.LeadTrackingService") as tracking_cls,
        patch("api.routers.leads.PrioritizedLeadScoringService") as scoring_cls,
        patch("api.routers.leads.LeadScoringService") as std_cls,
    ):
        tracking = MagicMock()
        tracking.get_or_create_visitor = AsyncMock(return_value=(lead, True))
        tracking_cls.return_value = tracking

        scoring = MagicMock()
        scoring.score_lead = MagicMock(return_value=_score_result())
        scoring_cls.return_value = scoring

        std = MagicMock()
        std.score_lead = AsyncMock(return_value=None)
        std_cls.return_value = std

        yield


@pytest.fixture
def mock_db():
    mock_session = AsyncMock()

    async def _get_db():
        yield mock_session

    _app.dependency_overrides[get_db_dep] = _get_db
    yield mock_session
    _app.dependency_overrides.pop(get_db_dep, None)


@pytest.fixture
def auth_demo():
    """The synthetic demo identity an anonymous visitor resolves to."""

    async def _demo():
        return _make_user(role="admin", user_id=DEMO_USER_ID, email=DEMO_USER_EMAIL)

    _app.dependency_overrides[get_current_active_user] = _demo
    yield
    _app.dependency_overrides.pop(get_current_active_user, None)


@pytest.fixture
def auth_real_admin():
    """A genuinely authenticated admin — not the demo identity."""

    async def _admin():
        return _make_user(role="admin", user_id="admin-1", email="admin@test.com")

    _app.dependency_overrides[get_current_active_user] = _admin
    yield
    _app.dependency_overrides.pop(get_current_active_user, None)


class TestIsDemoActor:
    def test_the_demo_identity_is_a_demo_actor(self):
        user = _make_user(user_id=DEMO_USER_ID, email=DEMO_USER_EMAIL)
        assert leads._is_demo_actor(user) is True

    def test_a_real_admin_is_not_a_demo_actor(self):
        user = _make_user(user_id="admin-1", email="admin@test.com")
        assert leads._is_demo_actor(user) is False

    def test_a_missing_user_is_a_demo_actor(self):
        assert leads._is_demo_actor(None) is True


class TestMaskEmail:
    def test_an_address_without_at_sign_is_fully_masked(self):
        assert leads._mask_email("not-an-email") == "***"

    def test_an_address_without_at_sign_does_not_leak_the_value(self):
        masked = leads._mask_email("not-an-email")
        assert masked != "not-an-email"
        assert "not" not in masked

    def test_a_single_character_local_part_is_fully_masked(self):
        assert leads._mask_email("a@example.com") == "*@example.com"

    def test_a_single_character_local_part_reveals_only_that_one_character(self):
        masked = leads._mask_email("a@example.com")
        assert masked.split("@")[0] == "*"
        assert len(masked.split("@")[0]) == 1

    def test_a_longer_local_part_keeps_only_the_first_character(self):
        assert leads._mask_email(LEAD_EMAIL) == MASKED_EMAIL

    def test_a_missing_address_stays_none(self):
        assert leads._mask_email(None) is None


class TestMaskName:
    """A visitor's name is personal detail exactly as much as their address."""

    def test_a_name_is_reduced_to_its_initial(self):
        assert leads._mask_name(LEAD_NAME) == MASKED_NAME

    def test_a_masked_name_does_not_leak_the_surname(self):
        masked = leads._mask_name("Katarzyna Nowak")
        assert masked == "K***"
        assert "Nowak" not in masked
        assert "Katarzyna" not in masked

    def test_a_missing_name_stays_none(self):
        assert leads._mask_name(None) is None

    def test_a_blank_name_stays_none(self):
        assert leads._mask_name("   ") is None


class TestListLeadsRedaction:
    @pytest.mark.asyncio
    async def test_list_leads_masks_the_email_for_the_demo_actor(self, auth_demo, mock_db):
        with _patched_repos(lead=_make_lead()):
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/leads")

        assert resp.status_code == 200
        items = resp.json()["items"]
        assert items
        for item in items:
            assert item["email"] == MASKED_EMAIL
            assert item["email"] != LEAD_EMAIL

    @pytest.mark.asyncio
    async def test_list_leads_masks_the_phone_for_the_demo_actor(self, auth_demo, mock_db):
        with _patched_repos(lead=_make_lead()):
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/leads")

        assert resp.status_code == 200
        items = resp.json()["items"]
        assert items
        for item in items:
            assert item["phone"] == MASKED_PHONE
            assert item["phone"] != LEAD_PHONE

    @pytest.mark.asyncio
    async def test_list_leads_masks_the_name_for_the_demo_actor(self, auth_demo, mock_db):
        with _patched_repos(lead=_make_lead()):
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/leads")

        assert resp.status_code == 200
        items = resp.json()["items"]
        assert items
        for item in items:
            assert item["name"] == MASKED_NAME
            assert LEAD_NAME not in resp.text

    @pytest.mark.asyncio
    async def test_list_leads_never_returns_the_real_address_to_the_demo_actor(
        self, auth_demo, mock_db
    ):
        with _patched_repos(lead=_make_lead()):
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/leads")

        assert resp.status_code == 200
        assert LEAD_EMAIL not in resp.text

    @pytest.mark.asyncio
    async def test_list_leads_keeps_the_email_for_a_real_admin(self, auth_real_admin, mock_db):
        with _patched_repos(lead=_make_lead()):
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/leads")

        assert resp.status_code == 200
        items = resp.json()["items"]
        assert items
        for item in items:
            assert item["email"] == LEAD_EMAIL
            assert item["phone"] == LEAD_PHONE
            assert item["name"] == LEAD_NAME


class TestGetLeadRedaction:
    @pytest.mark.asyncio
    async def test_get_lead_masks_the_contact_details_for_the_demo_actor(self, auth_demo, mock_db):
        with _patched_repos(lead=_make_lead()):
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/leads/lead-1")

        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == MASKED_EMAIL
        assert body["email"] != LEAD_EMAIL
        assert body["phone"] == MASKED_PHONE
        assert body["name"] == MASKED_NAME

    @pytest.mark.asyncio
    async def test_get_lead_keeps_the_contact_details_for_a_real_admin(
        self, auth_real_admin, mock_db
    ):
        with _patched_repos(lead=_make_lead()):
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/leads/lead-1")

        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == LEAD_EMAIL
        assert body["phone"] == LEAD_PHONE
        assert body["name"] == LEAD_NAME


class TestExportLeadsRedaction:
    @pytest.mark.asyncio
    async def test_export_leads_masks_the_email_column_for_the_demo_actor(self, auth_demo, mock_db):
        with _patched_repos(lead=_make_lead()):
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/leads/export")

        assert resp.status_code == 200
        assert MASKED_EMAIL in resp.text
        assert LEAD_EMAIL not in resp.text

    @pytest.mark.asyncio
    async def test_export_leads_masks_the_phone_column_for_the_demo_actor(self, auth_demo, mock_db):
        with _patched_repos(lead=_make_lead()):
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/leads/export")

        assert resp.status_code == 200
        assert MASKED_PHONE in resp.text
        assert LEAD_PHONE not in resp.text

    @pytest.mark.asyncio
    async def test_export_leads_masks_the_name_column_for_the_demo_actor(self, auth_demo, mock_db):
        with _patched_repos(lead=_make_lead()):
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/leads/export")

        assert resp.status_code == 200
        assert MASKED_NAME in resp.text
        assert LEAD_NAME not in resp.text

    @pytest.mark.asyncio
    async def test_export_leads_keeps_the_email_for_a_real_admin(self, auth_real_admin, mock_db):
        with _patched_repos(lead=_make_lead()):
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/leads/export")

        assert resp.status_code == 200
        assert LEAD_EMAIL in resp.text
        assert LEAD_NAME in resp.text


class TestUpdateLeadRedaction:
    @pytest.mark.asyncio
    async def test_update_lead_masks_the_contact_details_for_the_demo_actor(
        self, auth_demo, mock_db
    ):
        with _patched_repos(lead=_make_lead()):
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.patch("/leads/lead-1", json={"name": "New Name"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == MASKED_EMAIL
        assert body["email"] != LEAD_EMAIL
        assert body["phone"] == MASKED_PHONE
        assert body["name"] == MASKED_NAME

    @pytest.mark.asyncio
    async def test_update_lead_status_masks_the_contact_details_for_the_demo_actor(
        self, auth_demo, mock_db
    ):
        with patch("api.routers.leads.LeadTrackingService") as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.update_lead_status = AsyncMock(return_value=_make_lead(status="contacted"))
            mock_svc_cls.return_value = mock_svc

            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.patch("/leads/lead-1/status?status=contacted")

        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == MASKED_EMAIL
        assert body["email"] != LEAD_EMAIL
        assert body["phone"] == MASKED_PHONE


class TestPublicVisitorEndpoints:
    """The public self-service endpoints echo the caller's own address back."""

    @pytest.mark.asyncio
    async def test_create_visitor_echoes_the_submitted_email_unmasked(self, mock_db):
        with _patched_tracking(_make_lead(email="buyer@example.com")):
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.post(
                    "/leads/visitor",
                    json={"visitor_id": "vis-1", "email": "buyer@example.com"},
                )

        assert resp.status_code == 201
        body = resp.json()
        assert body["email"] == "buyer@example.com"

    @pytest.mark.asyncio
    async def test_create_visitor_never_returns_a_phone_number(self, mock_db):
        with _patched_tracking(_make_lead(email="buyer@example.com")):
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.post(
                    "/leads/visitor",
                    json={"visitor_id": "vis-1", "email": "buyer@example.com"},
                )

        assert resp.status_code == 201
        body = resp.json()
        assert body["phone"] != LEAD_PHONE
        assert body["phone"] == MASKED_PHONE

    @pytest.mark.asyncio
    async def test_create_visitor_masks_an_address_the_caller_did_not_submit(self, mock_db):
        """A lead found by visitor_id may carry somebody else's address."""
        with _patched_tracking(_make_lead(), is_new=False):
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.post("/leads/visitor", json={"visitor_id": "vis-1"})

        assert resp.status_code == 201
        body = resp.json()
        assert body["email"] == MASKED_EMAIL
        assert body["email"] != LEAD_EMAIL
        assert body["name"] == MASKED_NAME

    @pytest.mark.asyncio
    async def test_create_and_score_lead_echoes_the_submitted_email_unmasked(self, mock_db):
        with _patched_scoring(_make_lead(email="buyer@example.com")):
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.post(
                    "/leads",
                    json={
                        "visitor_id": "vis-1",
                        "email": "buyer@example.com",
                        "source": "organic",
                    },
                )

        assert resp.status_code == 201
        body = resp.json()
        assert body["email"] == "buyer@example.com"

    @pytest.mark.asyncio
    async def test_create_and_score_lead_never_returns_a_phone_number(self, mock_db):
        with _patched_scoring(_make_lead(email="buyer@example.com")):
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.post(
                    "/leads",
                    json={
                        "visitor_id": "vis-1",
                        "email": "buyer@example.com",
                        "source": "organic",
                    },
                )

        assert resp.status_code == 201
        body = resp.json()
        assert body["phone"] != LEAD_PHONE
        assert body["phone"] == MASKED_PHONE

    @pytest.mark.asyncio
    async def test_create_and_score_lead_echoes_the_submitted_name_unmasked(self, mock_db):
        """A name the caller just typed is their own input — echoing it leaks nothing."""
        with _patched_scoring(_make_lead(email="buyer@example.com", name="Buyer One")):
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.post(
                    "/leads",
                    json={
                        "visitor_id": "vis-1",
                        "email": "buyer@example.com",
                        "name": "Buyer One",
                        "source": "organic",
                    },
                )

        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Buyer One"

    @pytest.mark.asyncio
    async def test_create_and_score_lead_masks_a_name_the_caller_did_not_submit(self, mock_db):
        """A lead found by visitor_id may carry somebody else's name."""
        with _patched_scoring(_make_lead(email="buyer@example.com")):
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.post(
                    "/leads",
                    json={
                        "visitor_id": "vis-1",
                        "email": "buyer@example.com",
                        "source": "organic",
                    },
                )

        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == MASKED_NAME
        assert LEAD_NAME not in resp.text

    @pytest.mark.asyncio
    async def test_create_and_score_lead_returns_the_priority_score(self, mock_db):
        """The endpoint computes a priority score — the client must receive it.

        The response model used to drop the field (pydantic `extra='ignore'`),
        so the client never saw the score the endpoint's own summary promised.
        """
        with _patched_scoring(_make_lead(email="buyer@example.com")):
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.post(
                    "/leads",
                    json={
                        "visitor_id": "vis-1",
                        "email": "buyer@example.com",
                        "source": "organic",
                    },
                )

        assert resp.status_code == 201
        body = resp.json()
        assert body["priority_score"] is not None
        assert body["priority_score"]["score"] == 55
        assert body["priority_score"]["priority_tier"] == "warm"

    def test_the_response_model_declares_the_priority_score_field(self):
        """The field exists on the model, so it cannot be silently dropped."""
        assert "priority_score" in LeadWithScoreResponse.model_fields
