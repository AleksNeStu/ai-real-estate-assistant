"""
Anthropic (Claude) model provider implementation.

Supports Claude 3.5 Sonnet, Claude 3 Opus, and other Anthropic models.
"""

import os
from typing import Any, List, Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from pydantic import SecretStr

from .base import (
    ModelCapability,
    ModelInfo,
    PricingInfo,
    RemoteModelProvider,
)


class AnthropicProvider(RemoteModelProvider):
    """Anthropic (Claude) model provider."""

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def display_name(self) -> str:
        return "Anthropic (Claude)"

    def __init__(self, config: Optional[dict[str, Any]] = None):
        super().__init__(config)
        # Get API key from config, environment, or None
        if "api_key" not in self.config:
            self.config["api_key"] = os.getenv("ANTHROPIC_API_KEY")

    def list_models(self) -> List[ModelInfo]:
        """List available Anthropic models."""
        return [
            # Latest Models (2025)
            ModelInfo(
                id="claude-sonnet-4-5-20250929",
                display_name="Claude Sonnet 4.5 (Latest)",
                provider_name=self.display_name,
                context_window=200000,
                pricing=PricingInfo(input_price_per_1m=3.00, output_price_per_1m=15.00),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.VISION,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Latest and most advanced Claude model with improved reasoning and coding",
                recommended_for=[
                    "complex reasoning",
                    "code generation",
                    "long documents",
                    "agentic workflows",
                ],
            ),
            # Claude 3.5 Generation
            ModelInfo(
                id="claude-3-5-sonnet-20241022",
                display_name="Claude 3.5 Sonnet",
                provider_name=self.display_name,
                context_window=200000,
                pricing=PricingInfo(input_price_per_1m=3.00, output_price_per_1m=15.00),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.VISION,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Powerful Claude model with extended context - consider Sonnet 4.5 for latest features",
                recommended_for=["complex reasoning", "long documents", "code generation"],
            ),
            ModelInfo(
                id="claude-haiku-4-5-20251001",
                display_name="Claude Haiku 4.5 (Recommended)",
                provider_name=self.display_name,
                context_window=200000,
                pricing=PricingInfo(input_price_per_1m=1.00, output_price_per_1m=5.00),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.VISION,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Fast and cost-effective model for simpler tasks",
                recommended_for=[
                    "quick responses",
                    "high volume",
                    "cost-effective",
                    "general purpose",
                ],
            ),
            # Legacy Models
            ModelInfo(
                id="claude-3-opus-20240229",
                display_name="Claude 3 Opus (Legacy)",
                provider_name=self.display_name,
                context_window=200000,
                pricing=PricingInfo(input_price_per_1m=15.00, output_price_per_1m=75.00),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.VISION,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Previous generation model - consider Claude Sonnet 4.5 for better performance and lower cost",
                recommended_for=["legacy compatibility"],
            ),
        ]

    def create_model(
        self,
        model_id: str,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        streaming: bool = True,
        request_timeout: Optional[float] = None,
        **kwargs: Any,
    ) -> BaseChatModel:
        """Create Anthropic model instance."""
        # Validate model exists
        model_info = self.get_model_info(model_id)
        if not model_info:
            available = [m.id for m in self.list_models()]
            raise ValueError(
                f"Model '{model_id}' not available. Available models: {', '.join(available)}"
            )

        # Validate API key
        api_key = self.get_api_key()
        if not api_key:
            raise RuntimeError(
                "Anthropic API key required. "
                "Set ANTHROPIC_API_KEY environment variable or provide in config."
            )

        # Set default max_tokens if not provided (Anthropic requires this)
        if max_tokens is None:
            max_tokens = 4096

        # Get timeout from config or use default from settings
        timeout = request_timeout
        if timeout is None:
            timeout = self.config.get("request_timeout")
        if timeout is None:
            from config.settings import get_settings

            timeout = get_settings().llm_request_timeout_seconds

        llm = ChatAnthropic(
            temperature=temperature,
            streaming=streaming,
            api_key=SecretStr(api_key),
            default_request_timeout=timeout,  # type: ignore[call-arg]
            **kwargs,
        )
        llm.model = model_id
        llm.max_tokens = max_tokens
        return llm

    def validate_connection(self) -> tuple[bool, Optional[str]]:
        """Validate Anthropic connection."""
        api_key = self.get_api_key()
        if not api_key:
            return False, "API key not provided"

        try:
            # Try to create a minimal model instance
            self.create_model("claude-haiku-4-5-20251001")
            return True, None
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
