"""
OpenAI model provider implementation.

Supports GPT-4o, GPT-4o-mini, GPT-3.5-turbo and other OpenAI models.
"""

import os
from typing import List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel

from .base import (
    RemoteModelProvider,
    ModelInfo,
    ModelCapability,
    PricingInfo,
)


class OpenAIProvider(RemoteModelProvider):
    """OpenAI model provider."""

    @property
    def name(self) -> str:
        return "openai"

    @property
    def display_name(self) -> str:
        return "OpenAI"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        # Get API key from config, environment, or None
        if "api_key" not in self.config:
            self.config["api_key"] = os.getenv("OPENAI_API_KEY")

    def list_models(self) -> List[ModelInfo]:
        """List available OpenAI models."""
        return [
            ModelInfo(
                id="gpt-4o",
                display_name="GPT-4o",
                provider_name=self.display_name,
                context_window=128000,
                pricing=PricingInfo(
                    input_price_per_1m=2.50,
                    output_price_per_1m=10.00
                ),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.VISION,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Most advanced OpenAI model with vision and function calling",
                recommended_for=["complex reasoning", "vision tasks", "function calling"]
            ),
            ModelInfo(
                id="gpt-4o-mini",
                display_name="GPT-4o Mini",
                provider_name=self.display_name,
                context_window=128000,
                pricing=PricingInfo(
                    input_price_per_1m=0.15,
                    output_price_per_1m=0.60
                ),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.VISION,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Affordable and intelligent small model for fast tasks",
                recommended_for=["general purpose", "cost-effective", "fast responses"]
            ),
            ModelInfo(
                id="gpt-3.5-turbo",
                display_name="GPT-3.5 Turbo",
                provider_name=self.display_name,
                context_window=16385,
                pricing=PricingInfo(
                    input_price_per_1m=0.50,
                    output_price_per_1m=1.50
                ),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Fast, efficient model for simpler tasks",
                recommended_for=["simple queries", "high volume", "budget-conscious"]
            ),
            ModelInfo(
                id="gpt-4-turbo",
                display_name="GPT-4 Turbo",
                provider_name=self.display_name,
                context_window=128000,
                pricing=PricingInfo(
                    input_price_per_1m=10.00,
                    output_price_per_1m=30.00
                ),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.VISION,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Previous generation high-capability model",
                recommended_for=["complex analysis", "long documents"]
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
        """Create OpenAI model instance."""
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
                "OpenAI API key required. "
                "Set OPENAI_API_KEY environment variable or provide in config."
            )

        # Create model
        return ChatOpenAI(
            model=model_id,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=streaming,
            api_key=api_key,
            **kwargs
        )

    def validate_connection(self) -> tuple[bool, Optional[str]]:
        """Validate OpenAI connection."""
        api_key = self.get_api_key()
        if not api_key:
            return False, "API key not provided"

        try:
            # Try to create a minimal model instance
            model = self.create_model("gpt-3.5-turbo")
            # If no error, connection is valid
            return True, None
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
