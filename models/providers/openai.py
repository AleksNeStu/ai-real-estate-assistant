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
            # GPT-4o Series - Latest flagship models
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
                recommended_for=["complex reasoning", "vision tasks", "function calling", "multimodal analysis"]
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
                recommended_for=["general purpose", "cost-effective", "fast responses", "high volume tasks"]
            ),

            # O-Series - Advanced reasoning models
            ModelInfo(
                id="o1",
                display_name="O1",
                provider_name=self.display_name,
                context_window=200000,
                pricing=PricingInfo(
                    input_price_per_1m=15.00,
                    output_price_per_1m=60.00
                ),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Advanced reasoning model for complex problem-solving and deep analysis",
                recommended_for=["complex reasoning", "mathematical problems", "code analysis", "research tasks"]
            ),
            ModelInfo(
                id="o1-mini",
                display_name="O1 Mini",
                provider_name=self.display_name,
                context_window=128000,
                pricing=PricingInfo(
                    input_price_per_1m=3.00,
                    output_price_per_1m=12.00
                ),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Faster reasoning model for STEM tasks and coding",
                recommended_for=["coding", "STEM problems", "math", "fast reasoning"]
            ),
            ModelInfo(
                id="o3-mini",
                display_name="O3 Mini",
                provider_name=self.display_name,
                context_window=200000,
                pricing=PricingInfo(
                    input_price_per_1m=1.10,
                    output_price_per_1m=4.40
                ),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Latest efficient reasoning model with improved performance",
                recommended_for=["balanced reasoning", "cost-effective analysis", "coding tasks", "data analysis"]
            ),

            # GPT-4 Series - Previous generation
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
                recommended_for=["complex analysis", "long documents", "detailed responses"]
            ),
            ModelInfo(
                id="gpt-4",
                display_name="GPT-4",
                provider_name=self.display_name,
                context_window=8192,
                pricing=PricingInfo(
                    input_price_per_1m=30.00,
                    output_price_per_1m=60.00
                ),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Original GPT-4 model with strong performance",
                recommended_for=["high-quality responses", "creative tasks", "detailed analysis"]
            ),

            # GPT-3.5 Series - Budget-friendly
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
                recommended_for=["simple queries", "high volume", "budget-conscious", "chatbots"]
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
