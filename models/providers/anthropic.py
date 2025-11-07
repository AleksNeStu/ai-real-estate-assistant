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
            # Latest Models (2025)
            ModelInfo(
                id="claude-sonnet-4-5-20250929",
                display_name="Claude Sonnet 4.5 (Latest)",
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
                description="Latest and most advanced Claude model with improved reasoning and coding",
                recommended_for=["complex reasoning", "code generation", "long documents", "agentic workflows"]
            ),

            # Claude 3.5 Generation
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
                description="Powerful Claude model with extended context - consider Sonnet 4.5 for latest features",
                recommended_for=["complex reasoning", "long documents", "code generation"]
            ),
            ModelInfo(
                id="claude-3-5-haiku-20241022",
                display_name="Claude 3.5 Haiku (Recommended)",
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
                recommended_for=["quick responses", "high volume", "cost-effective", "general purpose"]
            ),

            # Legacy Models
            ModelInfo(
                id="claude-3-opus-20240229",
                display_name="Claude 3 Opus (Legacy)",
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
                description="Previous generation model - consider Claude Sonnet 4.5 for better performance and lower cost",
                recommended_for=["legacy compatibility"]
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
