"""
HuggingFace Inference Router model provider.

Supports the HuggingFace hosted-inference router API (OpenAI-compatible)
which fronts 100k+ community models behind a single API key.

Stargazer hook: bridge to the HuggingFace ecosystem; one key opens the
community-DPO + fine-tuned-model surface that HF users already know how
to navigate.

Reference docs (live-verified 2026-10-20):
- https://huggingface.co/docs/inference-providers/en/index
- https://huggingface.co/docs/inference-providers/en/providers/hf-inference
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

HUGGINGFACE_BASE_URL = "https://router.huggingface.co/v1"


class HuggingFaceProvider(RemoteModelProvider):
    """HuggingFace Inference Router provider using the OpenAI-compatible API."""

    @property
    def name(self) -> str:
        return "huggingface"

    @property
    def display_name(self) -> str:
        return "HuggingFace"

    def __init__(self, config: Optional[dict[str, Any]] = None):
        super().__init__(config)
        if "api_key" not in self.config:
            self.config["api_key"] = os.getenv("HUGGINGFACE_API_KEY")
        if "base_url" not in self.config:
            self.config["base_url"] = HUGGINGFACE_BASE_URL

    def list_models(self) -> List[ModelInfo]:
        """Curated HuggingFace Inference Router models.

        Curation biases toward (a) community-locked meta-llama / Qwen /
        DeepSeek models most operators request and (b) one smaller /
        faster option. ``pricing=None`` (unknown at boot) so the UI
        doesn't lie; HF charges per-token and per-model so a single
        price number wouldn't generalize anyway.
        """
        common_caps = [
            ModelCapability.STREAMING,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.JSON_MODE,
            ModelCapability.SYSTEM_MESSAGES,
        ]
        return [
            ModelInfo(
                id="meta-llama/Llama-3.3-70B-Instruct",
                display_name="Llama 3.3 70B Instruct",
                provider_name=self.display_name,
                context_window=131072,
                pricing=None,
                capabilities=common_caps,
                description=(
                    "Meta's Llama 3.3 70B via the HF Inference Router. "
                    "Top general-purpose default for HF users."
                ),
                recommended_for=["general chat", "function calling"],
            ),
            ModelInfo(
                id="Qwen/Qwen2.5-72B-Instruct",
                display_name="Qwen 2.5 72B Instruct",
                provider_name=self.display_name,
                context_window=32768,
                pricing=None,
                capabilities=common_caps,
                description=("Alibaba's Qwen 2.5 72B — multilingual strength on the HF router."),
                recommended_for=["multilingual", "general chat"],
            ),
            ModelInfo(
                id="deepseek-ai/DeepSeek-V3",
                display_name="DeepSeek V3 (Reasoning + Chat)",
                provider_name=self.display_name,
                context_window=65536,
                pricing=None,
                capabilities=common_caps,
                description=(
                    "DeepSeek V3 served by HF partners. Strong "
                    "general-purpose reasoning at low cost."
                ),
                recommended_for=["reasoning", "general chat", "cost-effective"],
            ),
            ModelInfo(
                id="meta-llama/Llama-3.1-8B-Instruct",
                display_name="Llama 3.1 8B Instruct (Fast + Cheap)",
                provider_name=self.display_name,
                context_window=131072,
                pricing=None,
                capabilities=common_caps,
                description=(
                    "Llama 3.1 8B on the HF router. Best entry-tier "
                    "option for HF users running high-throughput batches."
                ),
                recommended_for=["budget", "high throughput", "dev/CI"],
            ),
            ModelInfo(
                id="mistralai/Mistral-7B-Instruct-v0.3",
                display_name="Mistral 7B Instruct v0.3",
                provider_name=self.display_name,
                context_window=32768,
                pricing=None,
                capabilities=common_caps,
                description=(
                    "Mistral's open 7B. Apache 2.0, EU-friendly "
                    "hosting, popular with European dev tooling."
                ),
                recommended_for=["EU data residency", "open-source", "budget"],
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
        """Create a HuggingFace Inference Router model via OpenAI-compatible client."""
        api_key = self.get_api_key()
        if not api_key:
            raise RuntimeError(
                "HuggingFace API key required. "
                "Set HUGGINGFACE_API_KEY environment variable or provide in config."
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
            base_url=self.config.get("base_url", HUGGINGFACE_BASE_URL),
            request_timeout=timeout,  # type: ignore[call-arg]
            **kwargs,
        )
        if max_tokens is not None:
            llm.max_tokens = max_tokens
        return llm

    def validate_connection(self) -> tuple[bool, Optional[str]]:
        """Validate HuggingFace connection. Cheap (no network round-trip)."""
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
