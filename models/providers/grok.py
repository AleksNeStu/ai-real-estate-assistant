"""
Grok (xAI) model provider implementation.

Supports Grok-2 and other xAI models via OpenAI-compatible API.
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


class GrokProvider(RemoteModelProvider):
    """Grok (xAI) model provider using OpenAI-compatible API."""

    @property
    def name(self) -> str:
        return "grok"

    @property
    def display_name(self) -> str:
        return "Grok (xAI)"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        # Get API key from config, environment, or None
        if "api_key" not in self.config:
            self.config["api_key"] = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")

        # Set base URL for xAI API
        if "base_url" not in self.config:
            self.config["base_url"] = "https://api.x.ai/v1"

    def list_models(self) -> List[ModelInfo]:
        """List available Grok models."""
        return [
            ModelInfo(
                id="grok-2-1212",
                display_name="Grok 2 (Latest)",
                provider_name=self.display_name,
                context_window=131072,
                pricing=PricingInfo(
                    input_price_per_1m=2.00,
                    output_price_per_1m=10.00
                ),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Latest Grok 2 model with enhanced reasoning and real-time information",
                recommended_for=["real-time analysis", "current events", "reasoning", "creative tasks"]
            ),
            ModelInfo(
                id="grok-2-vision-1212",
                display_name="Grok 2 Vision",
                provider_name=self.display_name,
                context_window=32768,
                pricing=PricingInfo(
                    input_price_per_1m=2.00,
                    output_price_per_1m=10.00
                ),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.VISION,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Grok 2 with vision capabilities for image analysis",
                recommended_for=["image analysis", "visual reasoning", "multimodal tasks", "document understanding"]
            ),
            ModelInfo(
                id="grok-beta",
                display_name="Grok Beta",
                provider_name=self.display_name,
                context_window=131072,
                pricing=PricingInfo(
                    input_price_per_1m=5.00,
                    output_price_per_1m=15.00
                ),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Experimental Grok model with cutting-edge features",
                recommended_for=["experimental features", "advanced reasoning", "complex analysis"]
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
        """Create Grok model instance using OpenAI-compatible client."""
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
                "Grok API key required. "
                "Set XAI_API_KEY or GROK_API_KEY environment variable or provide in config."
            )

        # Create model using OpenAI-compatible interface
        return ChatOpenAI(
            model=model_id,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=streaming,
            api_key=api_key,
            base_url=self.config.get("base_url", "https://api.x.ai/v1"),
            **kwargs
        )

    def validate_connection(self) -> tuple[bool, Optional[str]]:
        """Validate Grok connection."""
        api_key = self.get_api_key()
        if not api_key:
            return False, "API key not provided"

        try:
            # Try to create a minimal model instance
            model = self.create_model("grok-2-1212")
            # If no error, connection is valid
            return True, None
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
