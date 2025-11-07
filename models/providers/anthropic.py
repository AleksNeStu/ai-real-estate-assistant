"""
Anthropic (Claude) model provider implementation.

Supports Claude 3.5 Sonnet, Claude 3 Opus, and other Anthropic models.
"""

import os
from typing import List, Optional
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel

from .base import (
    RemoteModelProvider,
    ModelInfo,
    ModelCapability,
    PricingInfo,
)


class AnthropicProvider(RemoteModelProvider):
    """Anthropic (Claude) model provider."""

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def display_name(self) -> str:
        return "Anthropic (Claude)"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        # Get API key from config, environment, or None
        if "api_key" not in self.config:
            self.config["api_key"] = os.getenv("ANTHROPIC_API_KEY")

    def list_models(self) -> List[ModelInfo]:
        """List available Anthropic models."""
        return [
            ModelInfo(
                id="claude-3-5-sonnet-20241022",
                display_name="Claude 3.5 Sonnet",
                provider_name=self.display_name,
                context_window=200000,
                pricing=PricingInfo(
                    input_price_per_1m=3.00,
                    output_price_per_1m=15.00
                ),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.VISION,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Most intelligent Claude model with extended context",
                recommended_for=["complex reasoning", "long documents", "code generation"]
            ),
            ModelInfo(
                id="claude-3-5-haiku-20241022",
                display_name="Claude 3.5 Haiku",
                provider_name=self.display_name,
                context_window=200000,
                pricing=PricingInfo(
                    input_price_per_1m=0.80,
                    output_price_per_1m=4.00
                ),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.VISION,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Fast and cost-effective model for simpler tasks",
                recommended_for=["quick responses", "high volume", "cost-effective"]
            ),
            ModelInfo(
                id="claude-3-opus-20240229",
                display_name="Claude 3 Opus",
                provider_name=self.display_name,
                context_window=200000,
                pricing=PricingInfo(
                    input_price_per_1m=15.00,
                    output_price_per_1m=75.00
                ),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.VISION,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Most powerful Claude model for complex tasks",
                recommended_for=["highest quality", "complex analysis", "research"]
            ),
        ]

    def create_model(
        self,
        model_id: str,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        streaming: bool = True,
        **kwargs
    ) -> BaseChatModel:
        """Create Anthropic model instance."""
        # Validate model exists
        model_info = self.get_model_info(model_id)
        if not model_info:
            available = [m.id for m in self.list_models()]
            raise ValueError(
                f"Model '{model_id}' not available. "
                f"Available models: {', '.join(available)}"
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

        # Create model
        return ChatAnthropic(
            model=model_id,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=streaming,
            api_key=api_key,
            **kwargs
        )

    def validate_connection(self) -> tuple[bool, Optional[str]]:
        """Validate Anthropic connection."""
        api_key = self.get_api_key()
        if not api_key:
            return False, "API key not provided"

        try:
            # Try to create a minimal model instance
            model = self.create_model("claude-3-5-haiku-20241022")
            return True, None
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
