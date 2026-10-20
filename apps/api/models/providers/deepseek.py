"""
DeepSeek model provider implementation.

Supports DeepSeek-V3 and other DeepSeek models via OpenAI-compatible API.
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


class DeepSeekProvider(RemoteModelProvider):
    """DeepSeek model provider using OpenAI-compatible API."""

    @property
    def name(self) -> str:
        return "deepseek"

    @property
    def display_name(self) -> str:
        return "DeepSeek"

    def __init__(self, config: Optional[dict[str, Any]] = None):
        super().__init__(config)
        # Get API key from config, environment, or None
        if "api_key" not in self.config:
            self.config["api_key"] = os.getenv("DEEPSEEK_API_KEY")

        # Set base URL for DeepSeek API
        if "base_url" not in self.config:
            self.config["base_url"] = "https://api.deepseek.com"

    def list_models(self) -> List[ModelInfo]:
        """List available DeepSeek models."""
        return [
            # ── 2026 V4 line (verified live 2026-10-20) ─────────────────
            # Per DeepSeek changelog, deepseek-chat and deepseek-reasoner were
            # DEPRECATED 2026-07-24 15:59 UTC. The V4.1-flash and V4-pro are
            # the current GA. Peak/off-peak pricing (split effective
            # 2026-08-16) omitted below — populate via api-docs.deepseek.com
            # before quoting per-token numbers in the UI.
            ModelInfo(
                id="deepseek-flash",
                display_name="DeepSeek V4.1 Flash (1M ctx, multimodal)",
                provider_name=self.display_name,
                context_window=1000000,
                pricing=None,
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.VISION,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="GA — V4.1 launched 2026-10-17. First Flash-tier model with native visual understanding. Replaces deepseek-chat + deepseek-reasoner for new picks.",
                recommended_for=["general chat", "cost-effective", "vision"],
            ),
            ModelInfo(
                id="deepseek-v4-pro",
                display_name="DeepSeek V4 Pro (1M ctx, top reasoning)",
                provider_name=self.display_name,
                context_window=1000000,
                pricing=None,
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="GA — top-tier reasoning. Strong chain-of-thought, function calling confirmed.",
                recommended_for=["complex reasoning", "math", "coding", "research"],
            ),
            # ── Pre-existing 2025-era entries (kept; all deprecated) ────
            # deepseek-chat and deepseek-reasoner were the 2025 line and
            # both DEPRECATED 2026-07-24. deepseek-coder is unverified on
            # the current docs. They remain here to preserve per-task
            # preferences already saved by users; new picks should prefer
            # the V4 line above.
            ModelInfo(
                id="deepseek-reasoner",
                display_name="DeepSeek R1 (DEPRECATED 2026-07-24)",
                provider_name=self.display_name,
                context_window=64000,
                pricing=PricingInfo(input_price_per_1m=0.55, output_price_per_1m=2.19),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="RETIRED 2026-07-24 15:59 UTC (per DeepSeek changelog). During the 3-month overlap it pointed to thinking mode of deepseek-v4-flash. Kept to preserve saved user preferences.",
                recommended_for=["legacy compatibility"],
            ),
            ModelInfo(
                id="deepseek-chat",
                display_name="DeepSeek V3 Chat (DEPRECATED 2026-07-24)",
                provider_name=self.display_name,
                context_window=64000,
                pricing=PricingInfo(input_price_per_1m=0.14, output_price_per_1m=0.28),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="RETIRED 2026-07-24 15:59 UTC. During the 3-month overlap it pointed to non-thinking mode of deepseek-v4-flash. Kept to preserve saved user preferences.",
                recommended_for=["legacy compatibility"],
            ),
            ModelInfo(
                id="deepseek-coder",
                display_name="DeepSeek Coder (UNVERIFIED — treat as deprecated)",
                provider_name=self.display_name,
                context_window=64000,
                pricing=PricingInfo(input_price_per_1m=0.14, output_price_per_1m=0.28),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Not mentioned in DeepSeek's current docs — treat as deprecated. Kept to preserve saved user preferences.",
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
        """Create DeepSeek model instance using OpenAI-compatible client."""
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
                "DeepSeek API key required. "
                "Set DEEPSEEK_API_KEY environment variable or provide in config."
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
            base_url=self.config.get("base_url", "https://api.deepseek.com"),
            request_timeout=timeout,  # type: ignore[call-arg]
            **kwargs,
        )
        if max_tokens is not None:
            llm.max_tokens = max_tokens
        return llm

    def validate_connection(self) -> tuple[bool, Optional[str]]:
        """Validate DeepSeek connection."""
        api_key = self.get_api_key()
        if not api_key:
            return False, "API key not provided"

        try:
            # `deepseek-chat` was deprecated 2026-07-24. Validate against
            # the current GA model.
            self.create_model("deepseek-flash")
            return True, None
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
