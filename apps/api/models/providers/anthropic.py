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
            # ── 2026 generation (verified live 2026-10-20) ──────────────
            # Dateless IDs from the 4.6 generation on. Opus 5.5 is INTENTIONALLY
            # OMITTED: Anthropic's deprecations page says 4.7+ rejects any
            # non-default `temperature` (only default `1.0` accepted), and our
            # `create_model` always sends `temperature=0.0`. Lifting that
            # requires a call-site decision tracked as Phase D.2 follow-up.
            ModelInfo(
                id="claude-sonnet-5-5",
                display_name="Claude Sonnet 5.5 (1M ctx, recommended)",
                provider_name=self.display_name,
                context_window=1000000,
                pricing=None,  # populate from platform.claude.com/docs/en/about-claude/pricing
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.VISION,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="GA — current Sonnet line, 1M context, dateless ID. Replaces sonnet-4-5 for new picks.",
                recommended_for=[
                    "complex reasoning",
                    "code generation",
                    "long documents",
                    "agentic workflows",
                ],
            ),
            ModelInfo(
                id="claude-haiku-5-5",
                display_name="Claude Haiku 5.5 (1M ctx, fastest)",
                provider_name=self.display_name,
                context_window=1000000,
                pricing=None,
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="GA — current Haiku line, 1M context, dateless ID. Two-tier input pricing (≤100K prompt vs >100K prompt). Replaces haiku-4-5 for new picks.",
                recommended_for=[
                    "fast responses",
                    "high throughput",
                    "cost-effective",
                ],
            ),
            # ── Pre-existing 4.5 / 3.5 / 3 Opus entries (kept) ────────────
            # claude-sonnet-4-5 is DEPRECATED — retires 2026-11-30.
            # claude-3-5-sonnet and claude-3-opus were retired 2025-10-28 and
            # 2026-01-05 respectively. They remain here to preserve
            # per-task preferences already saved by users — new picks
            # should use the 5.5 line above.
            ModelInfo(
                id="claude-sonnet-4-5-20250929",
                display_name="Claude Sonnet 4.5 (DEPRECATED — retires 2026-11-30)",
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
                description="DEPRECATED — retires 2026-11-30. Pre-5.5 Sonnet. Kept to preserve saved user preferences.",
                recommended_for=["legacy compatibility"],
            ),
            ModelInfo(
                id="claude-3-5-sonnet-20241022",
                display_name="Claude 3.5 Sonnet (RETIRED 2025-10-28)",
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
                description="RETIRED on Anthropic's deprecations page (2025-10-28). Kept to preserve saved user preferences; new picks should use Sonnet 5.5 above.",
                recommended_for=["legacy compatibility"],
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
