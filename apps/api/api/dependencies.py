from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import TYPE_CHECKING, Annotated, Any, Optional

from fastapi import Body, Depends, Header, HTTPException, Query, status
from langchain_core.language_models import BaseChatModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import models.user_model_preferences as user_model_preferences
from agents.hybrid_agent import HybridPropertyAgent, SimpleRAGAgent, create_hybrid_agent
from agents.services.crm_connector import CRMConnector, WebhookCRMConnector
from agents.services.data_enrichment import BasicDataEnrichmentService, DataEnrichmentService
from agents.services.legal_check import BasicLegalCheckService, LegalCheckService
from agents.services.valuation import SimpleValuationProvider, ValuationProvider
from api.models import RagQaRequest
from config.settings import settings
from db.models import User
from models.provider_factory import ModelProviderFactory
from services.model_preference_service import SYSTEM_DEFAULTS, ModelPreferenceService
from utils.circuit import get_circuit_breaker_manager

if TYPE_CHECKING:
    from data.enrichment.pipeline import EnrichmentPipeline
    from services.esignature_service import ESignatureService
    from services.template_service import TemplateService
    from vector_store.chroma_store import ChromaPropertyStore
    from vector_store.knowledge_store import KnowledgeStore

logger = logging.getLogger(__name__)

try:
    from vector_store.chroma_store import ChromaPropertyStore  # type: ignore
except Exception as e:
    logger.warning("ChromaPropertyStore not available, vector search disabled: %s", e)
    ChromaPropertyStore = None  # type: ignore

try:
    from vector_store.knowledge_store import KnowledgeStore  # type: ignore
except Exception as e:
    logger.warning("KnowledgeStore not available, knowledge RAG disabled: %s", e)
    KnowledgeStore = None  # type: ignore


@lru_cache()
def get_vector_store() -> Optional[ChromaPropertyStore]:
    """
    Get cached vector store instance for API.
    Returns None if embeddings are not available.
    """
    if ChromaPropertyStore is None:
        return None
    try:
        store = ChromaPropertyStore(
            persist_directory=str(settings.chroma_dir),
            collection_name="properties",
            embedding_model=settings.embedding_model,
        )
        return store
    except Exception as e:
        logger.warning("Vector store initialization failed: %s", e)
        return None


PROVIDER_ENV_VAR_MAP = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "grok": "XAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "zai": "ZHIPUAI_API_KEY",
    "moonshot": "MOONSHOT_API_KEY",
    "groq": "GROQ_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "qwen": "DASHSCOPE_API_KEY",
}


def _create_llm(provider_name: str, model_id: Optional[str]) -> BaseChatModel:
    llm, _resolved_model_id = _create_llm_with_resolved_model_id(
        provider_name=provider_name, model_id=model_id
    )
    return llm


@lru_cache(maxsize=16)
def _create_llm_with_resolved_model_id(
    provider_name: str, model_id: Optional[str]
) -> tuple[BaseChatModel, str]:
    # Check if demo mode is enabled (from env var)
    # Note: For per-session demo mode, the session check would happen in the calling function
    if os.getenv("DEMO_MODE", "false").lower() == "true":
        from core.demo import get_demo_llm

        logger.info("Demo mode enabled — using MockLLM (no real API calls)")
        return get_demo_llm(), "demo-mock"

    factory_provider = ModelProviderFactory.get_provider(provider_name)
    resolved_model_id = model_id

    if not resolved_model_id:
        if provider_name == "ollama" and getattr(settings, "ollama_default_model", None):
            resolved_model_id = settings.ollama_default_model
        else:
            models = factory_provider.list_models()
            if not models:
                raise RuntimeError(f"No models available for provider '{provider_name}'")
            resolved_model_id = models[0].id

    # Add Sentry breadcrumb for LLM creation (Task #56)
    try:
        from api.sentry_init import add_llm_breadcrumb

        add_llm_breadcrumb(provider=provider_name, model=resolved_model_id)
    except Exception as e:
        logger.debug("Sentry breadcrumb skipped: %s", e)

    llm = factory_provider.create_model(
        model_id=resolved_model_id,
        temperature=settings.default_temperature,
        max_tokens=settings.default_max_tokens,
    )
    return llm, resolved_model_id


async def _create_llm_with_api_key(
    provider_name: str,
    model_id: Optional[str],
    api_key: str,
) -> tuple[BaseChatModel, str]:
    """
    Create LLM instance with specific API key (for multi-key failover).

    This function is NOT cached and should be used when multi-key fallback is enabled.

    Args:
        provider_name: Provider name
        model_id: Model ID (None for default)
        api_key: API key to use

    Returns:
        Tuple of (LLM instance, resolved model ID)
    """
    # Temporarily set the API key in environment for the provider
    old_key = _set_provider_api_key(provider_name, api_key)

    try:
        factory_provider = ModelProviderFactory.get_provider(provider_name)
        resolved_model_id = model_id

        if not resolved_model_id:
            if provider_name == "ollama" and getattr(settings, "ollama_default_model", None):
                resolved_model_id = settings.ollama_default_model
            else:
                models = factory_provider.list_models()
                if not models:
                    raise RuntimeError(f"No models available for provider '{provider_name}'")
                resolved_model_id = models[0].id

        # Add Sentry breadcrumb for LLM creation (Task #56)
        try:
            from api.sentry_init import add_llm_breadcrumb

            add_llm_breadcrumb(provider=provider_name, model=resolved_model_id)
        except Exception as e:
            logger.debug("Sentry breadcrumb skipped: %s", e)

        llm = factory_provider.create_model(
            model_id=resolved_model_id,
            temperature=settings.default_temperature,
            max_tokens=settings.default_max_tokens,
        )
        return llm, resolved_model_id

    finally:
        # Restore original API key
        _restore_provider_api_key(provider_name, old_key)


def _set_provider_api_key(provider: str, api_key: str) -> Optional[str]:
    """
    Set provider API key in environment and return old value.

    Note: Mutates os.environ, safe only because create_model() is synchronous
    (no await between set/restore). For multi-worker deployments, each worker
    has its own os.environ so no cross-contamination.
    """
    env_var = PROVIDER_ENV_VAR_MAP.get(provider)
    if not env_var:
        return None

    old_key = os.environ.get(env_var)
    os.environ[env_var] = api_key
    return old_key


def _restore_provider_api_key(provider: str, old_key: Optional[str]) -> None:
    """Restore provider API key to previous value."""
    env_var = PROVIDER_ENV_VAR_MAP.get(provider)
    if not env_var:
        return

    if old_key is None:
        os.environ.pop(env_var, None)
    else:
        os.environ[env_var] = old_key


async def _create_llm_with_multi_key_fallback(
    providers: list[str],
    primary_model: Optional[str],
) -> BaseChatModel:
    """
    Create LLM with automatic multi-key and multi-provider fallback.

    Uses CircuitBreakerManager to:
    1. Try each provider in order
    2. For each provider, try each API key
    3. Automatically switch on failure
    4. Fall back to Ollama if all cloud providers fail

    Args:
        providers: Ordered list of providers to try
        primary_model: Model ID (None for default)

    Returns:
        LLM instance

    Raises:
        RuntimeError: If all providers and keys fail
    """
    manager = get_circuit_breaker_manager()

    # Build provider keys dict from settings
    provider_keys = settings.provider_api_keys

    # Filter to only include providers that have keys
    available_providers = [p for p in providers if p in provider_keys and provider_keys[p]]

    # Add Ollama as fallback if configured
    try:
        ollama_provider = ModelProviderFactory.get_provider("ollama")
        runtime_ok, _runtime_error = ollama_provider.validate_connection()
        if runtime_ok:
            available_providers.append("ollama")
            # Ollama doesn't use API keys
            provider_keys = {**provider_keys, "ollama": [""]}
    except Exception:
        pass

    if not available_providers:
        raise RuntimeError("No providers with API keys available")

    async def create_llm_with_key(
        provider: str,
        key_index: int,
        api_key: str,
    ) -> BaseChatModel:
        """Helper function to create LLM with specific provider and key."""
        llm, _resolved_model_id = await _create_llm_with_api_key(
            provider_name=provider,
            model_id=primary_model,
            api_key=api_key,
        )
        return llm

    try:
        return await manager.call_with_fallback(
            providers=available_providers,
            provider_keys=provider_keys,
            func=create_llm_with_key,  # type: ignore[arg-type]
        )
    except RuntimeError as e:
        raise RuntimeError(
            f"Failed to create LLM with any provider/key. Tried: {available_providers}"
        ) from e


async def get_llm(
    x_user_email: Annotated[str | None, Header(alias="X-User-Email")] = None,
) -> BaseChatModel:
    """
    Get Language Model instance.
    Uses settings to determine provider and model.
    Supports multi-key and multi-provider fallback when enabled.
    Returns MockLLM when DEMO_MODE is enabled.
    """
    if settings.demo_mode:
        from core.demo import get_demo_llm

        return get_demo_llm()

    default_provider_name = settings.default_provider
    default_model_id = settings.default_model

    preferred_provider: Optional[str] = None
    preferred_model: Optional[str] = None
    if x_user_email and x_user_email.strip():
        try:
            prefs = user_model_preferences.MODEL_PREFS_MANAGER.get_preferences(x_user_email.strip())
            preferred_provider = prefs.preferred_provider
            preferred_model = prefs.preferred_model
        except Exception as e:
            logger.warning("Failed to load model preferences: %s", e)

    primary_provider = preferred_provider or default_provider_name
    primary_model = preferred_model if preferred_provider else (preferred_model or default_model_id)

    # Use multi-key fallback if enabled
    if settings.enable_multi_key_fallback:
        try:
            # Build provider priority list
            providers = settings.provider_priority_order or [
                primary_provider,
                default_provider_name,
            ]
            # Remove duplicates while preserving order
            seen = set()
            unique_providers = []
            for p in providers:
                if p not in seen:
                    seen.add(p)
                    unique_providers.append(p)

            # Ensure default provider is in the list
            if default_provider_name not in seen:
                unique_providers.append(default_provider_name)

            return await _create_llm_with_multi_key_fallback(unique_providers, primary_model)
        except Exception as e:
            logger.error("Multi-key fallback failed, using legacy fallback: %s", e)
            # Fall through to legacy behavior

    # Legacy fallback behavior (single key per provider)
    try:
        return _create_llm(primary_provider, primary_model)
    except Exception as e:
        if preferred_provider or preferred_model:
            try:
                return _create_llm(default_provider_name, default_model_id)
            except Exception as fallback_err:
                logger.warning("Default provider fallback also failed: %s", fallback_err)
        if primary_provider != "ollama":
            try:
                ollama_provider = ModelProviderFactory.get_provider("ollama")
                runtime_ok, _runtime_error = ollama_provider.validate_connection()
                if runtime_ok:
                    return _create_llm("ollama", settings.ollama_default_model)
            except Exception as ollama_err:
                logger.warning("Ollama fallback failed: %s", ollama_err)
        raise RuntimeError(
            f"Could not initialize LLM with provider '{primary_provider}': {e}"
        ) from e


async def get_optional_llm(
    x_user_email: Annotated[str | None, Header(alias="X-User-Email")] = None,
) -> Optional[BaseChatModel]:
    try:
        return await get_llm(x_user_email=x_user_email)
    except Exception as e:
        logger.warning("LLM unavailable: %s", e)
        return None


def clear_llm_cache() -> None:
    """Clear LLM creation and provider factory caches.

    Useful for testing to ensure fresh state between tests.
    Clears both the LLM function cache and the ModelProviderFactory cache.
    """
    _create_llm_with_resolved_model_id.cache_clear()
    ModelProviderFactory.clear_cache()


def clear_vector_store_cache() -> None:
    """Clear vector store cache.

    Useful for testing to ensure fresh state between tests.
    Prevents lru_cache pollution when tests run in parallel.
    """
    get_vector_store.cache_clear()


def clear_knowledge_store_cache() -> None:
    """Clear knowledge store cache.

    Useful for testing to ensure fresh state between tests.
    """
    get_knowledge_store.cache_clear()


# =============================================================================
# Task-Specific Model Preferences (Task #87)
# =============================================================================


async def get_llm_for_task(
    task_type: str,
    x_user_email: str | None = None,
    session: AsyncSession | None = None,
) -> BaseChatModel:
    """
    Get Language Model instance configured for a specific task type.

    Priority order:
    1. Demo mode (returns MockLLM if DEMO_MODE=true)
    2. User's task-specific preference (from DB via ModelPreferenceService)
    3. User's global preference (from legacy UserModelPreferencesManager)
    4. System default for task type
    5. Settings default
    6. Fallback to Ollama

    Args:
        task_type: Task type (chat, search, tools, analysis, embedding)
        x_user_email: User email for preference lookup
        session: Database session for preference queries

    Returns:
        Configured LLM instance
    """
    if settings.demo_mode:
        from core.demo import get_demo_llm

        return get_demo_llm()

    primary_provider: Optional[str] = None
    primary_model: Optional[str] = None

    # 1. Try task-specific preference from database
    if x_user_email and x_user_email.strip() and session:
        try:
            user_query = select(User.id).where(User.email == x_user_email.strip())
            user_result = await session.execute(user_query)
            user_id = user_result.scalar_one_or_none()

            if user_id:
                service = ModelPreferenceService(session)
                preference = await service.get_preference_by_task(user_id, task_type)
                if preference and preference.is_active:
                    primary_provider = preference.provider
                    primary_model = preference.model_name
                    logger.debug(
                        "Using task-specific preference for %s: %s/%s",
                        task_type,
                        primary_provider,
                        primary_model,
                    )
        except Exception as e:
            logger.warning("Failed to load task-specific model preferences: %s", e)

    # 2. Fall back to legacy global preferences
    if not primary_provider and x_user_email and x_user_email.strip():
        try:
            prefs = user_model_preferences.MODEL_PREFS_MANAGER.get_preferences(x_user_email.strip())
            if prefs.preferred_provider:
                primary_provider = prefs.preferred_provider
                primary_model = prefs.preferred_model
                logger.debug(
                    "Using global preference for %s: %s/%s",
                    task_type,
                    primary_provider,
                    primary_model,
                )
        except Exception as e:
            logger.warning("Failed to load legacy model preferences: %s", e)

    # 3. Fall back to system default for task type
    if not primary_provider:
        task_default = SYSTEM_DEFAULTS.get(task_type)
        if task_default:
            primary_provider = task_default["provider"]
            primary_model = task_default["model_name"]
            logger.debug(
                "Using system default for %s: %s/%s",
                task_type,
                primary_provider,
                primary_model,
            )

    # 4. Final fallback to settings default
    if not primary_provider:
        primary_provider = settings.default_provider
        primary_model = settings.default_model

    try:
        return _create_llm(primary_provider, primary_model)
    except Exception as e:
        # Try settings default if we had a preference
        if primary_provider != settings.default_provider:
            try:
                return _create_llm(settings.default_provider, settings.default_model)
            except Exception as fallback_err:
                logger.warning(
                    "Default provider fallback for task %s failed: %s", task_type, fallback_err
                )

        # 5. Fallback to Ollama if configured
        if primary_provider != "ollama":
            try:
                ollama_provider = ModelProviderFactory.get_provider("ollama")
                runtime_ok, _runtime_error = ollama_provider.validate_connection()
                if runtime_ok:
                    logger.info("Falling back to Ollama for task %s", task_type)
                    return _create_llm("ollama", settings.ollama_default_model)
            except Exception as ollama_err:
                logger.warning("Ollama fallback for task %s failed: %s", task_type, ollama_err)

        raise RuntimeError(
            f"Could not initialize LLM for task '{task_type}' with provider '{primary_provider}': {e}"
        ) from e


async def get_optional_llm_for_task(
    task_type: str,
    x_user_email: str | None = None,
    session: AsyncSession | None = None,
) -> Optional[BaseChatModel]:
    """Get LLM for task, returning None if unavailable."""
    try:
        return await get_llm_for_task(task_type, x_user_email, session)
    except Exception as e:
        logger.warning("LLM unavailable for task %s: %s", task_type, e)
        return None


def get_optional_llm_with_details(
    *,
    x_user_email: str | None,
    provider_override: str | None,
    model_override: str | None,
) -> tuple[Optional[BaseChatModel], Optional[str], Optional[str]]:
    if settings.demo_mode:
        from core.demo import get_demo_llm

        return get_demo_llm(), "demo", "mock"

    default_provider_name = settings.default_provider
    default_model_id = settings.default_model

    preferred_provider: Optional[str] = None
    preferred_model: Optional[str] = None
    if x_user_email and x_user_email.strip():
        try:
            prefs = user_model_preferences.MODEL_PREFS_MANAGER.get_preferences(x_user_email.strip())
            preferred_provider = prefs.preferred_provider
            preferred_model = prefs.preferred_model
        except Exception as e:
            logger.warning("Failed to load model preferences: %s", e)

    has_overrides = bool(
        (provider_override and provider_override.strip())
        or (model_override and model_override.strip())
    )

    if provider_override and provider_override.strip():
        primary_provider = provider_override.strip()
        primary_model = (
            model_override.strip() if model_override and model_override.strip() else None
        )
    elif model_override and model_override.strip():
        primary_provider = preferred_provider or default_provider_name
        primary_model = model_override.strip()
    else:
        primary_provider = preferred_provider or default_provider_name
        primary_model = (
            preferred_model if preferred_provider else (preferred_model or default_model_id)
        )

    try:
        llm, resolved_model_id = _create_llm_with_resolved_model_id(primary_provider, primary_model)
        return llm, primary_provider, resolved_model_id
    except Exception as e:
        if has_overrides:
            logger.warning(
                "LLM unavailable for explicit selection (provider=%s, model=%s): %s",
                primary_provider,
                primary_model,
                e,
            )
            return None, primary_provider, primary_model

        if preferred_provider or preferred_model:
            try:
                llm, resolved_model_id = _create_llm_with_resolved_model_id(
                    default_provider_name,
                    default_model_id,
                )
                return llm, default_provider_name, resolved_model_id
            except Exception as fallback_err:
                logger.warning("Default provider fallback failed: %s", fallback_err)
        if primary_provider != "ollama":
            try:
                ollama_provider = ModelProviderFactory.get_provider("ollama")
                runtime_ok, _runtime_error = ollama_provider.validate_connection()
                if runtime_ok:
                    llm, resolved_model_id = _create_llm_with_resolved_model_id(
                        "ollama",
                        settings.ollama_default_model,
                    )
                    return llm, "ollama", resolved_model_id
            except Exception as ollama_err:
                logger.warning("Ollama fallback failed: %s", ollama_err)

        logger.warning("LLM unavailable: %s", e)
        return None, primary_provider, primary_model


def parse_rag_qa_request(
    payload: Annotated[Optional[RagQaRequest], Body()] = None,
    question: Annotated[Optional[str], Query()] = None,
    top_k: Annotated[int, Query(ge=1, le=50)] = 5,
    provider: Annotated[Optional[str], Query()] = None,
    model: Annotated[Optional[str], Query()] = None,
) -> RagQaRequest:
    if payload is not None:
        return payload

    if question is None or not question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Question must not be empty"
        )

    return RagQaRequest(
        question=question,
        top_k=top_k,
        provider=provider,
        model=model,
    )


def get_rag_qa_llm_details(
    rag_request: Annotated[RagQaRequest, Depends(parse_rag_qa_request)],
    x_user_email: Annotated[str | None, Header(alias="X-User-Email")] = None,
) -> tuple[Optional[BaseChatModel], Optional[str], Optional[str]]:
    return get_optional_llm_with_details(
        x_user_email=x_user_email,
        provider_override=rag_request.provider,
        model_override=rag_request.model,
    )


def get_valuation_provider() -> Optional[ValuationProvider]:
    if settings.valuation_mode != "simple":
        return None
    return SimpleValuationProvider()


def get_crm_connector() -> Optional[CRMConnector]:
    url = settings.crm_webhook_url
    if not url:
        return None
    return WebhookCRMConnector(url)


@lru_cache()
def get_knowledge_store() -> Optional[KnowledgeStore]:
    """
    Get cached knowledge store instance for RAG uploads (CE-safe).
    Returns None if embeddings are not available.
    """
    if KnowledgeStore is None:
        return None
    try:
        store = KnowledgeStore(
            persist_directory=str(settings.chroma_dir),
            collection_name="knowledge",
        )
        return store
    except Exception as e:
        logger.warning("Knowledge store initialization failed: %s", e)
        return None


def get_data_enrichment_service() -> Optional[DataEnrichmentService]:
    if not settings.data_enrichment_enabled:
        return None
    return BasicDataEnrichmentService()


# =============================================================================
# Property Enrichment Dependencies (Task #78)
# =============================================================================

_enrichment_pipeline: Optional[EnrichmentPipeline] = None


def get_enrichment_pipeline() -> Optional[EnrichmentPipeline]:
    """
    Get enrichment pipeline instance.

    Returns None if enrichment is disabled.
    """
    from data.enrichment.pipeline import PipelineConfig
    from data.enrichment.pipeline import get_enrichment_pipeline as _get_impl

    if not settings.enrichment_enabled:
        return None

    config = PipelineConfig(
        enabled=settings.enrichment_enabled,
        parallel_execution=settings.enrichment_parallel_execution,
        max_concurrent=settings.enrichment_max_concurrent,
        default_timeout=settings.enrichment_timeout_seconds,
        cache_enabled=settings.enrichment_cache_enabled,
        fallback_on_error=settings.enrichment_fallback_on_error,
        sources=settings.enrichment_sources if settings.enrichment_sources else None,
    )
    return _get_impl(config)


def get_enrichment_status(property_id: str) -> dict[str, Any]:
    """
    Get enrichment status for a property.

    Args:
        property_id: Property identifier

    Returns:
        Status dictionary
    """
    from data.enrichment.status import get_status_tracker

    return get_status_tracker().get_status(property_id)


def get_legal_check_service() -> Optional[LegalCheckService]:
    if settings.legal_check_mode != "basic":
        return None
    return BasicLegalCheckService()


# =============================================================================
# E-Signature Dependencies
# =============================================================================

_esignature_service: Optional[ESignatureService] = None
_template_service: Optional[TemplateService] = None


def get_esignature_service() -> Optional[ESignatureService]:
    """
    Get e-signature service instance.

    Returns None if not configured.
    """
    from services.esignature_service import get_esignature_service as _get_esignature_service_impl

    return _get_esignature_service_impl()


def get_template_service() -> Optional[TemplateService]:
    """
    Get template service instance.

    Returns None if not configured.
    """
    from services.template_service import get_template_service as _get_template_service_impl

    return _get_template_service_impl()


def get_agent(
    store: Annotated[Optional[ChromaPropertyStore], Depends(get_vector_store)],
    llm: Annotated[BaseChatModel, Depends(get_llm)],
) -> HybridPropertyAgent | SimpleRAGAgent:
    """
    Get initialized Hybrid Agent.
    """
    if not store:
        # If store is missing, we might want a simple agent or raise error
        # For now, let's assume we need the store for the full hybrid agent
        # But we can try to create it with a dummy retriever or fail
        # HybridPropertyAgent needs a retriever.
        raise RuntimeError("Vector Store unavailable, cannot create Hybrid Agent")

    retriever = store.get_retriever()
    return create_hybrid_agent(llm=llm, retriever=retriever)
