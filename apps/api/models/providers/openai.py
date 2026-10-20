"""
OpenAI model provider implementation.

Supports GPT-4o, GPT-4o-mini, GPT-3.5-turbo and other OpenAI models.
"""

import os
from typing import Any, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from .base import (
    ModelCapability,
    ModelInfo,
    PricingInfo,
    RemoteModelProvider,
)


class OpenAIProvider(RemoteModelProvider):
    """OpenAI model provider."""

    @property
    def name(self) -> str:
        return "openai"

    @property
    def display_name(self) -> str:
        return "OpenAI"

    def __init__(self, config: Optional[dict[str, Any]] = None):
        super().__init__(config)
        # Get API key from config, environment, or None
        if "api_key" not in self.config:
            self.config["api_key"] = os.getenv("OPENAI_API_KEY")

    def list_models(self) -> List[ModelInfo]:
        """List available OpenAI models."""
        return [
            # ── 2026 generation (verified live 2026-10-20) ──────────────
            # Top-line flagship: 1M context, GA. Dateless IDs from 4.6+ gen
            # in Anthropic, OpenAI follows the same pattern.
            ModelInfo(
                id="gpt-6-luna",
                display_name="GPT-6 Luna (1M ctx, cheapest)",
                provider_name=self.display_name,
                context_window=1050000,
                pricing=None,  # populate from openai.com/pricing before quoting
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="GA — cheapest 1M-context model. Strong general-purpose default.",
                recommended_for=["general purpose", "long context", "budget"],
            ),
            ModelInfo(
                id="gpt-6-sol",
                display_name="GPT-6 Sol (1M ctx, flagship mid-tier)",
                provider_name=self.display_name,
                context_window=1050000,
                pricing=None,
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="GA flagship mid-tier. Strong reasoning + coding at sub-flagship cost.",
                recommended_for=["general chat", "reasoning", "coding"],
            ),
            ModelInfo(
                id="gpt-5.6-luna",
                display_name="GPT-5.6 Luna (1M ctx, budget reasoning)",
                provider_name=self.display_name,
                context_window=1050000,
                pricing=None,
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Budget reasoning tier on 5.6 generation. Cheap + 1M ctx.",
                recommended_for=["cost-effective", "high throughput"],
            ),
            # Reasoning (o-series) — current line is o3 / o4-mini
            ModelInfo(
                id="o3",
                display_name="o3 (200K ctx, GA reasoning)",
                provider_name=self.display_name,
                context_window=200000,
                pricing=None,
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="GA reasoning model. Recommended o-series default.",
                recommended_for=["complex reasoning", "math", "research"],
            ),
            ModelInfo(
                id="o4-mini",
                display_name="o4-mini (200K ctx, fast reasoning)",
                provider_name=self.display_name,
                context_window=200000,
                pricing=None,
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Faster reasoning tier; current o-mini recommendation.",
                recommended_for=["coding", "STEM", "fast reasoning"],
            ),
            # ── Pre-existing 2025-2026 entries (kept; some deprecated) ──
            # Per OpenAI deprecations page, gpt-3.5-turbo, gpt-4, gpt-4-turbo,
            # o1, o3-mini ALL shut down 2026-10-23. They remain in this list
            # to preserve per-task preferences already saved by users — but
            # new picks should prefer the 2026 line above. UI flags the
            # recommended tier so users migrate on their own schedule.
            # O3-Series - Latest reasoning models
            ModelInfo(
                id="o3-mini",
                display_name="O3 Mini (Latest)",
                provider_name=self.display_name,
                context_window=200000,
                pricing=PricingInfo(input_price_per_1m=1.10, output_price_per_1m=4.40),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Latest efficient reasoning model with improved performance over o1",
                recommended_for=[
                    "advanced reasoning",
                    "cost-effective analysis",
                    "coding tasks",
                    "data analysis",
                ],
            ),
            # GPT-4o Series - Latest flagship models
            ModelInfo(
                id="gpt-4o",
                display_name="GPT-4o (Latest)",
                provider_name=self.display_name,
                context_window=128000,
                pricing=PricingInfo(input_price_per_1m=2.50, output_price_per_1m=10.00),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.VISION,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Most advanced OpenAI model with vision and function calling",
                recommended_for=[
                    "complex reasoning",
                    "vision tasks",
                    "function calling",
                    "multimodal analysis",
                ],
            ),
            ModelInfo(
                id="gpt-4o-mini",
                display_name="GPT-4o Mini (Recommended)",
                provider_name=self.display_name,
                context_window=128000,
                pricing=PricingInfo(input_price_per_1m=0.15, output_price_per_1m=0.60),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.VISION,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Affordable and intelligent small model for fast tasks",
                recommended_for=[
                    "general purpose",
                    "cost-effective",
                    "fast responses",
                    "high volume tasks",
                ],
            ),
            # O-Series - Advanced reasoning models
            ModelInfo(
                id="o1",
                display_name="O1",
                provider_name=self.display_name,
                context_window=200000,
                pricing=PricingInfo(input_price_per_1m=15.00, output_price_per_1m=60.00),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Advanced reasoning model for complex problem-solving and deep analysis",
                recommended_for=[
                    "complex reasoning",
                    "mathematical problems",
                    "code analysis",
                    "research tasks",
                ],
            ),
            ModelInfo(
                id="o1-mini",
                display_name="O1 Mini",
                provider_name=self.display_name,
                context_window=128000,
                pricing=PricingInfo(input_price_per_1m=3.00, output_price_per_1m=12.00),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Faster reasoning model for STEM tasks and coding",
                recommended_for=["coding", "STEM problems", "math", "fast reasoning"],
            ),
            # Legacy Models (Still supported but older)
            # GPT-4 Series
            ModelInfo(
                id="gpt-4-turbo",
                display_name="GPT-4 Turbo (Legacy)",
                provider_name=self.display_name,
                context_window=128000,
                pricing=PricingInfo(input_price_per_1m=10.00, output_price_per_1m=30.00),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.VISION,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Previous generation high-capability model - consider using GPT-4o instead",
                recommended_for=["legacy compatibility", "long documents"],
            ),
            ModelInfo(
                id="gpt-4",
                display_name="GPT-4 (Legacy)",
                provider_name=self.display_name,
                context_window=8192,
                pricing=PricingInfo(input_price_per_1m=30.00, output_price_per_1m=60.00),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Original GPT-4 model - consider using GPT-4o for better performance",
                recommended_for=["legacy compatibility"],
            ),
            # GPT-3.5 Series - Budget-friendly
            ModelInfo(
                id="gpt-3.5-turbo",
                display_name="GPT-3.5 Turbo (Budget)",
                provider_name=self.display_name,
                context_window=16385,
                pricing=PricingInfo(input_price_per_1m=0.50, output_price_per_1m=1.50),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Fast, efficient model for simpler tasks - consider GPT-4o Mini for better quality",
                recommended_for=["simple queries", "high volume", "budget-conscious", "chatbots"],
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
        """Create OpenAI model instance."""
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
                "OpenAI API key required. "
                "Set OPENAI_API_KEY environment variable or provide in config."
            )

        # Get timeout from config or use default from settings
        timeout = request_timeout
        if timeout is None:
            timeout = self.config.get("request_timeout")
        if timeout is None:
            from config.settings import get_settings

            timeout = get_settings().llm_request_timeout_seconds

        llm = ChatOpenAI(
            model=model_id,
            temperature=temperature,
            streaming=streaming,
            api_key=SecretStr(api_key),
            request_timeout=timeout,  # type: ignore[call-arg]
            **kwargs,
        )
        if max_tokens is not None:
            llm.max_tokens = max_tokens
        return llm

    def validate_connection(self) -> tuple[bool, Optional[str]]:
        """Validate OpenAI connection."""
        api_key = self.get_api_key()
        if not api_key:
            return False, "API key not provided"

        try:
            # `gpt-3.5-turbo` shut down 2026-10-23 per OpenAI's deprecations
            # page. Validate against a current GA model (`gpt-4o-mini`) so a
            # live key returns True at probe time.
            self.create_model("gpt-4o-mini")
            return True, None
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
