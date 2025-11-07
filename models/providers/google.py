"""
Google (Gemini) model provider implementation.

Supports Gemini 1.5 Pro, Gemini 1.5 Flash, and other Google models.
"""

import os
from typing import List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models import BaseChatModel

from .base import (
    RemoteModelProvider,
    ModelInfo,
    ModelCapability,
    PricingInfo,
)


class GoogleProvider(RemoteModelProvider):
    """Google (Gemini) model provider."""

    @property
    def name(self) -> str:
        return "google"

    @property
    def display_name(self) -> str:
        return "Google (Gemini)"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        # Get API key from config, environment, or None
        if "api_key" not in self.config:
            self.config["api_key"] = os.getenv("GOOGLE_API_KEY")

    def list_models(self) -> List[ModelInfo]:
        """List available Google models."""
        return [
            ModelInfo(
                id="gemini-1.5-pro",
                display_name="Gemini 1.5 Pro",
                provider_name=self.display_name,
                context_window=2000000,  # 2M tokens!
                pricing=PricingInfo(
                    input_price_per_1m=1.25,
                    output_price_per_1m=5.00
                ),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.VISION,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Most capable Gemini model with massive 2M token context",
                recommended_for=["long documents", "complex analysis", "multimodal tasks"]
            ),
            ModelInfo(
                id="gemini-1.5-flash",
                display_name="Gemini 1.5 Flash",
                provider_name=self.display_name,
                context_window=1000000,  # 1M tokens
                pricing=PricingInfo(
                    input_price_per_1m=0.075,
                    output_price_per_1m=0.30
                ),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.VISION,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Fast and efficient model with 1M token context",
                recommended_for=["fast responses", "cost-effective", "high volume"]
            ),
            ModelInfo(
                id="gemini-2.0-flash-exp",
                display_name="Gemini 2.0 Flash (Experimental)",
                provider_name=self.display_name,
                context_window=1000000,
                pricing=PricingInfo(
                    input_price_per_1m=0.00,  # Free during preview
                    output_price_per_1m=0.00
                ),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.VISION,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Next-generation experimental model (free during preview)",
                recommended_for=["testing", "experimentation", "free tier"]
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
        """Create Google model instance."""
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
                "Google API key required. "
                "Set GOOGLE_API_KEY environment variable or provide in config."
            )

        # Create model
        return ChatGoogleGenerativeAI(
            model=model_id,
            temperature=temperature,
            max_output_tokens=max_tokens,
            streaming=streaming,
            google_api_key=api_key,
            **kwargs
        )

    def validate_connection(self) -> tuple[bool, Optional[str]]:
        """Validate Google connection."""
        api_key = self.get_api_key()
        if not api_key:
            return False, "API key not provided"

        try:
            # Try to create a minimal model instance
            model = self.create_model("gemini-1.5-flash")
            return True, None
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
