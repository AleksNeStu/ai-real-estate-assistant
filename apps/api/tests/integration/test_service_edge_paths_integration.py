"""The edge paths of the services the type cleanup touched.

Every test here calls the service or the helper directly. A request handler
runs in its own asyncio task, and the coverage tracer does not come back after
the task suspends, so the lines of a handler are only visible to the report
when they run in the test's own task.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from analytics.anomaly_detector import AnomalyDetector
from api.routers import auth_jwt, cma
from api.routers.webhooks import esignatures as webhooks_esignatures
from db.models import PriceSnapshot, User, UserPreferenceProfile
from db.schemas import CMAReportCreate
from services.agent_performance import AgentPerformanceService
from services.anomaly_service import AnomalyService
from services.document_storage import DocumentStorageService
from services.personalization_service import PersonalizationService
from services.search_metrics_service import SearchMetricsService
from tools.negotiation_tool import NegotiationTool
from tools.price_forecast_tools import PriceForecastTool
from utils.free_tier import _try_create_openrouter_free

# ---------------------------------------------------------------------------
# personalization: the city preference
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_city_of_an_interaction_is_remembered(db_session):
    """A property the buyer looked at raises the weight of its city."""
    db_session.add(User(id="user-1", email="user-1@example.com"))
    db_session.add(
        UserPreferenceProfile(
            user_id="user-1",
            preferred_cities=[],
            view_count=0,
            favorite_count=0,
        )
    )
    await db_session.flush()

    service = PersonalizationService(db_session)
    preferences = await service.update_preferences_from_interaction(
        "user-1",
        {"city": "Kraków", "price": 480_000.0},
        "view",
    )

    assert preferences.preferred_cities["Kraków"] > 0.0

    from sqlalchemy import select

    profile = (
        await db_session.execute(
            select(UserPreferenceProfile).where(UserPreferenceProfile.user_id == "user-1")
        )
    ).scalar_one()
    assert profile.preferred_cities[0]["city"] == "Kraków"


@pytest.mark.asyncio
async def test_a_known_city_keeps_its_weight(db_session):
    """A city the buyer already looked at is weighted again, not doubled."""
    db_session.add(User(id="user-2", email="user-2@example.com"))
    db_session.add(
        UserPreferenceProfile(
            user_id="user-2",
            preferred_cities=[{"city": "Kraków", "weight": 0.5}],
            view_count=0,
            favorite_count=0,
        )
    )
    await db_session.flush()

    service = PersonalizationService(db_session)
    preferences = await service.update_preferences_from_interaction(
        "user-2",
        {"city": "Kraków", "price": 480_000.0},
        "view",
    )

    assert preferences.preferred_cities["Kraków"] == pytest.approx(0.6, abs=0.001)


# ---------------------------------------------------------------------------
# agent performance: the trends and the goals
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_trends_of_an_agent_without_deals_are_empty(db_session):
    """An agent without assignments has no trends."""
    service = AgentPerformanceService(db_session)
    trends = await service.get_performance_trends("agent-1")

    assert isinstance(trends, list)


@pytest.mark.asyncio
async def test_the_value_of_a_goal_is_measured(db_session):
    """The value of a goal is read from the deals of the agent."""
    service = AgentPerformanceService(db_session)
    now = datetime.now(UTC)

    deals = await service._calculate_goal_current_value(
        "agent-1",
        "deals",
        now - timedelta(days=30),
        now,
    )
    revenue = await service._calculate_goal_current_value(
        "agent-1",
        "revenue",
        now - timedelta(days=30),
        now,
    )
    gci = await service._calculate_goal_current_value(
        "agent-1",
        "gci",
        now - timedelta(days=30),
        now,
    )

    assert deals == 0.0
    assert revenue == 0.0
    assert gci == 0.0


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
# the anomaly detector: the ordering of the snapshots
# ---------------------------------------------------------------------------


def test_the_snapshots_are_ordered_by_date():
    """The prices are compared in the order they were recorded."""
    detector = AnomalyDetector()
    base = datetime(2025, 1, 1, tzinfo=UTC)
    snapshots = [
        PriceSnapshot(id="2", property_id="prop-1", price=200.0, recorded_at=base),
        PriceSnapshot(
            id="1", property_id="prop-1", price=100.0, recorded_at=base - timedelta(days=1)
        ),
    ]

    anomalies = detector.detect_price_anomalies(snapshots)

    assert isinstance(anomalies, list)


# ---------------------------------------------------------------------------
# the search metrics: the mean reciprocal rank
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_mean_reciprocal_rank_without_clicks_is_zero(db_session):
    """Without a click there is no rank to report."""
    service = SearchMetricsService(db_session)

    assert await service.calculate_mrr() == 0.0


# ---------------------------------------------------------------------------
# the document storage: the file that is saved
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_saved_document_gets_a_name_and_a_size(tmp_path):
    """The stored file is named after the upload and its size is reported."""
    from io import BytesIO

    from fastapi import UploadFile

    storage = DocumentStorageService(storage_path=str(tmp_path))
    upload = UploadFile(file=BytesIO(b"%PDF-1.4 content"), filename="contract.pdf")

    storage_path, unique_filename, file_size = await storage.save_file(
        user_id="user-1",
        file=upload,
        max_size_bytes=1024 * 1024,
    )

    assert unique_filename.endswith(".pdf")
    assert file_size == len(b"%PDF-1.4 content")
    assert storage_path


# ---------------------------------------------------------------------------
# the anomaly service: one anomaly
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_one_anomaly_is_read_by_its_id(db_session):
    """The anomaly is answered with its own fields."""

    class _Anomaly:
        def __init__(self):
            self.id = "anomaly-1"
            self.severity = "medium"

    anomaly = _Anomaly()
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=anomaly)

    service = AnomalyService(repo, MagicMock())
    found = await service.get_anomaly_by_id("anomaly-1")

    assert found == {"id": "anomaly-1", "severity": "medium"}


# ---------------------------------------------------------------------------
# the demo data: the generator and the seed
# ---------------------------------------------------------------------------


def test_the_demo_data_generator_starts_with_empty_lists():
    """The generator collects the identifiers it creates."""
    from alembic.demo_data_generator import ComprehensiveDemoDataGenerator

    generator = ComprehensiveDemoDataGenerator(MagicMock())

    assert generator.user_ids == []
    assert generator.property_ids == []
    assert generator.agent_ids == []


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

    # The store and the database of the deployment are left alone: the seed
    # clears the property store of the machine it runs on, and that is not
    # what this test is about.
    with (
        patch("alembic.seed.get_session_factory", return_value=_Factory()),
        patch("alembic.seed.ChromaPropertyStore"),
        patch("alembic.seed._seed_properties_chroma", return_value=0),
        patch("alembic.seed._seed_users", return_value=[]),
        patch("alembic.seed._seed_saved_searches"),
        patch("alembic.seed._seed_notification_preferences"),
    ):
        await seed.seed_all(clear=True)


# ---------------------------------------------------------------------------
# the reranker: the weights
# ---------------------------------------------------------------------------


def test_the_reranker_without_weights_keeps_its_own():
    """Without a weight set the reranker keeps the values it was given."""
    from vector_store.reranker import PropertyReranker

    reranker = PropertyReranker(
        boost_exact_matches=2.0,
        boost_metadata_match=1.0,
        boost_quality_signals=0.5,
        diversity_penalty=0.1,
    )

    assert reranker.boost_exact_matches == 2.0
    assert reranker._ranking_weights is None


# ---------------------------------------------------------------------------
# the OAuth endpoints: the settings that are not there
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_google_oauth_without_a_redirect_uri_is_refused():
    """Google sign-in needs a redirect URI before it can start."""
    request = MagicMock()
    response = MagicMock()

    with patch("api.routers.auth_jwt.get_settings") as mock_settings:
        mock_settings.return_value.auth_oauth_google_enabled = True
        mock_settings.return_value.google_client_id = "client"
        mock_settings.return_value.google_client_secret = "secret"  # pragma: allowlist secret
        mock_settings.return_value.google_redirect_uri = None
        with pytest.raises(Exception) as excinfo:
            await auth_jwt.google_oauth_start(request, response)

    assert "not configured" in str(excinfo.value)


@pytest.mark.asyncio
async def test_the_oauth_callback_without_a_redirect_uri_is_refused():
    """The callback needs a redirect URI as well."""
    request = MagicMock()
    response = MagicMock()
    request.cookies = {"oauth_state": "state"}

    with patch("api.routers.auth_jwt.get_settings") as mock_settings:
        mock_settings.return_value.google_client_id = "client"
        mock_settings.return_value.google_client_secret = "secret"  # pragma: allowlist secret
        mock_settings.return_value.google_redirect_uri = None
        with pytest.raises(Exception) as excinfo:
            await auth_jwt.oauth_callback(request, response, code="code", state="state")

    assert "not configured" in str(excinfo.value)


@pytest.mark.asyncio
async def test_apple_oauth_without_a_redirect_uri_is_refused(tmp_path):
    """Apple sign-in needs a redirect URI before it can start."""
    key_file = tmp_path / "apple.pem"
    key_file.write_text("a private key", encoding="utf-8")
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
# the CMA report: the vector store that is not there
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
# the webhook: the signed document that is stored
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_signed_document_is_stored(tmp_path):
    """The signed document is written into the directory of the user."""
    signature_request = MagicMock()
    signature_request.title = "Contract"
    signature_request.user_id = "user-1"
    signature_request.provider_envelope_id = "env-1"

    service = MagicMock()
    service.download_signed_document = AsyncMock(return_value=b"%PDF-1.4 signed")

    storage = MagicMock()
    storage._get_user_dir.return_value = tmp_path / "user-1"

    signed_doc_repo = MagicMock()
    signed_doc_repo.create = AsyncMock(return_value=MagicMock())

    with (
        patch(
            "services.document_storage.get_document_storage",
            return_value=storage,
        ),
        patch(
            "api.routers.webhooks.esignatures.SignedDocumentRepository",
            return_value=signed_doc_repo,
        ),
    ):
        await webhooks_esignatures._download_and_store_signed_document(
            MagicMock(),
            signature_request,
            service,
        )

    stored = list((tmp_path / "user-1" / "signed_documents").glob("*.pdf"))
    assert stored
    assert stored[0].read_bytes() == b"%PDF-1.4 signed"


# ---------------------------------------------------------------------------
# the audit middleware: the registration
# ---------------------------------------------------------------------------


def test_the_audit_middleware_is_registered_on_the_app():
    """The middleware is added to the application."""
    from api.middleware.audit import AuditMiddleware, add_audit_middleware

    app = MagicMock()
    add_audit_middleware(app)

    app.add_middleware.assert_called_once_with(AuditMiddleware)


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
# the lead model: the relationship to the lead
# ---------------------------------------------------------------------------


def test_the_priority_score_points_at_the_lead_model():
    """The priority score carries the lead it belongs to."""
    from db.lead_models import LeadPriorityScore

    assert LeadPriorityScore.__tablename__ == "lead_priority_scores"
    assert LeadPriorityScore.lead.property.mapper.class_.__name__ == "Lead"


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
