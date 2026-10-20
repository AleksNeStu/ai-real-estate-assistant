"""Unit tests for ModelPreferenceService (Task #87)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from services.model_preference_service import (
    AVAILABLE_MODELS,
    SYSTEM_DEFAULTS,
    CostEstimate,
    ModelPreferenceData,
    ModelPreferenceService,
)


@pytest.fixture
def mock_session():
    """Create a mock AsyncSession."""
    session = MagicMock(spec=AsyncSession)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def service(mock_session):
    """Create a ModelPreferenceService instance."""
    return ModelPreferenceService(mock_session)


@pytest.fixture
def sample_preference():
    """Create a sample TaskModelPreference."""
    from db.models import TaskModelPreference

    return TaskModelPreference(
        id=str(uuid4()),
        user_id="test-user-123",
        task_type="chat",
        provider="openai",
        model_name="gpt-4o-mini",
        fallback_chain=[{"provider": "anthropic", "model_name": "claude-3-5-sonnet-20241022"}],
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


class TestModelPreferenceServiceInit:
    """Tests for service initialization."""

    def test_init_stores_session(self, mock_session):
        """Test that service stores the session."""
        service = ModelPreferenceService(mock_session)
        assert service.session is mock_session


class TestGetUserPreferences:
    """Tests for get_user_preferences method."""

    @pytest.mark.asyncio
    async def test_returns_user_preferences(self, service, mock_session, sample_preference):
        """Test that method returns user preferences."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_preference]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        preferences = await service.get_user_preferences("test-user-123")

        assert len(preferences) == 1
        assert preferences[0] == sample_preference
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_empty_list_for_no_preferences(self, service, mock_session):
        """Test that method returns empty list when no preferences exist."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        preferences = await service.get_user_preferences("test-user-123")

        assert len(preferences) == 0


class TestGetPreferenceByTask:
    """Tests for get_preference_by_task method."""

    @pytest.mark.asyncio
    async def test_returns_preference_for_valid_task(
        self, service, mock_session, sample_preference
    ):
        """Test that method returns preference for valid task type."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_preference
        mock_session.execute.return_value = mock_result

        preference = await service.get_preference_by_task("test-user-123", "chat")

        assert preference == sample_preference

    @pytest.mark.asyncio
    async def test_raises_error_for_invalid_task_type(self, service):
        """Test that method raises ValueError for invalid task type."""
        with pytest.raises(ValueError, match="Invalid task_type"):
            await service.get_preference_by_task("test-user-123", "invalid_task")

    @pytest.mark.asyncio
    async def test_returns_none_for_nonexistent_preference(self, service, mock_session):
        """Test that method returns None when preference doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        preference = await service.get_preference_by_task("test-user-123", "chat")

        assert preference is None


class TestCreatePreference:
    """Tests for create_preference method."""

    @pytest.mark.asyncio
    async def test_creates_preference_with_valid_data(self, service, mock_session):
        """Test creating a preference with valid data."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # No existing preference
        mock_session.execute.return_value = mock_result

        preference = await service.create_preference(
            user_id="test-user-123",
            task_type="chat",
            provider="openai",
            model_name="gpt-4o-mini",
        )

        assert preference is not None
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_error_for_invalid_task_type(self, service):
        """Test that create raises ValueError for invalid task type."""
        with pytest.raises(ValueError, match="Invalid task_type"):
            await service.create_preference(
                user_id="test-user-123",
                task_type="invalid_task",
                provider="openai",
                model_name="gpt-4o-mini",
            )

    @pytest.mark.asyncio
    async def test_raises_error_for_invalid_provider(self, service):
        """Test that create raises ValueError for invalid provider."""
        with pytest.raises(ValueError, match="Invalid provider"):
            await service.create_preference(
                user_id="test-user-123",
                task_type="chat",
                provider="invalid_provider",
                model_name="some-model",
            )

    @pytest.mark.asyncio
    async def test_raises_error_for_existing_preference(
        self, service, mock_session, sample_preference
    ):
        """Test that create raises ValueError if preference already exists."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_preference
        mock_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Preference already exists"):
            await service.create_preference(
                user_id="test-user-123",
                task_type="chat",
                provider="openai",
                model_name="gpt-4o-mini",
            )

    @pytest.mark.asyncio
    async def test_creates_preference_with_fallback_chain(self, service, mock_session):
        """Test creating a preference with fallback chain."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        fallback_chain = [{"provider": "anthropic", "model_name": "claude-3-5-sonnet-20241022"}]

        preference = await service.create_preference(
            user_id="test-user-123",
            task_type="chat",
            provider="openai",
            model_name="gpt-4o-mini",
            fallback_chain=fallback_chain,
        )

        assert preference is not None


class TestUpdatePreference:
    """Tests for update_preference method."""

    @pytest.mark.asyncio
    async def test_updates_existing_preference(self, service, mock_session, sample_preference):
        """Test updating an existing preference."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_preference
        mock_session.execute.return_value = mock_result

        preference = await service.update_preference(
            user_id="test-user-123",
            preference_id=sample_preference.id,
            provider="anthropic",
            model_name="claude-3-5-sonnet-20241022",
        )

        assert preference is not None
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_none_for_nonexistent_preference(self, service, mock_session):
        """Test that update returns None when preference doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        preference = await service.update_preference(
            user_id="test-user-123",
            preference_id="nonexistent-id",
            provider="anthropic",
            model_name="claude-3-5-sonnet-20241022",
        )

        assert preference is None

    @pytest.mark.asyncio
    async def test_updates_is_active_flag(self, service, mock_session, sample_preference):
        """Test updating the is_active flag."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_preference
        mock_session.execute.return_value = mock_result

        preference = await service.update_preference(
            user_id="test-user-123",
            preference_id=sample_preference.id,
            is_active=False,
        )

        assert preference is not None


class TestDeletePreference:
    """Tests for delete_preference method."""

    @pytest.mark.asyncio
    async def test_deletes_existing_preference(self, service, mock_session):
        """Test deleting an existing preference."""
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        deleted = await service.delete_preference("test-user-123", "preference-id")

        assert deleted is True
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_false_for_nonexistent_preference(self, service, mock_session):
        """Test that delete returns False when preference doesn't exist."""
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        deleted = await service.delete_preference("test-user-123", "nonexistent-id")

        assert deleted is False


class TestGetOrCreatePreference:
    """Tests for get_or_create_preference method."""

    @pytest.mark.asyncio
    async def test_returns_existing_preference(self, service, mock_session, sample_preference):
        """Test that method returns existing preference if found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_preference
        mock_session.execute.return_value = mock_result

        preference = await service.get_or_create_preference("test-user-123", "chat")

        assert preference == sample_preference

    @pytest.mark.asyncio
    async def test_creates_default_preference_when_not_found(self, service, mock_session):
        """Test that method creates preference with defaults when not found."""
        # First call returns None (no existing preference)
        # Second call for create also returns None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        preference = await service.get_or_create_preference("test-user-123", "chat")

        assert preference is not None
        mock_session.add.assert_called_once()


class TestGetSystemDefaults:
    """Tests for get_system_defaults method."""

    def test_returns_all_task_types(self, service):
        """Test that method returns defaults for all task types."""
        defaults = service.get_system_defaults()

        assert len(defaults) == len(SYSTEM_DEFAULTS)
        task_types = [d["task_type"] for d in defaults]
        assert "chat" in task_types
        assert "search" in task_types
        assert "tools" in task_types
        assert "analysis" in task_types
        assert "embedding" in task_types

    def test_includes_pricing_information(self, service):
        """Test that defaults include pricing information."""
        defaults = service.get_system_defaults()

        for default in defaults:
            assert "cost_per_1m_input_tokens" in default
            assert "cost_per_1m_output_tokens" in default


class TestGetAvailableProviders:
    """Tests for get_available_providers method."""

    def test_returns_all_providers(self, service):
        """Test that method returns all available providers."""
        providers = service.get_available_providers()

        assert "openai" in providers
        assert "anthropic" in providers
        assert "google" in providers
        assert "ollama" in providers

    def test_returns_correct_count(self, service):
        """Test that method returns correct number of providers."""
        providers = service.get_available_providers()

        assert len(providers) == len(AVAILABLE_MODELS)


class TestGetAvailableModels:
    """Tests for get_available_models method."""

    def test_returns_models_per_provider(self, service):
        """Test that method returns models for each provider."""
        models = service.get_available_models()

        assert "openai" in models
        assert "gpt-4o" in models["openai"]
        assert "gpt-4o-mini" in models["openai"]

    def test_returns_copy_not_reference(self, service):
        """Test that method returns a copy, not the original dict."""
        models1 = service.get_available_models()
        models2 = service.get_available_models()

        # Modifying one should not affect the other
        models1["openai"] = []
        assert len(models2["openai"]) > 0


class TestGetCostEstimate:
    """Tests for get_cost_estimate method."""

    def test_returns_cost_estimate_for_known_model(self, service):
        """Test getting cost estimate for a known model."""
        estimate = service.get_cost_estimate(
            "openrouter", "nvidia/nemotron-3-super-120b-a12b:free", 1000
        )

        assert estimate.provider == "openrouter"
        assert estimate.model_name == "nvidia/nemotron-3-super-120b-a12b:free"
        assert estimate.input_cost_per_1m == 0.0
        assert estimate.output_cost_per_1m == 0.0
        assert estimate.estimated_tokens_per_request == 1000

    def test_calculates_estimated_cost(self, service):
        """Test that cost estimate includes calculated cost."""
        estimate = service.get_cost_estimate(
            "openrouter", "nvidia/nemotron-3-super-120b-a12b:free", 1000
        )

        # Free model: cost is 0.0
        assert estimate.estimated_cost_per_request is not None
        assert estimate.estimated_cost_per_request == 0.0

    def test_returns_estimate_for_unknown_model(self, service):
        """Test getting cost estimate for an unknown model."""
        estimate = service.get_cost_estimate("unknown", "unknown-model", 1000)

        assert estimate.provider == "unknown"
        assert estimate.model_name == "unknown-model"
        assert estimate.input_cost_per_1m is None
        assert estimate.output_cost_per_1m is None


class TestValidateProviderModel:
    """Tests for _validate_provider_model method."""

    def test_validates_known_provider_and_model(self, service):
        """Test validation passes for known provider and model."""
        # Should not raise any exception
        service._validate_provider_model("openai", "gpt-4o-mini")

    def test_raises_error_for_unknown_provider(self, service):
        """Test validation raises error for unknown provider."""
        with pytest.raises(ValueError, match="Invalid provider"):
            service._validate_provider_model("unknown_provider", "some-model")

    def test_warns_for_unknown_model(self, service):
        """Test validation warns but allows unknown model."""
        # Should not raise exception, just log warning
        service._validate_provider_model("openai", "unknown-model")


class TestValidateFallbackChain:
    """Tests for _validate_fallback_chain method."""

    def test_validates_valid_fallback_chain(self, service):
        """Test validation passes for valid fallback chain."""
        fallback_chain = [
            {"provider": "anthropic", "model_name": "claude-3-5-sonnet-20241022"},
            {"provider": "google", "model_name": "gemini-1.5-pro"},
        ]

        # Should not raise any exception
        service._validate_fallback_chain(fallback_chain, "openai", "gpt-4o-mini")

    def test_raises_error_for_too_long_chain(self, service):
        """Test validation raises error for chain exceeding 5 models."""
        fallback_chain = [
            {"provider": "anthropic", "model_name": "claude-3-5-sonnet-20241022"},
            {"provider": "google", "model_name": "gemini-1.5-pro"},
            {"provider": "openai", "model_name": "gpt-4o"},
            {"provider": "anthropic", "model_name": "claude-haiku-4-5-20251001"},
            {"provider": "google", "model_name": "gemini-1.5-flash"},
            {"provider": "openai", "model_name": "gpt-4-turbo"},
        ]

        with pytest.raises(ValueError, match="cannot exceed 5 models"):
            service._validate_fallback_chain(fallback_chain, "openai", "gpt-4o-mini")

    def test_raises_error_for_missing_provider(self, service):
        """Test validation raises error for missing provider field."""
        fallback_chain = [
            {"model_name": "claude-3-5-sonnet-20241022"},
        ]

        with pytest.raises(ValueError, match="must have 'provider' and 'model_name'"):
            service._validate_fallback_chain(fallback_chain, "openai", "gpt-4o-mini")

    def test_raises_error_for_missing_model_name(self, service):
        """Test validation raises error for missing model_name field."""
        fallback_chain = [
            {"provider": "anthropic"},
        ]

        with pytest.raises(ValueError, match="must have 'provider' and 'model_name'"):
            service._validate_fallback_chain(fallback_chain, "openai", "gpt-4o-mini")

    def test_raises_error_for_duplicate_in_chain(self, service):
        """Test validation raises error for duplicate in fallback chain."""
        fallback_chain = [
            {"provider": "openai", "model_name": "gpt-4o-mini"},  # Same as primary
        ]

        with pytest.raises(ValueError, match="Duplicate model"):
            service._validate_fallback_chain(fallback_chain, "openai", "gpt-4o-mini")


class TestCostEstimateDataclass:
    """Tests for CostEstimate dataclass."""

    def test_creates_with_required_fields(self):
        """Test creating CostEstimate with required fields."""
        estimate = CostEstimate(
            provider="openai",
            model_name="gpt-4o-mini",
        )

        assert estimate.provider == "openai"
        assert estimate.model_name == "gpt-4o-mini"
        assert estimate.estimated_tokens_per_request == 1000

    def test_creates_with_all_fields(self):
        """Test creating CostEstimate with all fields."""
        estimate = CostEstimate(
            provider="openai",
            model_name="gpt-4o-mini",
            input_cost_per_1m=0.15,
            output_cost_per_1m=0.60,
            estimated_tokens_per_request=2000,
            estimated_cost_per_request=0.00048,
        )

        assert estimate.input_cost_per_1m == 0.15
        assert estimate.output_cost_per_1m == 0.60


class TestModelPreferenceDataDataclass:
    """Tests for ModelPreferenceData dataclass."""

    def test_creates_with_required_fields(self):
        """Test creating ModelPreferenceData with required fields."""
        data = ModelPreferenceData(
            id="test-id",
            user_id="test-user",
            task_type="chat",
            provider="openai",
            model_name="gpt-4o-mini",
        )

        assert data.id == "test-id"
        assert data.user_id == "test-user"
        assert data.task_type == "chat"
        assert data.is_active is True

    def test_creates_with_fallback_chain(self):
        """Test creating ModelPreferenceData with fallback chain."""
        fallback = [{"provider": "anthropic", "model_name": "claude-3-5-sonnet-20241022"}]
        data = ModelPreferenceData(
            id="test-id",
            user_id="test-user",
            task_type="chat",
            provider="openai",
            model_name="gpt-4o-mini",
            fallback_chain=fallback,
        )

        assert data.fallback_chain == fallback
