"""
The model a tool speaks with.

A tool that builds its own model bypasses the demo guard and the per-user
preference cascade. On a deployment without a provider key the feature dies
with "Zhipu AI API key required" while the rest of the application runs on
the mock model - the tool builds a model the application never chose.

The order here is the one the application uses everywhere else:

1. the model the caller resolved and injected - that is the model the
   user chose, and it is the first choice;
2. a demo deployment speaks with the mock model, never with a provider,
   so no demo visitor can spend a token;
3. only a standalone tool without an injected model falls back to the
   configured provider, and it says so when it cannot.
"""

import logging
from typing import Any, Optional

from langchain_core.language_models import BaseChatModel

from config.settings import get_settings

logger = logging.getLogger(__name__)


def resolve_tool_llm(
    injected: Optional[BaseChatModel] = None,
    *,
    task_type: str = "tools",
    model_id: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> Optional[BaseChatModel]:
    """The model this tool should speak with.

    Args:
        injected: The model the caller resolved. Used as is.
        task_type: The name of the feature, for the log line.
        model_id: The model to ask for in the fallback case.
        temperature: The temperature for the fallback case.
        max_tokens: The token budget for the fallback case.
    """
    if injected is not None:
        return injected

    settings = get_settings()

    if settings.demo_mode:
        from core.demo import get_demo_llm

        return get_demo_llm()

    try:
        from models.provider_factory import ModelProviderFactory

        kwargs: dict[str, Any] = {
            "model_id": model_id or settings.default_model or "gpt-4o-mini",
            "provider_name": settings.default_provider,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        return ModelProviderFactory.create_model(**kwargs)
    except Exception as exc:
        logger.warning("No LLM available for %s: %s", task_type, exc)
        return None
