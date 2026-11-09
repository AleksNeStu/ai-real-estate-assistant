"""
MiniMax model provider implementation.

MiniMax speaks the OpenAI-compatible protocol, so this provider is a thin
wrapper over ``ChatOpenAI`` with a different base URL and key — the same shape
as OpenRouter and Groq.

Two things make it more than a copy of that shape:

* the model list is **updatable without a code change** — ``MINIMAX_MODELS``
  (a comma-separated list of model ids) is appended to the curated list, so a
  new MiniMax release is a deployment variable, not a pull request;
* the base URL is a deployment variable (``MINIMAX_BASE_URL``), so the
  international and the regional endpoints are the same code.
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

MINIMAX_BASE_URL = "https://api.minimax.io/v1"

# The effort levels MiniMax accepts. Anything else is ignored - the
# deployment must not be able to break the API with a typo.
_REASONING_EFFORTS = frozenset({"minimal", "low", "medium", "high", "xhigh", "max", "none"})


class MiniMaxProvider(RemoteModelProvider):
    """MiniMax model provider — OpenAI-compatible API."""

    @property
    def name(self) -> str:
        return "minimax"

    @property
    def display_name(self) -> str:
        return "MiniMax"

    def __init__(self, config: Optional[dict[str, Any]] = None):
        super().__init__(config)
        if "api_key" not in self.config:
            # The project-scoped key wins over the workstation-wide one, so a
            # developer's own MiniMax account does not shadow the deployment's.
            self.config["api_key"] = os.getenv("REALT_MINIMAX_API_KEY") or os.getenv(
                "MINIMAX_API_KEY"
            )
        if "base_url" not in self.config:
            self.config["base_url"] = os.getenv("MINIMAX_BASE_URL") or MINIMAX_BASE_URL

    def list_models(self) -> List[ModelInfo]:
        """The curated MiniMax models, plus any the deployment adds.

        ``MINIMAX_MODELS`` is a comma-separated list of model ids. Every id in
        it becomes an entry, so the list can grow without touching the code.
        """
        models: List[ModelInfo] = [
            ModelInfo(
                id="MiniMax-M3.1-Flash",
                display_name="MiniMax M3.1 Flash",
                provider_name=self.display_name,
                context_window=204800,
                pricing=None,
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="MiniMax M3.1 Flash — fast, cheap, tool calling, multilingual",
                recommended_for=["demo", "chat", "tools", "multilingual"],
            ),
            ModelInfo(
                id="MiniMax-M2.7",
                display_name="MiniMax M2.7",
                provider_name=self.display_name,
                context_window=204800,
                pricing=None,
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="MiniMax M2.7 — stronger reasoning, slower",
                recommended_for=["analysis", "tools"],
            ),
        ]

        known = {model.id for model in models}
        for model_id in _configured_model_ids():
            if model_id in known:
                continue
            models.append(
                ModelInfo(
                    id=model_id,
                    display_name=model_id,
                    provider_name=self.display_name,
                    context_window=0,
                    pricing=PricingInfo(input_price_per_1m=0.0, output_price_per_1m=0.0),
                    capabilities=[
                        ModelCapability.STREAMING,
                        ModelCapability.FUNCTION_CALLING,
                        ModelCapability.SYSTEM_MESSAGES,
                    ],
                    description="Configured through MINIMAX_MODELS",
                    recommended_for=["demo", "chat"],
                )
            )

        return models

    def create_model(
        self,
        model_id: str,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        streaming: bool = True,
        request_timeout: Optional[float] = None,
        **kwargs: Any,
    ) -> BaseChatModel:
        """Create a MiniMax model instance via the OpenAI-compatible API."""
        api_key = self.get_api_key()
        if not api_key:
            raise RuntimeError(
                "MiniMax API key required. "
                "Set MINIMAX_API_KEY environment variable or provide in config."
            )

        if request_timeout is None:
            from config.settings import get_settings

            request_timeout = get_settings().llm_request_timeout_seconds

        # How hard the model thinks. M3.1 Flash always reasons and reasons at
        # 'max' when the parameter is missing, which costs the most tokens for
        # the least extra value in a demo that answers from a catalogue. The
        # knob is the deployment's, not the code's: an unknown value is
        # ignored rather than sent to the API.
        effort = self._reasoning_effort(model_id)
        if effort:
            extra_body = dict(kwargs.pop("extra_body", None) or {})
            extra_body["reasoning"] = {"effort": effort}
            kwargs["extra_body"] = extra_body

        llm = ChatOpenAI(
            model=model_id,
            temperature=temperature,
            streaming=streaming,
            api_key=SecretStr(api_key),
            base_url=self.config.get("base_url") or MINIMAX_BASE_URL,
            request_timeout=request_timeout,
            **kwargs,
        )
        if max_tokens is not None:
            llm.max_tokens = max_tokens
        return llm

    def _reasoning_effort(self, model_id: str) -> Optional[str]:
        """The effort the deployment asks for, if it asks for one."""
        from config.settings import get_settings

        effort = (get_settings().minimax_reasoning_effort or "").strip().lower()
        if effort not in _REASONING_EFFORTS:
            return None
        # M3.1 Flash always reasons and answers HTTP 400 to 'none'.
        if effort == "none" and "M3.1-Flash" in model_id:
            return None
        return effort

    def validate_connection(self) -> tuple[bool, Optional[str]]:
        """Validate the MiniMax connection: a key and at least one model."""
        api_key = self.get_api_key()
        if not api_key:
            return False, "API key not provided"
        try:
            if self.list_models():
                return True, None
            return False, "No models available"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"


def _configured_model_ids() -> List[str]:
    """The model ids the deployment adds through ``MINIMAX_MODELS``."""
    raw = os.getenv("MINIMAX_MODELS") or ""
    return [part.strip() for part in raw.split(",") if part.strip()]
