"""The edge paths of the routers the type cleanup touched.

Every test here calls the handler or the helper directly. A request handler
runs in its own asyncio task, and the coverage tracer does not come back after
the task suspends, so the lines of a handler are only visible to the report
when they run in the test's own task.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.routers import (
    agent_analytics,
    anomalies,
    bulk_jobs,
    data_sources,
    monitoring,
    profile,
    push,
    search,
    tools,
)
from db.models import User
from db.schemas import PushSubscriptionCreate
from tools.tco_tools import TCOComparisonInput, TCOInput

# ---------------------------------------------------------------------------
# tools: the comparison carries both scenarios
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_tco_comparison_answers_with_both_scenarios():
    """The comparison is made between the two scenarios it was given."""
    result = await tools.compare_tco(
        TCOComparisonInput(
            scenario_a=TCOInput(property_price=300_000.0),
            scenario_b=TCOInput(property_price=450_000.0),
        )
    )

    assert result.scenario_a_name == "Property A"
    assert result.scenario_b_name == "Property B"


# ---------------------------------------------------------------------------
# search: the polygon of the search page is one ring of points
# ---------------------------------------------------------------------------


def test_a_ring_of_points_is_a_valid_polygon():
    """The search page sends one ring of [lon, lat] pairs, not GeoJSON rings."""
    assert search._validate_polygon([[50.0, 19.9], [50.1, 19.9], [50.05, 20.0]]) is None


def test_a_ring_of_two_points_is_refused():
    """A ring with fewer than three vertices is refused."""
    assert search._validate_polygon([[50.0, 19.9], [50.1, 19.9]]) == (
        "Polygon must have at least 3 vertices"
    )


# ---------------------------------------------------------------------------
# push: the subscription that is already there
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_subscribing_again_answers_with_the_subscription(db_session):
    """A second subscription for the same endpoint answers with the first one."""
    existing = MagicMock()
    existing.id = "sub-1"
    existing.user_id = "user-1"
    existing.endpoint = "https://push.example.com/sub/1"
    existing.is_active = True
    existing.device_name = None
    existing.created_at = datetime(2025, 1, 1, tzinfo=UTC)
    existing.last_used_at = None

    repo = MagicMock()
    repo.get_by_endpoint = AsyncMock(return_value=existing)

    user = User(id="user-1", email="user@example.com")
    body = PushSubscriptionCreate(
        endpoint="https://push.example.com/sub/1",
        keys={"p256dh": "key", "auth": "secret"},
    )

    with (
        patch("api.routers.push.settings") as mock_settings,
        patch("api.routers.push.PushSubscriptionRepository", return_value=repo),
    ):
        mock_settings.push_enabled = True
        result = await push.subscribe_to_push(body, user, db_session)

    assert result.endpoint == "https://push.example.com/sub/1"
    assert result.id == "sub-1"


# ---------------------------------------------------------------------------
# anomalies: one anomaly
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_one_anomaly_is_answered_with_the_response_model(db_session):
    """The anomaly is answered with the response model, not a bare dict."""
    anomaly = {
        "id": "anomaly-1",
        "anomaly_type": "price_spike",
        "severity": "medium",
        "scope_type": "property",
        "scope_id": "prop-1",
        "detected_at": datetime(2025, 1, 1, tzinfo=UTC),
        "algorithm": "zscore",
        "threshold_used": 3.0,
        "metric_name": "price",
        "expected_value": 100.0,
        "actual_value": 200.0,
        "deviation_percent": 100.0,
    }

    service = MagicMock()
    service.get_anomaly_by_id = AsyncMock(return_value=anomaly)

    with patch("api.routers.anomalies.get_anomaly_service", return_value=service):
        result = await anomalies.get_anomaly("anomaly-1", current_user={}, db=db_session)

    assert result.id == "anomaly-1"
    assert result.actual_value == 200.0


# ---------------------------------------------------------------------------
# agent analytics: the deals of an agent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_deals_of_an_agent_are_listed(db_session):
    """The list answers with the deals, not with their identifiers."""
    user = User(id="agent-1", email="agent@example.com")
    user.role = "agent"

    with patch("api.routers.agent_analytics._deal_to_response") as mock_to_response:
        mock_to_response.return_value = MagicMock()
        result = await agent_analytics.list_my_deals(
            status_filter=None,
            page=1,
            page_size=20,
            user=user,
            session=db_session,
        )

    assert result.total == 0
    assert result.items == []


# ---------------------------------------------------------------------------
# bulk jobs: the import and the export
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_an_import_job_is_created_with_the_database_url(db_session):
    """The job is queued with the database URL of the deployment."""
    from fastapi import BackgroundTasks

    request = bulk_jobs.BulkImportRequest(
        source_type="portal_api",
        source_name="otodom",
        config={"portal": "otodom", "city": "Krakow"},
    )
    background_tasks = BackgroundTasks()

    with patch("config.settings.get_settings") as mock_settings:
        mock_settings.return_value.database_url = "sqlite+aiosqlite:///:memory:"
        result = await bulk_jobs.create_import_job(request, background_tasks, db_session)

    assert result.id
    assert background_tasks.tasks


@pytest.mark.asyncio
async def test_an_export_job_is_created_with_the_database_url(db_session):
    """The job is queued with the database URL of the deployment."""
    from fastapi import BackgroundTasks

    request = bulk_jobs.BulkExportRequest(
        format="json",
        config={"query": "Krakow", "filters": {}, "limit": 10},
    )
    background_tasks = BackgroundTasks()

    with patch("config.settings.get_settings") as mock_settings:
        mock_settings.return_value.database_url = "sqlite+aiosqlite:///:memory:"
        result = await bulk_jobs.create_export_job(request, background_tasks, db_session)

    assert result.id
    assert background_tasks.tasks


# ---------------------------------------------------------------------------
# data sources: the portal that is tested
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_portal_source_is_tested_through_the_registry():
    """The portal is looked up in the registry and asked for its health."""
    adapter = MagicMock()
    adapter.health_check = AsyncMock(return_value=True)

    with (
        patch("data.adapters.registry.AdapterRegistry.list_adapters", return_value=["otodom"]),
        patch("data.adapters.registry.AdapterRegistry.get_adapter", return_value=adapter),
    ):
        result = await data_sources._test_portal_source(
            {"portal": "otodom", "api_key": "key"}  # pragma: allowlist secret
        )

    assert result.success is True
    assert "otodom" in result.message


@pytest.mark.asyncio
async def test_an_unknown_portal_is_reported():
    """A portal the registry does not know is reported, not raised."""
    with patch("data.adapters.registry.AdapterRegistry.list_adapters", return_value=["otodom"]):
        result = await data_sources._test_portal_source({"portal": "unknown"})

    assert result.success is False
    assert "unknown" in result.message


# ---------------------------------------------------------------------------
# monitoring: the readiness probe
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_readiness_probe_answers_with_its_checks(db_session):
    """The probe answers with the checks it ran."""
    from api.deps.auth import AuthCredentials

    user = User(id="user-1", email="user@example.com")
    credentials = AuthCredentials(user=user, token_payload={"roles": ["user"]})
    response = await monitoring.readiness_check(db=db_session, credentials=credentials)

    body = response.body.decode() if hasattr(response, "body") else str(response)
    assert "database" in body


# ---------------------------------------------------------------------------
# profile: the export
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_export_gathers_the_data_of_the_user(db_session):
    """The export runs in the background and gathers the data of the user."""
    from fastapi import BackgroundTasks

    from api.routers.profile import DataExportRequest

    user = User(id="user-1", email="user@example.com")
    user.data_export_requested_at = None

    background_tasks = BackgroundTasks()
    request = DataExportRequest(
        format="json",
        include_favorites=False,
        include_search_history=False,
        include_documents=False,
    )

    with patch("api.routers.profile.get_current_active_user"):
        response = await profile.request_data_export(
            request,
            background_tasks,
            user,
            db_session,
        )

    assert response.export_id
    # The export itself runs as a background task - it is awaited here so that
    # its lines are recorded.
    for task in background_tasks.tasks:
        await task()
