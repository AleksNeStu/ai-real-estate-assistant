"""
Google (Gemini) model provider implementation.

Supports Gemini 1.5 Pro, Gemini 1.5 Flash, and other Google models.
"""

import os
from typing import Any, Dict, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import SecretStr

from .base import (
    ModelCapability,
    ModelInfo,
    PricingInfo,
    RemoteModelProvider,
)


class GoogleProvider(RemoteModelProvider):
    """Google (Gemini) model provider."""

    @property
    def name(self) -> str:
        return "google"

    @property
    def display_name(self) -> str:
        return "Google (Gemini)"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        # Get API key from config, environment, or None
        if "api_key" not in self.config:
            self.config["api_key"] = os.getenv("GOOGLE_API_KEY")

    def list_models(self) -> List[ModelInfo]:
        """List available Google models."""
        return [
            # ── 2026 generation (verified live 2026-10-20) ──────────────
            # Per Google deprecations page, gemini-2.0-flash shut down
            # 2026-06-01 and gemini-1.5-pro/flash are not on the current
            # deprecations window (treated as retired). The 2.5 family is
            # access-restricted (grandfathered only). The 3.x and 4-argon
            # lines are the path for new project onboarding.
            ModelInfo(
                id="gemini-4-argon",
                display_name="Gemini 4 Argon (1M ctx, top flagship)",
                provider_name=self.display_name,
                context_window=1048576,
                pricing=None,  # populate from ai.google.dev/pricing
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.VISION,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="GA — new top flagship. Long-decode, vision, audio.",
                recommended_for=["complex reasoning", "long context", "multimodal"],
            ),
            ModelInfo(
                id="gemini-3.8-flash",
                display_name="Gemini 3.8 Flash (1M ctx, fast)",
                provider_name=self.display_name,
                context_window=1048576,
                pricing=None,
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.VISION,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="GA — Flash tier on 3.8 generation. Fast + cheap. (Audio via gemini-3.8-live.)",
                recommended_for=["speed", "cost-effective", "high volume"],
            ),
            ModelInfo(
                id="gemini-3.6-flash",
                display_name="Gemini 3.6 Flash (1M ctx, stable)",
                provider_name=self.display_name,
                context_window=1048576,
                pricing=None,
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.VISION,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="GA — predecessor to 3.8-flash. Still on the new project path.",
                recommended_for=["fast responses", "general purpose"],
            ),
            # ── Pre-existing 2025-era entries (kept; some retired) ──────
            # gemini-1.5-pro/flash are off the deprecations window (retired
            # earlier) and gemini-2.0-flash(-exp) shut down 2026-06-01. They
            # remain in this list to preserve per-task preferences already
            # saved by users — but new picks should prefer the 2026 line above.
            ModelInfo(
                id="gemini-2.0-flash-exp",
                display_name="Gemini 2.0 Flash (shut down 2026-06-01)",
                provider_name=self.display_name,
                context_window=1000000,
                pricing=PricingInfo(
                    input_price_per_1m=0.075,  # Pricing when GA
                    output_price_per_1m=0.30,
                ),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.VISION,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="RETIRED on Google's deprecations page (shut down 2026-06-01). Kept here to avoid breaking saved user preferences; new picks should use Gemini 3.8/3.6 Flash or 4 Argon above.",
                recommended_for=["legacy compatibility"],
            ),
            ModelInfo(
                id="gemini-1.5-pro",
                display_name="Gemini 1.5 Pro (Recommended — legacy)",
                provider_name=self.display_name,
                context_window=2000000,  # 2M tokens!
                pricing=PricingInfo(input_price_per_1m=1.25, output_price_per_1m=5.00),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.VISION,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Off Google's current deprecations window (retired earlier). Massive 2M-token context. Kept to preserve saved user preferences.",
                recommended_for=[
                    "long documents",
                    "complex analysis",
                    "multimodal tasks",
                    "large contexts",
                ],
            ),
            ModelInfo(
                id="gemini-1.5-flash",
                display_name="Gemini 1.5 Flash (legacy)",
                provider_name=self.display_name,
                context_window=1000000,
                pricing=PricingInfo(input_price_per_1m=0.075, output_price_per_1m=0.30),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.VISION,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Off Google's current deprecations window. 1M-token context, fast + cheap. Kept to preserve saved user preferences.",
                recommended_for=[
                    "fast responses",
                    "cost-effective",
                    "high volume",
                    "balanced performance",
                ],
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
        """Create Google model instance."""
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
                "Google API key required. "
                "Set GOOGLE_API_KEY environment variable or provide in config."
            )

        # Get timeout from config or use default from settings
        timeout = request_timeout
        if timeout is None:
            timeout = self.config.get("request_timeout")
        if timeout is None:
            from config.settings import get_settings

            timeout = get_settings().llm_request_timeout_seconds

        # Create model with timeout
        return ChatGoogleGenerativeAI(
            model=model_id,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=SecretStr(api_key),
            timeout=timeout,
            **kwargs,
        )

    def validate_connection(self) -> tuple[bool, Optional[str]]:
        """Validate Google connection."""
        api_key = self.get_api_key()
        if not api_key:
            return False, "API key not provided"

        try:
            # gemini-1.5-flash is off Google's current deprecations window.
            # Validate against a current GA model.
            self.create_model("gemini-3.8-flash")
            return True, None
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
