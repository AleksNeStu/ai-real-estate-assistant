"""
Unit tests for SearchMetricsService.

Tests search event recording, interaction tracking, and metrics calculation.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import ABExperiment, RankingConfig, SearchEvent
from services.search_metrics_service import (
    InteractionData,
    SearchMetricsService,
    SearchMetricsSummary,
    get_search_metrics_service,
)


@pytest.fixture
def search_metrics_service(db_session: AsyncSession) -> SearchMetricsService:
    """Create a SearchMetricsService instance."""
    return SearchMetricsService(db_session)


@pytest.fixture
async def ranking_config(db_session: AsyncSession) -> RankingConfig:
    """Create a ranking configuration for tests."""
    config = RankingConfig(
        name="metrics_test_config",
        description="Config for metrics tests",
        alpha=0.7,
        boost_exact_match=1.5,
        is_active=True,
    )
    db_session.add(config)
    await db_session.commit()
    await db_session.refresh(config)
    return config


@pytest.fixture
async def search_event(
    db_session: AsyncSession,
    ranking_config: RankingConfig,
) -> SearchEvent:
    """Create a search event for tests."""
    event = SearchEvent(
        session_id="test-session-123",
        query="apartments in Warsaw",
        results_count=10,
        results_property_ids=["prop1", "prop2", "prop3", "prop4", "prop5"],
        processing_time_ms=150,
        ranking_config_id=str(ranking_config.id),
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    return event


# =============================================================================
# Test record_search_event
# =============================================================================


@pytest.mark.asyncio
async def test_record_search_event(
    search_metrics_service: SearchMetricsService,
    ranking_config: RankingConfig,
):
    """Test recording a search event."""
    event = await search_metrics_service.record_search_event(
        session_id="new-session",
        query="2 bedroom Krakow",
        results_count=5,
        results_property_ids=["p1", "p2", "p3", "p4", "p5"],
        processing_time_ms=100,
        ranking_config_id=str(ranking_config.id),
    )

    assert event.id is not None
    assert event.session_id == "new-session"
    assert event.query == "2 bedroom Krakow"
    assert event.results_count == 5
    assert event.processing_time_ms == 100


@pytest.mark.asyncio
async def test_record_search_event_with_user(
    search_metrics_service: SearchMetricsService,
    ranking_config: RankingConfig,
):
    """Test recording a search event with user ID."""
    event = await search_metrics_service.record_search_event(
        session_id="user-session",
        query="test query",
        results_count=3,
        results_property_ids=["a", "b", "c"],
        processing_time_ms=50,
        user_id="user-123",
        ranking_config_id=str(ranking_config.id),
    )

    assert event.user_id == "user-123"


@pytest.mark.asyncio
async def test_record_search_event_with_experiment(
    search_metrics_service: SearchMetricsService,
    ranking_config: RankingConfig,
    experiment: ABExperiment,
):
    """Test recording a search event with experiment ID."""
    event = await search_metrics_service.record_search_event(
        session_id="exp-session",
        query="test query",
        results_count=2,
        results_property_ids=["x", "y"],
        processing_time_ms=75,
        experiment_id="exp-123",
        ranking_config_id=str(ranking_config.id),
    )

    assert event.experiment_id == "exp-123"


# =============================================================================
# Test record_interaction
# =============================================================================


@pytest.mark.asyncio
async def test_record_interaction(
    search_metrics_service: SearchMetricsService,
    search_event: SearchEvent,
):
    """Test recording an interaction."""
    data = InteractionData(
        search_event_id=str(search_event.id),
        property_id="prop1",
        position=0,
        viewed=True,
        clicked=True,
    )

    interaction = await search_metrics_service.record_interaction(data)

    assert interaction.id is not None
    assert interaction.search_event_id == search_event.id
    assert interaction.property_id == "prop1"
    assert interaction.position == 0
    assert interaction.viewed is True
    assert interaction.clicked is True


@pytest.mark.asyncio
async def test_record_interaction_with_dwell_time(
    search_metrics_service: SearchMetricsService,
    search_event: SearchEvent,
):
    """Test recording an interaction with dwell time."""
    data = InteractionData(
        search_event_id=str(search_event.id),
        property_id="prop2",
        position=1,
        viewed=True,
        view_duration_ms=5000,
    )

    interaction = await search_metrics_service.record_interaction(data)

    assert interaction.view_duration_ms == 5000


@pytest.mark.asyncio
async def test_record_interaction_all_types(
    search_metrics_service: SearchMetricsService,
    search_event: SearchEvent,
):
    """Test recording all interaction types."""
    data = InteractionData(
        search_event_id=str(search_event.id),
        property_id="prop3",
        position=2,
        viewed=True,
        clicked=True,
        favorited=True,
        contacted=True,
    )

    interaction = await search_metrics_service.record_interaction(data)

    assert interaction.viewed is True
    assert interaction.clicked is True
    assert interaction.favorited is True
    assert interaction.contacted is True


# =============================================================================
# Test record_click and record_view convenience methods
# =============================================================================


@pytest.mark.asyncio
async def test_record_click(
    search_metrics_service: SearchMetricsService,
    search_event: SearchEvent,
):
    """Test the record_click convenience method."""
    interaction = await search_metrics_service.record_click(
        search_event_id=str(search_event.id),
        property_id="prop1",
        position=0,
    )

    assert interaction.clicked is True
    assert interaction.viewed is True


@pytest.mark.asyncio
async def test_record_view(
    search_metrics_service: SearchMetricsService,
    search_event: SearchEvent,
):
    """Test the record_view convenience method."""
    interaction = await search_metrics_service.record_view(
        search_event_id=str(search_event.id),
        property_id="prop2",
        position=1,
        view_duration_ms=3000,
    )

    assert interaction.viewed is True
    assert interaction.view_duration_ms == 3000


# =============================================================================
# Test calculate_ctr
# =============================================================================


@pytest.mark.asyncio
async def test_calculate_ctr_no_data(search_metrics_service: SearchMetricsService):
    """Test CTR calculation with no data."""
    ctr = await search_metrics_service.calculate_ctr()

    assert ctr == 0.0


@pytest.mark.asyncio
async def test_calculate_ctr_with_clicks(
    search_metrics_service: SearchMetricsService,
    search_event: SearchEvent,
):
    """Test CTR calculation with clicks."""
    # Record some clicks
    await search_metrics_service.record_click(str(search_event.id), "prop1", 0)
    await search_metrics_service.record_click(str(search_event.id), "prop2", 1)

    ctr = await search_metrics_service.calculate_ctr()

    # 2 clicks / 10 results = 0.2
    assert ctr == 0.2


@pytest.mark.asyncio
async def test_calculate_ctr_filters_by_config(
    search_metrics_service: SearchMetricsService,
    ranking_config: RankingConfig,
    db_session: AsyncSession,
):
    """Test CTR calculation filters by ranking config."""
    # Create event with one config
    event1 = await search_metrics_service.record_search_event(
        session_id="session-1",
        query="query1",
        results_count=5,
        results_property_ids=["a", "b", "c", "d", "e"],
        processing_time_ms=100,
        ranking_config_id=str(ranking_config.id),
    )

    # Create another config and event
    config2 = RankingConfig(name="config2", alpha=0.5)
    db_session.add(config2)
    await db_session.commit()
    await db_session.refresh(config2)

    event2 = SearchEvent(
        session_id="session-2",
        query="query2",
        results_count=5,
        results_property_ids=["f", "g", "h", "i", "j"],
        processing_time_ms=100,
        ranking_config_id=str(config2.id),
    )
    db_session.add(event2)
    await db_session.commit()
    await db_session.refresh(event2)

    # Record clicks on both
    await search_metrics_service.record_click(str(event1.id), "a", 0)
    await search_metrics_service.record_click(str(event2.id), "f", 0)

    # Filter by first config only
    ctr = await search_metrics_service.calculate_ctr(ranking_config_id=str(ranking_config.id))

    # 1 click / 5 results = 0.2
    assert ctr == 0.2


# =============================================================================
# Test calculate_mrr
# =============================================================================


@pytest.mark.asyncio
async def test_calculate_mrr_no_clicks(search_metrics_service: SearchMetricsService):
    """Test MRR calculation with no clicks."""
    mrr = await search_metrics_service.calculate_mrr()

    assert mrr == 0.0


@pytest.mark.asyncio
async def test_calculate_mrr_first_position(
    search_metrics_service: SearchMetricsService,
    search_event: SearchEvent,
):
    """Test MRR when first click is at position 0."""
    await search_metrics_service.record_click(str(search_event.id), "prop1", 0)

    mrr = await search_metrics_service.calculate_mrr()

    # 1 / (0 + 1) = 1.0
    assert mrr == 1.0


@pytest.mark.asyncio
async def test_calculate_mrr_second_position(
    search_metrics_service: SearchMetricsService,
    search_event: SearchEvent,
):
    """Test MRR when first click is at position 1."""
    await search_metrics_service.record_click(str(search_event.id), "prop2", 1)

    mrr = await search_metrics_service.calculate_mrr()

    # 1 / (1 + 1) = 0.5
    assert mrr == 0.5


@pytest.mark.asyncio
async def test_calculate_mrr_multiple_searches(
    search_metrics_service: SearchMetricsService,
    ranking_config: RankingConfig,
):
    """Test MRR with multiple searches."""
    # Search 1: click at position 0 -> RR = 1.0
    event1 = await search_metrics_service.record_search_event(
        session_id="mrr-session-1",
        query="query1",
        results_count=5,
        results_property_ids=["a", "b", "c", "d", "e"],
        processing_time_ms=100,
        ranking_config_id=str(ranking_config.id),
    )
    await search_metrics_service.record_click(str(event1.id), "a", 0)

    # Search 2: click at position 2 -> RR = 0.33
    event2 = await search_metrics_service.record_search_event(
        session_id="mrr-session-2",
        query="query2",
        results_count=5,
        results_property_ids=["f", "g", "h", "i", "j"],
        processing_time_ms=100,
        ranking_config_id=str(ranking_config.id),
    )
    await search_metrics_service.record_click(str(event2.id), "h", 2)

    mrr = await search_metrics_service.calculate_mrr()

    # (1.0 + 0.33) / 2 ≈ 0.666
    assert 0.6 < mrr < 0.7


# =============================================================================
# Test calculate_ndcg
# =============================================================================


@pytest.mark.asyncio
async def test_calculate_ndcg_no_interactions(
    search_metrics_service: SearchMetricsService,
):
    """Test NDCG with no interactions."""
    ndcg = await search_metrics_service.calculate_ndcg()

    assert ndcg == 0.0


@pytest.mark.asyncio
async def test_calculate_ndcg_single_click(
    search_metrics_service: SearchMetricsService,
    search_event: SearchEvent,
):
    """Test NDCG with a single click at position 0."""
    await search_metrics_service.record_click(str(search_event.id), "prop1", 0)

    ndcg = await search_metrics_service.calculate_ndcg(k=10)

    # Single relevant item at position 0 = perfect NDCG
    assert ndcg == 1.0


@pytest.mark.asyncio
async def test_calculate_ndcg_with_favorites(
    search_metrics_service: SearchMetricsService,
    search_event: SearchEvent,
):
    """Test NDCG with favorites (higher gain)."""
    # Click at position 0 (gain=1)
    await search_metrics_service.record_click(str(search_event.id), "prop1", 0)

    # Click + favorite at position 1 (gain=2)
    data = InteractionData(
        search_event_id=str(search_event.id),
        property_id="prop2",
        position=1,
        clicked=True,
        favorited=True,
    )
    await search_metrics_service.record_interaction(data)

    ndcg = await search_metrics_service.calculate_ndcg(k=10)

    # NDCG should be < 1.0 because higher gain is at lower position
    assert 0.5 < ndcg < 1.0


# =============================================================================
# Test calculate_avg_dwell_time
# =============================================================================


@pytest.mark.asyncio
async def test_calculate_avg_dwell_time_no_data(
    search_metrics_service: SearchMetricsService,
):
    """Test average dwell time with no data."""
    avg = await search_metrics_service.calculate_avg_dwell_time()

    assert avg == 0.0


@pytest.mark.asyncio
async def test_calculate_avg_dwell_time(
    search_metrics_service: SearchMetricsService,
    search_event: SearchEvent,
):
    """Test average dwell time calculation."""
    # Record views with different dwell times
    await search_metrics_service.record_view(
        str(search_event.id), "prop1", 0, view_duration_ms=1000
    )
    await search_metrics_service.record_view(
        str(search_event.id), "prop2", 1, view_duration_ms=3000
    )

    avg = await search_metrics_service.calculate_avg_dwell_time()

    # (1000 + 3000) / 2 = 2000
    assert avg == 2000.0


# =============================================================================
# Test get_metrics_summary
# =============================================================================


@pytest.mark.asyncio
async def test_get_metrics_summary_empty(
    search_metrics_service: SearchMetricsService,
):
    """Test metrics summary with no data."""
    summary = await search_metrics_service.get_metrics_summary()

    assert isinstance(summary, SearchMetricsSummary)
    assert summary.total_searches == 0
    assert summary.total_clicks == 0
    assert summary.avg_ctr == 0.0


@pytest.mark.asyncio
async def test_get_metrics_summary_with_data(
    search_metrics_service: SearchMetricsService,
    search_event: SearchEvent,
):
    """Test metrics summary with data."""
    # Record some interactions (different properties to avoid unique constraint)
    await search_metrics_service.record_click(str(search_event.id), "prop1", 0)
    await search_metrics_service.record_click(str(search_event.id), "prop2", 1)
    await search_metrics_service.record_view(
        str(search_event.id), "prop3", 2, view_duration_ms=5000
    )

    summary = await search_metrics_service.get_metrics_summary()

    assert summary.total_searches == 1
    assert summary.total_clicks == 2
    assert summary.total_views == 3  # 2 clicks (viewed=True) + 1 view
    assert summary.avg_ctr == 0.2  # 2 clicks / 10 results
    assert summary.avg_results_per_search == 10
    assert summary.avg_processing_time_ms == 150


@pytest.mark.asyncio
async def test_get_metrics_summary_date_filter(
    search_metrics_service: SearchMetricsService,
    ranking_config: RankingConfig,
):
    """Test metrics summary with date filtering."""
    # Create event in the past (should be filtered out)
    past_date = datetime.now(UTC) - timedelta(days=30)

    old_event = SearchEvent(
        session_id="old-session",
        query="old query",
        results_count=5,
        results_property_ids=["old1", "old2"],
        processing_time_ms=100,
        ranking_config_id=str(ranking_config.id),
        search_timestamp=past_date,
    )
    search_metrics_service.session.add(old_event)
    await search_metrics_service.session.commit()

    # Get summary for last 7 days only
    start = datetime.now(UTC) - timedelta(days=7)
    summary = await search_metrics_service.get_metrics_summary(
        start_date=start, end_date=datetime.now(UTC)
    )

    assert summary.total_searches == 0


# =============================================================================
# Test compare_configs
# =============================================================================


@pytest.mark.asyncio
async def test_compare_configs(
    search_metrics_service: SearchMetricsService,
    ranking_config: RankingConfig,
    db_session: AsyncSession,
):
    """Test comparing metrics across configs."""
    # Create second config
    config2 = RankingConfig(name="compare_config2", alpha=0.6)
    db_session.add(config2)
    await db_session.commit()
    await db_session.refresh(config2)

    # Create events for both configs
    event1 = await search_metrics_service.record_search_event(
        session_id="compare-session-1",
        query="query1",
        results_count=5,
        results_property_ids=["a", "b", "c", "d", "e"],
        processing_time_ms=100,
        ranking_config_id=str(ranking_config.id),
    )
    await search_metrics_service.record_click(str(event1.id), "a", 0)

    event2 = await search_metrics_service.record_search_event(
        session_id="compare-session-2",
        query="query2",
        results_count=5,
        results_property_ids=["f", "g", "h", "i", "j"],
        processing_time_ms=100,
        ranking_config_id=str(config2.id),
    )
    await search_metrics_service.record_click(str(event2.id), "f", 0)
    await search_metrics_service.record_click(str(event2.id), "g", 1)

    comparison = await search_metrics_service.compare_configs(
        [str(ranking_config.id), str(config2.id)]
    )

    assert len(comparison) == 2
    assert str(ranking_config.id) in comparison
    assert str(config2.id) in comparison

    # Config2 has higher CTR (2 clicks / 5 results vs 1/5)
    assert comparison[str(config2.id)].avg_ctr > comparison[str(ranking_config.id)].avg_ctr


# =============================================================================
# Test factory function
# =============================================================================


def test_get_search_metrics_service_factory(db_session: AsyncSession):
    """Test the factory function."""
    service = get_search_metrics_service(db_session)

    assert isinstance(service, SearchMetricsService)
    assert service.session == db_session


@pytest.fixture(autouse=True)
async def _the_test_users_exist(create_test_users):
    """The users the events belong to have to be real rows.

    The deployment enforces foreign keys, and a search event belongs to a user
    - so the user has to exist for the event to be writable at all.
    """
    await create_test_users("user-123")


@pytest.fixture
async def experiment(db_session: AsyncSession) -> ABExperiment:
    """An A/B experiment the search events can point at.

    The deployment enforces foreign keys, and a search event may name the
    experiment it ran under - so the experiment has to exist for the event to
    be writable at all.
    """
    from datetime import UTC, datetime

    config = RankingConfig(
        name="metrics_experiment_config",
        description="Config for the experiment test",
        alpha=0.7,
        boost_exact_match=1.5,
        is_active=False,
    )
    db_session.add(config)
    await db_session.flush()

    exp = ABExperiment(
        id="exp-123",
        name="metrics_experiment",
        control_config_id=str(config.id),
        treatment_config_id=str(config.id),
        start_date=datetime.now(UTC),
    )
    db_session.add(exp)
    await db_session.commit()
    await db_session.refresh(exp)
    return exp
