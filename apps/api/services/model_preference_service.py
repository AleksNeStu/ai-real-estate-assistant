"""
Model Preference Service (Task #87).

This service provides:
- CRUD operations for task-specific model preferences
- System default model configurations
- Model capability validation
- Cost estimation utilities
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security_utils import sanitize_for_log
from db.models import TASK_TYPES, TaskModelPreference

logger = logging.getLogger(__name__)


# System default models per task type
# All models use OpenRouter free tier — $0 cost, production quality.
# Override per-task via user preferences or request parameters.
SYSTEM_DEFAULTS: dict[str, dict[str, Any]] = {
    "chat": {
        "provider": "openrouter",
        "model_name": "nvidia/nemotron-3-super-120b-a12b:free",
        "description": "Nemotron 3 Super 120B — best free model, function calling, 262K ctx",
        "cost_per_1m_input_tokens": 0.0,
        "cost_per_1m_output_tokens": 0.0,
    },
    "search": {
        "provider": "openrouter",
        "model_name": "nvidia/nemotron-3-super-120b-a12b:free",
        "description": "Nemotron 3 Super 120B — fast search query processing",
        "cost_per_1m_input_tokens": 0.0,
        "cost_per_1m_output_tokens": 0.0,
    },
    "tools": {
        "provider": "openrouter",
        "model_name": "nvidia/nemotron-3-super-120b-a12b:free",
        "description": "Nemotron 3 Super 120B — tool execution with function calling",
        "cost_per_1m_input_tokens": 0.0,
        "cost_per_1m_output_tokens": 0.0,
    },
    "analysis": {
        "provider": "openrouter",
        "model_name": "nvidia/nemotron-3-super-120b-a12b:free",
        "description": "Nemotron 3 Super 120B — complex analysis and reasoning",
        "cost_per_1m_input_tokens": 0.0,
        "cost_per_1m_output_tokens": 0.0,
    },
    "embedding": {
        "provider": "openrouter",
        "model_name": "nvidia/nemotron-3-super-120b-a12b:free",
        "description": "ChromaDB uses FastEmbed locally; fallback for LLM-based tasks",
        "cost_per_1m_input_tokens": 0.0,
        "cost_per_1m_output_tokens": 0.0,
    },
}

# Available models per provider
AVAILABLE_MODELS: dict[str, list[str]] = {
    "openai": [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
        "text-embedding-3-small",
        "text-embedding-3-large",
    ],
    "anthropic": [
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229",
    ],
    "google": [
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-1.0-pro",
    ],
    "openrouter": [
        "nvidia/nemotron-3-super-120b-a12b:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "openai/gpt-oss-120b:free",
        "google/gemma-4-31b-it:free",
        "deepseek/deepseek-chat",
        "openai/gpt-4o-mini",
    ],
    "ollama": [
        "llama3.2:3b",
        "llama3.1:8b",
        "mistral:7b",
    ],
}


@dataclass
class ModelPreferenceData:
    """Dataclass for model preference data."""

    id: str
    user_id: str
    task_type: str
    provider: str
    model_name: str
    fallback_chain: Optional[list[dict[str, str]]] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class CostEstimate:
    """Cost estimate for model usage."""

    provider: str
    model_name: str
    input_cost_per_1m: Optional[float] = None
    output_cost_per_1m: Optional[float] = None
    estimated_tokens_per_request: int = 1000
    estimated_cost_per_request: Optional[float] = None


class ModelPreferenceService:
    """Service for managing per-task model preferences."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the service.

        Args:
            session: Database session
        """
        self.session = session

    async def get_user_preferences(self, user_id: str) -> list[TaskModelPreference]:
        """Get all model preferences for a user.

        Args:
            user_id: User ID

        Returns:
            List of TaskModelPreference objects
        """
        query = (
            select(TaskModelPreference)
            .where(TaskModelPreference.user_id == user_id)
            .order_by(TaskModelPreference.task_type)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_preference_by_task(
        self, user_id: str, task_type: str
    ) -> Optional[TaskModelPreference]:
        """Get model preference for a specific task type.

        Args:
            user_id: User ID
            task_type: Task type (chat, search, tools, analysis, embedding)

        Returns:
            TaskModelPreference if found, None otherwise
        """
        if task_type not in TASK_TYPES:
            raise ValueError(f"Invalid task_type: {task_type}. Must be one of {TASK_TYPES}")

        query = select(TaskModelPreference).where(
            and_(
                TaskModelPreference.user_id == user_id,
                TaskModelPreference.task_type == task_type,
            )
        )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_preference(
        self,
        user_id: str,
        task_type: str,
        provider: str,
        model_name: str,
        fallback_chain: Optional[list[dict[str, str]]] = None,
        is_active: bool = True,
    ) -> TaskModelPreference:
        """Create a new model preference.

        Args:
            user_id: User ID
            task_type: Task type
            provider: Provider name
            model_name: Model identifier
            fallback_chain: Ordered list of fallback models
            is_active: Whether the preference is active

        Returns:
            Created TaskModelPreference

        Raises:
            ValueError: If validation fails
        """
        # Validate task type
        if task_type not in TASK_TYPES:
            raise ValueError(f"Invalid task_type: {task_type}. Must be one of {TASK_TYPES}")

        # Validate provider and model
        self._validate_provider_model(provider, model_name)

        # Validate fallback chain
        if fallback_chain:
            self._validate_fallback_chain(fallback_chain, provider, model_name)

        # Check if preference already exists
        existing = await self.get_preference_by_task(user_id, task_type)
        if existing:
            raise ValueError(
                f"Preference already exists for task_type '{task_type}'. Use update instead."
            )

        preference = TaskModelPreference(
            id=str(uuid4()),
            user_id=user_id,
            task_type=task_type,
            provider=provider,
            model_name=model_name,
            fallback_chain=fallback_chain,
            is_active=is_active,
        )

        self.session.add(preference)
        await self.session.flush()
        await self.session.refresh(preference)

        logger.info(
            "Created model preference for user %s: %s/%s for task %s",
            sanitize_for_log(user_id[:8]),
            sanitize_for_log(provider),
            sanitize_for_log(model_name),
            sanitize_for_log(task_type),
        )

        return preference

    async def update_preference(
        self,
        user_id: str,
        preference_id: str,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        fallback_chain: Optional[list[dict[str, str]]] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[TaskModelPreference]:
        """Update an existing model preference.

        Args:
            user_id: User ID
            preference_id: Preference ID
            provider: New provider name
            model_name: New model identifier
            fallback_chain: New fallback chain
            is_active: New active status

        Returns:
            Updated TaskModelPreference if found, None otherwise
        """
        query = select(TaskModelPreference).where(
            and_(
                TaskModelPreference.id == preference_id,
                TaskModelPreference.user_id == user_id,
            )
        )

        result = await self.session.execute(query)
        preference = result.scalar_one_or_none()

        if not preference:
            return None

        # Update fields
        if provider is not None:
            preference.provider = provider

        if model_name is not None:
            preference.model_name = model_name

        if provider is not None or model_name is not None:
            self._validate_provider_model(preference.provider, preference.model_name)

        if fallback_chain is not None:
            self._validate_fallback_chain(
                fallback_chain, preference.provider, preference.model_name
            )
            preference.fallback_chain = fallback_chain

        if is_active is not None:
            preference.is_active = is_active

        preference.updated_at = datetime.now(UTC)

        await self.session.flush()
        await self.session.refresh(preference)

        logger.info(
            "Updated model preference %s for user %s",
            sanitize_for_log(preference_id[:8]),
            sanitize_for_log(user_id[:8]),
        )

        return preference

    async def delete_preference(self, user_id: str, preference_id: str) -> bool:
        """Delete a model preference.

        Args:
            user_id: User ID
            preference_id: Preference ID

        Returns:
            True if deleted, False if not found
        """
        query = delete(TaskModelPreference).where(
            and_(
                TaskModelPreference.id == preference_id,
                TaskModelPreference.user_id == user_id,
            )
        )

        result = await self.session.execute(query)

        if result.rowcount > 0:  # type: ignore[attr-defined]
            logger.info(
                "Deleted model preference %s for user %s",
                sanitize_for_log(preference_id[:8]),
                sanitize_for_log(user_id[:8]),
            )
            return True

        return False

    async def get_or_create_preference(self, user_id: str, task_type: str) -> TaskModelPreference:
        """Get existing preference or create with system default.

        Args:
            user_id: User ID
            task_type: Task type

        Returns:
            TaskModelPreference (existing or new with defaults)
        """
        existing = await self.get_preference_by_task(user_id, task_type)
        if existing:
            return existing

        # Create with system default
        default = SYSTEM_DEFAULTS.get(task_type, SYSTEM_DEFAULTS["chat"])
        return await self.create_preference(
            user_id=user_id,
            task_type=task_type,
            provider=default["provider"],
            model_name=default["model_name"],
        )

    def get_system_defaults(self) -> list[dict[str, Any]]:
        """Get system default model preferences.

        Returns:
            List of default configurations per task type
        """
        defaults = []
        for task_type, config in SYSTEM_DEFAULTS.items():
            defaults.append(
                {
                    "task_type": task_type,
                    "provider": config["provider"],
                    "model_name": config["model_name"],
                    "description": config.get("description"),
                    "cost_per_1m_input_tokens": config.get("cost_per_1m_input_tokens"),
                    "cost_per_1m_output_tokens": config.get("cost_per_1m_output_tokens"),
                }
            )
        return defaults

    def get_available_providers(self) -> list[str]:
        """Get list of available providers.

        Returns:
            List of provider names
        """
        return list(AVAILABLE_MODELS.keys())

    def get_available_models(self) -> dict[str, list[str]]:
        """Get available models per provider.

        Returns:
            Dictionary mapping provider names to model lists
        """
        return AVAILABLE_MODELS.copy()

    def get_cost_estimate(
        self,
        provider: str,
        model_name: str,
        estimated_tokens: int = 1000,
    ) -> CostEstimate:
        """Get cost estimate for using a model.

        Args:
            provider: Provider name
            model_name: Model identifier
            estimated_tokens: Estimated tokens per request

        Returns:
            CostEstimate with pricing information
        """
        # Try to find pricing in system defaults
        input_cost = None
        output_cost = None

        for config in SYSTEM_DEFAULTS.values():
            if config["provider"] == provider and config["model_name"] == model_name:
                input_cost = config.get("cost_per_1m_input_tokens")
                output_cost = config.get("cost_per_1m_output_tokens")
                break

        # Calculate estimated cost per request
        estimated_cost = None
        if input_cost is not None:
            # Assume 80% input, 20% output tokens
            input_tokens = int(estimated_tokens * 0.8)
            output_tokens = int(estimated_tokens * 0.2)

            input_cost_req = (input_cost / 1_000_000) * input_tokens
            output_cost_req = (output_cost or 0) / 1_000_000 * output_tokens
            estimated_cost = input_cost_req + output_cost_req

        return CostEstimate(
            provider=provider,
            model_name=model_name,
            input_cost_per_1m=input_cost,
            output_cost_per_1m=output_cost,
            estimated_tokens_per_request=estimated_tokens,
            estimated_cost_per_request=estimated_cost,
        )

    def _validate_provider_model(self, provider: str, model_name: str) -> None:
        """Validate provider and model combination.

        Args:
            provider: Provider name
            model_name: Model identifier

        Raises:
            ValueError: If provider or model is invalid
        """
        if provider not in AVAILABLE_MODELS:
            raise ValueError(
                f"Invalid provider: {provider}. "
                f"Available providers: {list(AVAILABLE_MODELS.keys())}"
            )

        if model_name not in AVAILABLE_MODELS[provider]:
            logger.warning(
                "Model '%s' not in known list for provider '%s'. Allowing for flexibility.",
                sanitize_for_log(model_name),
                sanitize_for_log(provider),
            )

    def _validate_fallback_chain(
        self,
        fallback_chain: list[dict[str, str]],
        primary_provider: str,
        primary_model: str,
    ) -> None:
        """Validate fallback chain configuration.

        Args:
            fallback_chain: List of fallback configurations
            primary_provider: Primary provider name
            primary_model: Primary model name

        Raises:
            ValueError: If fallback chain is invalid
        """
        if len(fallback_chain) > 5:
            raise ValueError("Fallback chain cannot exceed 5 models")

        # Check for duplicates including primary
        seen = {(primary_provider, primary_model)}
        for item in fallback_chain:
            if "provider" not in item or "model_name" not in item:
                raise ValueError("Each fallback must have 'provider' and 'model_name' fields")

            key = (item["provider"], item["model_name"])
            if key in seen:
                raise ValueError(f"Duplicate model in fallback chain: {key}")
            seen.add(key)

            # Validate provider/model exists
            self._validate_provider_model(item["provider"], item["model_name"])
