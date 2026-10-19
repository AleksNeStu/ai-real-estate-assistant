"""
Fireworks AI model provider implementation.

Supports the Fireworks AI hosted-inference API (OpenAI-compatible) for
production-grade open-source models with sub-200ms TTFT.

Stargazer hook: speed brag (custom GPU stack, fastest inference), broad
function-calling support, transparent pricing per token at the
``accounts/fireworks/models/<slug>`` path.

Reference docs (live-verified 2026-10-20):
- https://docs.fireworks.ai/api-reference/inference-api
- https://fireworks.ai/models
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

FIREWORKS_BASE_URL = "https://api.fireworks.ai/inference/v1"
# All Fireworks model IDs route through the ``accounts/fireworks/models/``
# namespace; the OpenAI-compat endpoint rejects bare model IDs without it.
_FIREWORKS_MODEL_PREFIX = "accounts/fireworks/models/"


class FireworksProvider(RemoteModelProvider):
    """Fireworks AI model provider using the OpenAI-compatible API."""

    @property
    def name(self) -> str:
        return "fireworks"

    @property
    def display_name(self) -> str:
        return "Fireworks AI"

    def __init__(self, config: Optional[dict[str, Any]] = None):
        super().__init__(config)
        if "api_key" not in self.config:
            self.config["api_key"] = os.getenv("FIREWORKS_API_KEY")
        if "base_url" not in self.config:
            self.config["base_url"] = FIREWORKS_BASE_URL

    def list_models(self) -> List[ModelInfo]:
        """Curated Fireworks models — speed + breadth.

        Curation biases toward (a) the speed-brag small models so
        stargazers see Fireworks' <200ms TTFT promise on day one, and
        (b) the reasoning+function-calling models most operators use
        in production. Each ID is prefixed with
        ``accounts/fireworks/models/`` because that's what the
        OpenAI-compat endpoint expects.
        """

        def _id(slug: str) -> str:
            return _FIREWORKS_MODEL_PREFIX + slug

        common_caps = [
            ModelCapability.STREAMING,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.JSON_MODE,
            ModelCapability.SYSTEM_MESSAGES,
        ]
        return [
            ModelInfo(
                id=_id("llama-v3p3-70b-instruct"),
                display_name="Llama 3.3 70B Instruct (Firewoks)",
                provider_name=self.display_name,
                context_window=131072,
                pricing=None,
                capabilities=common_caps,
                description=(
                    "Llama 3.3 70B on Fireworks' GPU stack. Best "
                    "default for production chat traffic."
                ),
                recommended_for=["general chat", "function calling", "production"],
            ),
            ModelInfo(
                id=_id("deepseek-r1"),
                display_name="DeepSeek R1 (Reasoning)",
                provider_name=self.display_name,
                context_window=164000,
                pricing=None,
                capabilities=common_caps,
                description=(
                    "DeepSeek R1 with explicit chain-of-thought. Fireworks "
                    "serves it with predictably-fast first-token latency."
                ),
                recommended_for=["complex reasoning", "math", "scientific analysis"],
            ),
            ModelInfo(
                id=_id("qwen2p5-72b-instruct"),
                display_name="Qwen 2.5 72B Instruct",
                provider_name=self.display_name,
                context_window=32768,
                pricing=None,
                capabilities=common_caps,
                description=(
                    "Alibaba's Qwen 2.5 72B. Multilingual strength "
                    "(29+ languages) on Fireworks' speed-first stack."
                ),
                recommended_for=["multilingual", "general chat", "EU/CN regions"],
            ),
            ModelInfo(
                id=_id("llama-v3p3-8b-instruct"),
                display_name="Llama 3.3 8B Instruct (Fast)",
                provider_name=self.display_name,
                context_window=131072,
                pricing=None,
                capabilities=common_caps,
                description=(
                    "Llama 3.3 8B on Fireworks. Sub-200ms TTFT for "
                    "interactive demos; cheapest path to speed."
                ),
                recommended_for=["interactive demo", "speed", "budget"],
            ),
            ModelInfo(
                id=_id("llama-v3p2-3b-instruct"),
                display_name="Llama 3.2 3B Instruct (Fastest)",
                provider_name=self.display_name,
                context_window=131072,
                pricing=None,
                capabilities=common_caps,
                description=(
                    "Cheapest Fireworks model. Suitable for high-throughput "
                    "classification and dev/CI batch jobs."
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
        """Create a Fireworks model instance via the OpenAI-compatible client."""
        # Auto-prefix the ``accounts/fireworks/models/`` namespace if the
        # caller passed a bare slug. Curated ``list_models()`` entries
        # already include the prefix, but external callers sometimes omit it.
        if not model_id.startswith(_FIREWORKS_MODEL_PREFIX):
            model_id = _FIREWORKS_MODEL_PREFIX + model_id

        api_key = self.get_api_key()
        if not api_key:
            raise RuntimeError(
                "Fireworks AI API key required. "
                "Set FIREWORKS_API_KEY environment variable or provide in config."
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
            base_url=self.config.get("base_url", FIREWORKS_BASE_URL),
            request_timeout=timeout,  # type: ignore[call-arg]
            **kwargs,
        )
        if max_tokens is not None:
            llm.max_tokens = max_tokens
        return llm

    def validate_connection(self) -> tuple[bool, Optional[str]]:
        """Validate Fireworks connection. Cheap (no network round-trip)."""
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
