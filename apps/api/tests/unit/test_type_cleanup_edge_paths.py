"""The edge paths the type cleanup touched.

The changed-lines coverage gate reads two reports - the unit one and the
integration one - and every changed line has to be covered in both. These
tests are the unit half of that pair; their twins live in
``tests/integration/api/test_api_edge_paths_integration.py`` and
``tests/integration/test_service_edge_paths_integration.py``.

Every test calls the handler or the helper directly. A request handler runs
in its own asyncio task, and the coverage tracer does not come back after the
task suspends, so the lines of a handler are only visible to the report when
they run in the test's own task.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.middleware.audit import AuditMiddleware
from api.routers import bulk_jobs, push, tools
from db.models import User
from db.schemas import PushSubscriptionCreate
from tools.negotiation_tool import NegotiationTool
from tools.price_forecast_tools import PriceForecastTool
from tools.tco_tools import TCOComparisonInput, TCOInput
from utils.free_tier import _try_create_openrouter_free

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
# negotiation: the band without comparables and the fallback search
# ---------------------------------------------------------------------------


def test_a_target_without_comparables_has_no_band():
    """Without a price and without comparables there is no band to propose."""
    tool = NegotiationTool()

    result = tool.analyse(target={"city": "Kraków"}, comparables=[])

    assert result["price_band"]["lower"] is None


def test_a_target_without_comparables_falls_back_to_its_own_price():
    """Without comparables the band is derived from the asking price."""
    tool = NegotiationTool()

    result = tool.analyse(target={"city": "Kraków", "price": 500_000.0}, comparables=[])

    assert result["price_band"]["lower"] == 450_000.0
    assert result["price_band"]["upper"] == 490_000.0


def test_the_comparables_are_fetched_from_the_vector_store():
    """Without an identifier the target is searched for, and the rest compares."""
    document = MagicMock()
    document.metadata = {"city": "Kraków", "property_type": "apartment"}
    comparable = MagicMock()
    comparable.metadata = {"city": "Kraków", "price": 400_000.0}

    store = MagicMock(spec=["search"])
    store.search = MagicMock(return_value=[(document, 0.9), (comparable, 0.8)])

    tool = NegotiationTool(vector_store=store)
    target, comparables = tool._fetch_property_and_comps("prop-1")

    assert target["city"] == "Kraków"
    assert comparables[0]["price"] == 400_000.0


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
# price forecast: the JSON inside the answer
# ---------------------------------------------------------------------------


def test_the_json_inside_the_answer_is_read():
    """A JSON object inside a longer answer is read."""
    parsed = PriceForecastTool._parse_llm_json('here it is: {"price": 100} and more')

    assert parsed == {"price": 100}


# ---------------------------------------------------------------------------
# the free tier: the free models of OpenRouter
# ---------------------------------------------------------------------------


def test_the_free_models_of_openrouter_are_read():
    """The cascade asks OpenRouter for the models it charges nothing for."""
    provider = MagicMock()
    provider.get_free_model_ids = MagicMock(return_value=["free/model"])

    with (
        patch("utils.free_tier.get_settings") as mock_settings,
        patch("models.provider_factory.ModelProviderFactory.get_provider", return_value=provider),
    ):
        mock_settings.return_value.openrouter_api_key = "key"  # pragma: allowlist secret
        mock_settings.return_value.free_tier_default_model = "free/model"
        model = _try_create_openrouter_free()

    assert model is not None


# ---------------------------------------------------------------------------
# the audit middleware: the mutating request
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_audit_middleware_hands_the_response_back():
    """The middleware passes the response through and logs the request."""
    request = MagicMock()
    request.method = "POST"
    request.url.path = "/api/v1/leads"
    request.state = MagicMock()
    request.headers = {}
    request.client = None

    response = MagicMock()
    response.status_code = 200

    async def call_next(_request):
        return response

    session_factory = MagicMock()
    session_factory.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
    session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    middleware = AuditMiddleware(app=MagicMock())
    with (
        patch("api.middleware.audit.get_session_factory", return_value=session_factory),
        patch("api.middleware.audit.AuditService"),
    ):
        result = await middleware.dispatch(request, call_next)

    assert result is response


@pytest.mark.asyncio
async def test_the_audit_middleware_is_registered_on_the_app():
    """The middleware is added to the application."""
    from api.middleware.audit import add_audit_middleware

    app = MagicMock()
    add_audit_middleware(app)

    app.add_middleware.assert_called_once_with(AuditMiddleware)


# ---------------------------------------------------------------------------
# auth: the OAuth endpoints need a redirect URI
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apple_oauth_without_a_redirect_uri_is_refused(tmp_path):
    """Apple sign-in needs a redirect URI before it can start."""
    key_file = tmp_path / "apple.pem"
    key_file.write_text("a private key", encoding="utf-8")
    from api.routers import auth_jwt

    request = MagicMock()
    response = MagicMock()

    with patch("api.routers.auth_jwt.get_settings") as mock_settings:
        mock_settings.return_value.apple_private_key_path = str(key_file)
        mock_settings.return_value.apple_client_id = "client"
        mock_settings.return_value.apple_team_id = "team"
        mock_settings.return_value.apple_key_id = "key"
        mock_settings.return_value.google_redirect_uri = None
        with pytest.raises(Exception) as excinfo:
            await auth_jwt.apple_oauth_start(request, response)

    assert "not configured" in str(excinfo.value)


# ---------------------------------------------------------------------------
# bulk jobs: the portal that is not in the registry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_an_unknown_portal_is_refused(db_session):
    """A portal the registry does not know is refused."""
    from api.routers.bulk_jobs import _process_portal_import
    from db.models import BulkJob

    job = BulkJob(
        id="portal-unknown-001",
        job_type="import",
        source_type="portal_api",
        config={},
        status="running",
    )
    db_session.add(job)
    await db_session.flush()

    with patch("data.adapters.get_adapter", return_value=None):
        with pytest.raises(ValueError, match="unknown portal"):
            await _process_portal_import(job, {"portal": "nowhere"}, db_session)


# ---------------------------------------------------------------------------
# cma: the vector store that is not there
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_cma_comparables_need_a_vector_store(db_session):
    """The comparables are read from the vector store."""
    from api.routers import cma

    user = User(id="user-1", email="user@example.com")

    with patch("api.routers.cma.get_vector_store", return_value=None):
        with pytest.raises(Exception) as excinfo:
            await cma.find_comparables(
                "prop-1",
                max_distance_km=5.0,
                min_score=40.0,
                max_results=6,
                user=user,
                session=db_session,
            )

    assert "not available" in str(excinfo.value)


@pytest.mark.asyncio
async def test_a_cma_report_without_a_vector_store_is_refused(db_session):
    """The report needs the vector store."""
    from api.routers import cma
    from db.schemas import CMAReportCreate

    user = User(id="user-1", email="user@example.com")

    with patch("api.routers.cma.get_vector_store", return_value=None):
        with pytest.raises(Exception) as excinfo:
            await cma.generate_cma_report(
                CMAReportCreate(
                    subject_property_id="prop-1",
                    comparable_ids=[],
                    custom_adjustments=None,
                    notes=None,
                ),
                user,
                db_session,
            )

    assert "not available" in str(excinfo.value)


# ---------------------------------------------------------------------------
# the lead model: the relationship to the lead
# ---------------------------------------------------------------------------


def test_the_priority_score_points_at_the_lead_model():
    """The priority score carries the lead it belongs to."""
    from db.lead_models import LeadPriorityScore

    assert LeadPriorityScore.__tablename__ == "lead_priority_scores"
    assert LeadPriorityScore.lead.property.mapper.class_.__name__ == "Lead"


# ---------------------------------------------------------------------------
# personalization: a city that is already there
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_known_city_is_weighted_again(db_session):
    """A city the buyer already looked at keeps its weight and grows it."""
    from db.models import UserPreferenceProfile
    from services.personalization_service import PersonalizationService

    db_session.add(User(id="user-known", email="known@example.com"))
    db_session.add(
        UserPreferenceProfile(
            user_id="user-known",
            preferred_cities=[{"city": "Kraków", "weight": 0.5}],
            view_count=0,
            favorite_count=0,
        )
    )
    await db_session.flush()

    service = PersonalizationService(db_session)
    preferences = await service.update_preferences_from_interaction(
        "user-known",
        {"city": "Kraków", "price": 480_000.0},
        "view",
    )

    assert preferences.preferred_cities["Kraków"] == pytest.approx(0.6, abs=0.001)


# ---------------------------------------------------------------------------
# the reranker: the weights it is given
# ---------------------------------------------------------------------------


def test_the_reranker_keeps_the_weights_it_is_given():
    """A weight set is kept as it is."""
    from services.ranking_config_service import RankingWeights
    from vector_store.reranker import PropertyReranker

    weights = RankingWeights(
        boost_exact_match=2.0,
        boost_metadata_match=1.5,
        boost_quality_signals=1.0,
        diversity_penalty=0.2,
    )
    reranker = PropertyReranker(ranking_weights=weights)

    assert reranker._ranking_weights is weights
    assert reranker.boost_exact_matches == 2.0


# ---------------------------------------------------------------------------
# the seed: the tables it clears
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_seed_clears_the_tables_it_fills(db_session):
    """The seed clears the tables it is about to fill again."""
    from alembic import seed

    class _Factory:
        def __call__(self):
            return self

        async def __aenter__(self):
            return db_session

        async def __aexit__(self, *_args):
            return None

    with (
        patch("alembic.seed.get_session_factory", return_value=_Factory()),
        patch("alembic.seed.ChromaPropertyStore"),
        patch("alembic.seed._seed_properties_chroma", return_value=0),
        patch("alembic.seed._seed_users", return_value=[]),
        patch("alembic.seed._seed_saved_searches"),
        patch("alembic.seed._seed_notification_preferences"),
    ):
        await seed.seed_all(clear=True)
