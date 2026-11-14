"""
Unit tests for ABTestingService.

Tests experiment management, variant assignment, and configuration retrieval.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import ABExperiment, RankingConfig
from services.ab_testing_service import ABTestingService, get_ab_testing_service


@pytest.fixture
def ab_testing_service(db_session: AsyncSession) -> ABTestingService:
    """Create an ABTestingService instance."""
    return ABTestingService(db_session)


@pytest.fixture
async def control_config(db_session: AsyncSession) -> RankingConfig:
    """Create a control ranking configuration."""
    config = RankingConfig(
        name="control_config",
        description="Control configuration for A/B test",
        alpha=0.7,
        boost_exact_match=1.5,
    )
    db_session.add(config)
    await db_session.commit()
    await db_session.refresh(config)
    return config


@pytest.fixture
async def treatment_config(db_session: AsyncSession) -> RankingConfig:
    """Create a treatment ranking configuration."""
    config = RankingConfig(
        name="treatment_config",
        description="Treatment configuration for A/B test",
        alpha=0.8,
        boost_exact_match=1.3,
    )
    db_session.add(config)
    await db_session.commit()
    await db_session.refresh(config)
    return config


@pytest.fixture
async def draft_experiment(
    db_session: AsyncSession,
    control_config: RankingConfig,
    treatment_config: RankingConfig,
) -> ABExperiment:
    """Create a draft experiment."""
    experiment = ABExperiment(
        name="draft_experiment",
        description="A draft experiment",
        control_config_id=str(control_config.id),
        treatment_config_id=str(treatment_config.id),
        traffic_split=0.5,
        status="draft",
        start_date=datetime.now(UTC),
    )
    db_session.add(experiment)
    await db_session.commit()
    await db_session.refresh(experiment)
    return experiment


@pytest.fixture
async def running_experiment(
    db_session: AsyncSession,
    control_config: RankingConfig,
    treatment_config: RankingConfig,
) -> ABExperiment:
    """Create a running experiment."""
    experiment = ABExperiment(
        name="running_experiment",
        description="A running experiment",
        control_config_id=str(control_config.id),
        treatment_config_id=str(treatment_config.id),
        traffic_split=0.5,
        status="running",
        start_date=datetime.now(UTC) - timedelta(days=1),
    )
    db_session.add(experiment)
    await db_session.commit()
    await db_session.refresh(experiment)
    return experiment


# =============================================================================
# Test get_active_experiment
# =============================================================================


@pytest.mark.asyncio
async def test_get_active_experiment_returns_running(
    ab_testing_service: ABTestingService,
    running_experiment: ABExperiment,
):
    """Test that get_active_experiment returns a running experiment."""
    result = await ab_testing_service.get_active_experiment()

    assert result is not None
    assert result.id == running_experiment.id
    assert result.status == "running"


@pytest.mark.asyncio
async def test_get_active_experiment_none_when_no_running(
    ab_testing_service: ABTestingService,
    draft_experiment: ABExperiment,
):
    """Test that get_active_experiment returns None when no experiment is running."""
    result = await ab_testing_service.get_active_experiment()

    assert result is None


@pytest.mark.asyncio
async def test_get_active_experiment_ignores_completed(
    db_session: AsyncSession,
    ab_testing_service: ABTestingService,
    control_config: RankingConfig,
    treatment_config: RankingConfig,
):
    """Test that completed experiments are not returned."""
    completed = ABExperiment(
        name="completed_experiment",
        control_config_id=str(control_config.id),
        treatment_config_id=str(treatment_config.id),
        traffic_split=0.5,
        status="completed",
        start_date=datetime.now(UTC) - timedelta(days=10),
        end_date=datetime.now(UTC) - timedelta(days=1),
    )
    db_session.add(completed)
    await db_session.commit()

    result = await ab_testing_service.get_active_experiment()

    assert result is None


# =============================================================================
# Test get_experiment_for_session
# =============================================================================


@pytest.mark.asyncio
async def test_get_experiment_for_session_creates_assignment(
    ab_testing_service: ABTestingService,
    running_experiment: ABExperiment,
):
    """Test that get_experiment_for_session creates a new assignment."""
    session_id = "test-session-123"

    assignment = await ab_testing_service.get_experiment_for_session(session_id)

    assert assignment is not None
    assert assignment.session_id == session_id
    assert assignment.experiment_id == running_experiment.id
    assert assignment.variant in ("control", "treatment")


@pytest.mark.asyncio
async def test_get_experiment_for_session_returns_existing(
    ab_testing_service: ABTestingService,
    running_experiment: ABExperiment,
    db_session: AsyncSession,
):
    """Test that existing assignment is returned for same session."""
    session_id = "test-session-456"

    # Create first assignment
    first = await ab_testing_service.get_experiment_for_session(session_id)

    # Get again - should return same assignment
    second = await ab_testing_service.get_experiment_for_session(session_id)

    assert first.id == second.id
    assert first.variant == second.variant


@pytest.mark.asyncio
async def test_get_experiment_for_session_none_when_no_experiment(
    ab_testing_service: ABTestingService,
    draft_experiment: ABExperiment,
):
    """Test that None is returned when no active experiment."""
    session_id = "test-session-789"

    result = await ab_testing_service.get_experiment_for_session(session_id)

    assert result is None


@pytest.mark.asyncio
async def test_get_experiment_for_session_with_user_id(
    ab_testing_service: ABTestingService,
    running_experiment: ABExperiment,
):
    """Test that assignment includes user_id when provided."""
    session_id = "test-session-with-user"
    user_id = "user-123"

    assignment = await ab_testing_service.get_experiment_for_session(
        session_id=session_id, user_id=user_id
    )

    assert assignment is not None
    assert assignment.user_id == user_id


# =============================================================================
# Test _assign_variant
# =============================================================================


def test_assign_variant_deterministic(ab_testing_service: ABTestingService):
    """Test that variant assignment is deterministic."""
    session_id = "deterministic-test"
    experiment_id = "exp-123"

    # Call multiple times - should always return same result
    results = [
        ab_testing_service._assign_variant(session_id, experiment_id, 0.5) for _ in range(10)
    ]

    assert len(set(results)) == 1  # All results should be identical


def test_assign_variant_different_sessions(ab_testing_service: ABTestingService):
    """Test that different sessions get potentially different variants."""
    experiment_id = "exp-456"

    # Collect variants for many sessions
    variants = [
        ab_testing_service._assign_variant(f"session-{i}", experiment_id, 0.5) for i in range(100)
    ]

    # With 50/50 split and 100 sessions, we should get both variants
    control_count = sum(1 for v in variants if v == "control")
    treatment_count = sum(1 for v in variants if v == "treatment")

    # Allow some variance but expect roughly 50/50
    assert 20 < control_count < 80
    assert 20 < treatment_count < 80


def test_assign_variant_traffic_split(ab_testing_service: ABTestingService):
    """Test that traffic_split affects variant distribution."""
    experiment_id = "exp-789"

    # 80/20 split favoring treatment
    variants = [
        ab_testing_service._assign_variant(f"split-session-{i}", experiment_id, 0.8)
        for i in range(100)
    ]

    treatment_count = sum(1 for v in variants if v == "treatment")

    # With 80% treatment split, expect roughly 80 treatments
    assert 60 < treatment_count < 95


# =============================================================================
# Test get_ranking_config_for_session
# =============================================================================


@pytest.mark.asyncio
async def test_get_ranking_config_for_session_returns_experiment_config(
    ab_testing_service: ABTestingService,
    running_experiment: ABExperiment,
    control_config: RankingConfig,
    treatment_config: RankingConfig,
):
    """Test that experiment config is returned when in experiment."""
    session_id = "config-test-session"

    config = await ab_testing_service.get_ranking_config_for_session(session_id)

    assert config is not None
    assert config.id in [control_config.id, treatment_config.id]


@pytest.mark.asyncio
async def test_get_ranking_config_for_session_returns_active_when_no_experiment(
    ab_testing_service: ABTestingService,
    draft_experiment: ABExperiment,
    db_session: AsyncSession,
):
    """Test that active config is returned when no experiment running."""
    # First deactivate all existing configs to avoid conflicts
    from sqlalchemy import update

    await db_session.execute(update(RankingConfig).values(is_active=False))
    await db_session.commit()

    # Create a new config specifically for this test and activate it
    active_config = RankingConfig(
        name="active_config_for_no_exp_test",
        description="Active config for no experiment test",
        alpha=0.7,
        is_active=True,
    )
    db_session.add(active_config)
    await db_session.commit()
    await db_session.refresh(active_config)

    session_id = "no-experiment-session"
    config = await ab_testing_service.get_ranking_config_for_session(session_id)

    assert config is not None
    assert config.id == active_config.id


# =============================================================================
# Test start_experiment
# =============================================================================


@pytest.mark.asyncio
async def test_start_experiment_success(
    ab_testing_service: ABTestingService,
    draft_experiment: ABExperiment,
):
    """Test starting a draft experiment."""
    result = await ab_testing_service.start_experiment(str(draft_experiment.id))

    assert result is not None
    assert result.status == "running"
    assert result.id == draft_experiment.id


@pytest.mark.asyncio
async def test_start_experiment_not_found(ab_testing_service: ABTestingService):
    """Test starting a non-existent experiment."""
    result = await ab_testing_service.start_experiment("non-existent-id")

    assert result is None


@pytest.mark.asyncio
async def test_start_experiment_already_running(
    ab_testing_service: ABTestingService,
    running_experiment: ABExperiment,
):
    """Test that starting an already running experiment fails."""
    with pytest.raises(ValueError, match="Can only start experiments in 'draft'"):
        await ab_testing_service.start_experiment(str(running_experiment.id))


# =============================================================================
# Test stop_experiment
# =============================================================================


@pytest.mark.asyncio
async def test_stop_experiment_success(
    ab_testing_service: ABTestingService,
    running_experiment: ABExperiment,
):
    """Test stopping a running experiment."""
    result = await ab_testing_service.stop_experiment(str(running_experiment.id))

    assert result is not None
    assert result.status == "completed"
    assert result.end_date is not None


@pytest.mark.asyncio
async def test_stop_experiment_with_reason(
    ab_testing_service: ABTestingService,
    running_experiment: ABExperiment,
):
    """Test stopping an experiment with a reason."""
    reason = "Statistical significance reached"
    result = await ab_testing_service.stop_experiment(str(running_experiment.id), reason=reason)

    assert result is not None
    assert result.status == "completed"


@pytest.mark.asyncio
async def test_stop_experiment_not_found(ab_testing_service: ABTestingService):
    """Test stopping a non-existent experiment."""
    result = await ab_testing_service.stop_experiment("non-existent-id")

    assert result is None


# =============================================================================
# Test factory function
# =============================================================================


def test_get_ab_testing_service_factory(db_session: AsyncSession):
    """Test the factory function."""
    service = get_ab_testing_service(db_session)

    assert isinstance(service, ABTestingService)
    assert service.session == db_session


@pytest.fixture(autouse=True)
async def _the_test_users_exist(create_test_users):
    """The users the assignments belong to have to be real rows.

    The deployment enforces foreign keys, and an assignment belongs to a user
    - so the user has to exist for the assignment to be writable at all.
    """
    await create_test_users("user-123")
