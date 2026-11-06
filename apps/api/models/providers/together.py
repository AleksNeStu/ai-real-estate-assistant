"""
Together AI model provider implementation.

Supports the Together AI hosted-inference API (OpenAI-compatible) for
200+ open-source models (Llama, Qwen, DeepSeek, Mistral, etc.).

Stargazer hook: breadth of open-source model coverage at sub-$1/M token
price points; one API key unlocks the entire open-source ecosystem.

Reference docs (live-verified 2026-10-20):
- https://docs.together.ai/docs/openai-api-compatibility
- https://api.together.xyz/v1/models
"""

import os
from typing import Any, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from .base import (
    ModelCapability,
    ModelInfo,
    RemoteModelProvider,
)

TOGETHER_BASE_URL = "https://api.together.xyz/v1"


class TogetherProvider(RemoteModelProvider):
    """Together AI model provider using the OpenAI-compatible API."""

    @property
    def name(self) -> str:
        return "together"

    @property
    def display_name(self) -> str:
        return "Together AI"

    def __init__(self, config: Optional[dict[str, Any]] = None):
        super().__init__(config)
        if "api_key" not in self.config:
            self.config["api_key"] = os.getenv("TOGETHER_API_KEY")
        if "base_url" not in self.config:
            self.config["base_url"] = TOGETHER_BASE_URL

    def list_models(self) -> List[ModelInfo]:
        """Curated subset of Together AI's hosted open-source models.

        Shows breadth (Llama + Qwen + DeepSeek + Mistral) at the price
        points most operators ask about. Pricing set to ``None`` (cost
        unknown at boot) so the UI doesn't lie; ops can populate
        per-model prices from the Together pricing page when needed.
        """
        common_caps = [
            ModelCapability.STREAMING,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.JSON_MODE,
            ModelCapability.SYSTEM_MESSAGES,
        ]
        return [
            ModelInfo(
                id="meta-llama/Llama-3.3-70B-Instruct-Turbo",
                display_name="Llama 3.3 70B Instruct Turbo",
                provider_name=self.display_name,
                context_window=131072,
                pricing=None,
                capabilities=common_caps,
                description=(
                    "Meta's Llama 3.3 70B with Together's Turbo inference "
                    "(FP-8 quant, sub-second TTFT on small prompts)."
                ),
                recommended_for=["general chat", "function calling", "cost-effective"],
            ),
            ModelInfo(
                id="Qwen/Qwen2.5-72B-Instruct-Turbo",
                display_name="Qwen 2.5 72B Instruct Turbo",
                provider_name=self.display_name,
                context_window=32768,
                pricing=None,
                capabilities=common_caps,
                description=(
                    "Alibaba's Qwen 2.5 72B, top multilingual open model "
                    "(29+ languages, strong on non-English)."
                ),
                recommended_for=["multilingual", "general chat", "cost-effective"],
            ),
            ModelInfo(
                id="deepseek-ai/DeepSeek-R1",
                display_name="DeepSeek R1 (Reasoning)",
                provider_name=self.display_name,
                context_window=65536,
                pricing=None,
                capabilities=common_caps,
                description=(
                    "DeepSeek R1 reasoning model with chain-of-thought "
                    "trace. Competes with o1 on math/coding benchmarks."
                ),
                recommended_for=["complex reasoning", "math", "scientific analysis"],
            ),
            ModelInfo(
                id="mistralai/Mistral-Small-24B-Instruct-2501",
                display_name="Mistral Small 24B (Latest)",
                provider_name=self.display_name,
                context_window=32768,
                pricing=None,
                capabilities=common_caps,
                description=(
                    "Mistral's mid-size latest release. Apache 2.0, "
                    "strong function-calling, EU-hosted inference."
                ),
                recommended_for=["general chat", "function calling", "EU data residency"],
            ),
            ModelInfo(
                id="meta-llama/Llama-3.2-11B-Vision-Instruct-Turbo",
                display_name="Llama 3.2 11B Vision Turbo",
                provider_name=self.display_name,
                context_window=131072,
                pricing=None,
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.VISION,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description=(
                    "Llama 3.2 11B vision-capable. Cheapest vision option "
                    "across the wiring for stargazers testing image inputs."
                ),
                recommended_for=["vision", "low-cost", "image understanding"],
            ),
            ModelInfo(
                id="meta-llama/Llama-3.1-8B-Instruct-Turbo",
                display_name="Llama 3.1 8B Instruct Turbo (Cheapest)",
                provider_name=self.display_name,
                context_window=131072,
                pricing=None,
                capabilities=common_caps,
                description=(
                    "Cheapest model on Together. Suitable for dev/CI runs, "
                    "high-throughput classification, and budget research."
                ),
                recommended_for=["budget", "high throughput", "dev/CI"],
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
        """Create a Together model instance via OpenAI-compatible client."""
        model_info = self.get_model_info(model_id)
        if not model_info:
            available = [m.id for m in self.list_models()]
            raise ValueError(
                f"Model '{model_id}' not available. Available models: {', '.join(available)}"
            )

        api_key = self.get_api_key()
        if not api_key:
            raise RuntimeError(
                "Together AI API key required. "
                "Set TOGETHER_API_KEY environment variable or provide in config."
            )

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
            base_url=self.config.get("base_url", TOGETHER_BASE_URL),
            request_timeout=timeout,  # type: ignore[call-arg]
            **kwargs,
        )
        if max_tokens is not None:
            llm.max_tokens = max_tokens
        return llm

    def validate_connection(self) -> tuple[bool, Optional[str]]:
        """Validate Together AI connection. Cheap (no network round-trip)."""
        api_key = self.get_api_key()
        if not api_key:
            return False, "API key not provided"
        try:
            models = self.list_models()
            if models:
                return True, None
            return False, "No models available"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
