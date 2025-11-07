"""
Base classes for model providers.

This module defines the abstract base classes for implementing different
LLM providers (OpenAI, Anthropic, Google, Ollama, etc.).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, List
from langchain_core.language_models import BaseChatModel


class ModelCapability(str, Enum):
    """Enumeration of model capabilities."""
    STREAMING = "streaming"
    FUNCTION_CALLING = "function_calling"
    VISION = "vision"
    JSON_MODE = "json_mode"
    SYSTEM_MESSAGES = "system_messages"


@dataclass
class PricingInfo:
    """Pricing information for a model."""
    input_price_per_1m: float  # Price per 1M input tokens
    output_price_per_1m: float  # Price per 1M output tokens
    currency: str = "USD"

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Estimate cost for given token usage.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in the specified currency
        """
        input_cost = (input_tokens / 1_000_000) * self.input_price_per_1m
        output_cost = (output_tokens / 1_000_000) * self.output_price_per_1m
        return round(input_cost + output_cost, 6)


@dataclass
class ModelInfo:
    """Information about a specific model."""
    id: str
    display_name: str
    provider_name: str
    context_window: int
    pricing: Optional[PricingInfo] = None
    capabilities: List[ModelCapability] = None
    description: Optional[str] = None
    recommended_for: List[str] = None

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []
        if self.recommended_for is None:
            self.recommended_for = []

    def has_capability(self, capability: ModelCapability) -> bool:
        """Check if model has a specific capability."""
        return capability in self.capabilities

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "display_name": self.display_name,
            "provider": self.provider_name,
            "context_window": self.context_window,
            "capabilities": [c.value for c in self.capabilities],
            "pricing": {
                "input": self.pricing.input_price_per_1m if self.pricing else None,
                "output": self.pricing.output_price_per_1m if self.pricing else None,
            } if self.pricing else None,
            "description": self.description,
            "recommended_for": self.recommended_for,
        }


class ModelProvider(ABC):
    """
    Abstract base class for model providers.

    Each provider implementation must implement methods to:
    - List available models
    - Create configured model instances
    - Validate API keys/credentials
    - Provide provider-specific configuration
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize provider with optional configuration.

        Args:
            config: Provider-specific configuration dictionary
        """
        self.config = config or {}

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'openai', 'anthropic')."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable provider name (e.g., 'OpenAI', 'Anthropic')."""
        pass

    @property
    @abstractmethod
    def requires_api_key(self) -> bool:
        """Whether this provider requires an API key."""
        pass

    @property
    def is_local(self) -> bool:
        """Whether this provider runs locally."""
        return False

    @abstractmethod
    def list_models(self) -> List[ModelInfo]:
        """
        List all available models from this provider.

        Returns:
            List of ModelInfo objects describing available models
        """
        pass

    @abstractmethod
    def create_model(
        self,
        model_id: str,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        streaming: bool = True,
        **kwargs
    ) -> BaseChatModel:
        """
        Create a configured model instance.

        Args:
            model_id: Model identifier
            temperature: Temperature for generation (0.0 - 2.0)
            max_tokens: Maximum tokens to generate
            streaming: Whether to enable streaming
            **kwargs: Additional model-specific parameters

        Returns:
            Configured LangChain chat model instance

        Raises:
            ValueError: If model_id is not available
            RuntimeError: If API key is required but not provided
        """
        pass

    def validate_connection(self) -> tuple[bool, Optional[str]]:
        """
        Validate provider connection and credentials.

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Try to list models as a connection test
            models = self.list_models()
            if models:
                return True, None
            return False, "No models available"
        except Exception as e:
            return False, str(e)

    def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """
        Get information about a specific model.

        Args:
            model_id: Model identifier

        Returns:
            ModelInfo if model exists, None otherwise
        """
        models = self.list_models()
        for model in models:
            if model.id == model_id:
                return model
        return None

    def estimate_cost(
        self,
        model_id: str,
        input_tokens: int,
        output_tokens: int
    ) -> Optional[float]:
        """
        Estimate cost for using a specific model.

        Args:
            model_id: Model identifier
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost or None if pricing unavailable
        """
        model_info = self.get_model_info(model_id)
        if model_info and model_info.pricing:
            return model_info.pricing.estimate_cost(input_tokens, output_tokens)
        return None

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.display_name}>"


class LocalModelProvider(ModelProvider):
    """
    Base class for local model providers (Ollama, LM Studio, etc.).

    Local providers don't require API keys and run on the user's machine.
    """

    @property
    def requires_api_key(self) -> bool:
        return False

    @property
    def is_local(self) -> bool:
        return True


class RemoteModelProvider(ModelProvider):
    """
    Base class for remote/cloud model providers (OpenAI, Anthropic, etc.).

    Remote providers typically require API keys and charge per token.
    """

    @property
    def requires_api_key(self) -> bool:
        return True

    @property
    def is_local(self) -> bool:
        return False

    def get_api_key(self) -> Optional[str]:
        """
        Get API key from configuration or environment.

        Returns:
            API key if available, None otherwise
        """
        return self.config.get("api_key")

    def validate_api_key(self) -> bool:
        """
        Validate that API key is provided.

        Returns:
            True if API key is available and valid
        """
        api_key = self.get_api_key()
        return api_key is not None and len(api_key) > 0
