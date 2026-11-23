"""The free-tier cascade must fall through at call time.

The cascade used to end at the first provider whose client could be
*built*. A provider that builds and then fails - depleted prepaid credits,
a rate limit, an outage - ended the request instead of the next provider
taking over, so a provider that is registered but cannot answer was a
fallback that never fell back.

Measured on the demo (2026-11-23): the cascade was google,minimax,ollama,
openrouter and the Google key's prepaid credits were depleted, so every
anonymous chat answered the visitor with the raw 402. The node's cascade
was reordered and the chat answered again - but the code still had no
fallthrough, so the next provider to die ends the demo the same way.
"""

from __future__ import annotations

from typing import Any, Optional

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from starlette.requests import Request

from api.models import ChatRequest
from api.routers import chat
from utils import free_tier


class _FakeModel(BaseChatModel):
    """A provider client that either answers or refuses."""

    answer: str = "answered"
    refuses: bool = False
    calls: int = 0
    model_name: str = "fake-model"

    @property
    def _llm_type(self) -> str:
        return "fake"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        self.calls += 1
        if self.refuses:
            raise RuntimeError("provider refused: RESOURCE_EXHAUSTED")
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=self.answer))])


class _Settings:
    """A deployment with a free tier and a cascade of its own."""

    demo_llm_mode = False
    free_tier_enabled = True

    def __init__(self, cascade: list[str]) -> None:
        self.free_tier_provider_cascade = cascade


@pytest.fixture(autouse=True)
def _clean_provider_cache():
    free_tier.reset_free_tier_provider_cache()
    yield
    free_tier.reset_free_tier_provider_cache()


def _cascade(monkeypatch, models: dict[str, _FakeModel], order: list[str]) -> None:
    """Point the cascade at the given fake providers, in the given order."""
    monkeypatch.setattr(free_tier, "get_settings", lambda: _Settings(order))
    for name, model in models.items():
        monkeypatch.setitem(free_tier._PROVIDERS_BY_NAME, name, lambda model=model: model)


@pytest.mark.asyncio
async def test_the_cascade_falls_through_to_the_next_provider(monkeypatch):
    """A provider that builds and then fails must not end the request."""
    first = _FakeModel(refuses=True)
    second = _FakeModel(answer="from the second")
    _cascade(monkeypatch, {"first": first, "second": second}, ["first", "second"])

    llm = free_tier.get_llm_for_free_user()
    assert llm is not None

    message = await llm.ainvoke([HumanMessage(content="hello")])

    assert message.content == "from the second"
    assert first.calls == 1, "the failing provider must have been tried"
    assert second.calls == 1


@pytest.mark.asyncio
async def test_the_sync_path_falls_through_too(monkeypatch):
    first = _FakeModel(refuses=True)
    second = _FakeModel(answer="from the second")
    _cascade(monkeypatch, {"first": first, "second": second}, ["first", "second"])

    llm = free_tier.get_llm_for_free_user()
    assert llm is not None

    message = llm.invoke([HumanMessage(content="hello")])

    assert message.content == "from the second"


@pytest.mark.asyncio
async def test_a_provider_that_answers_is_not_skipped(monkeypatch):
    """The cascade stops at the first provider that answers."""
    first = _FakeModel(answer="from the first")
    second = _FakeModel(answer="from the second")
    _cascade(monkeypatch, {"first": first, "second": second}, ["first", "second"])

    llm = free_tier.get_llm_for_free_user()
    assert llm is not None

    message = await llm.ainvoke([HumanMessage(content="hello")])

    assert message.content == "from the first"
    assert second.calls == 0


@pytest.mark.asyncio
async def test_every_provider_failing_names_the_provider_and_not_the_stack(monkeypatch):
    """The visitor gets the names, never the provider's raw error."""
    _cascade(
        monkeypatch,
        {"first": _FakeModel(refuses=True), "second": _FakeModel(refuses=True)},
        ["first", "second"],
    )

    llm = free_tier.get_llm_for_free_user()
    assert llm is not None

    with pytest.raises(free_tier.FreeTierProvidersUnavailable) as excinfo:
        await llm.ainvoke([HumanMessage(content="hello")])

    message = str(excinfo.value)
    assert "first" in message
    assert "second" in message
    assert "RESOURCE_EXHAUSTED" not in message, "the raw provider error must not reach the visitor"
    assert "Traceback" not in message


@pytest.mark.asyncio
async def test_the_error_carries_every_failed_provider(monkeypatch):
    _cascade(
        monkeypatch,
        {"first": _FakeModel(refuses=True), "second": _FakeModel(refuses=True)},
        ["first", "second"],
    )

    llm = free_tier.get_llm_for_free_user()
    assert llm is not None

    with pytest.raises(free_tier.FreeTierProvidersUnavailable) as excinfo:
        await llm.ainvoke([HumanMessage(content="hello")])

    assert [name for name, _ in excinfo.value.failures] == ["first", "second"]


def test_no_provider_can_be_built_returns_none(monkeypatch):
    """The 503 of the router keeps its meaning: nothing can answer at all."""

    def _nothing():
        return None

    monkeypatch.setattr(free_tier, "get_settings", lambda: _Settings(["first"]))
    monkeypatch.setitem(free_tier._PROVIDERS_BY_NAME, "first", _nothing)

    assert free_tier.get_llm_for_free_user() is None


def test_the_model_carries_the_name_of_its_first_provider(monkeypatch):
    """The context manager sizes the history against a model name."""
    _cascade(
        monkeypatch,
        {"first": _FakeModel(answer="from the first"), "second": _FakeModel()},
        ["first", "second"],
    )

    llm = free_tier.get_llm_for_free_user()
    assert llm is not None

    assert llm.model_name == "fake-model"


def _request() -> Request:
    """A request from an anonymous address."""
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/chat/free",
            "headers": [(b"x-forwarded-for", b"203.0.113.9")],
            "client": ("203.0.113.9", 12345),
        }
    )


@pytest.mark.asyncio
async def test_the_endpoint_answers_503_naming_the_failed_providers(monkeypatch):
    """The visitor gets the names of the failed providers, not a raw error."""
    from fastapi import HTTPException

    class _Settings:
        free_tier_enabled = True
        demo_llm_mode = False

    def _boom(*_args, **_kwargs):
        raise free_tier.FreeTierProvidersUnavailable(
            [("google", "RuntimeError"), ("minimax", "RuntimeError")]
        )

    monkeypatch.setattr(chat, "get_settings", lambda: _Settings())
    monkeypatch.setattr(chat, "_build_agent_and_process", _boom)
    monkeypatch.setattr(chat, "get_llm_for_free_user", lambda: _FakeModel())

    with pytest.raises(HTTPException) as excinfo:
        await chat.chat_free_endpoint(
            request=ChatRequest(message="hello"),
            req=_request(),
            store=object(),
            memory_service=object(),
            user=None,
        )

    assert excinfo.value.status_code == 503
    detail = excinfo.value.detail
    assert "google" in detail
    assert "minimax" in detail
    assert "RuntimeError" not in detail
