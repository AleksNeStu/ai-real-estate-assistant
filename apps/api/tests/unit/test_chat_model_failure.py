"""A model that failed is not an answer.

The deployed demo answered every prompt with the provider's own error text and
a 200: "Error processing query with RAG: Error code: 429 - Token Plan usage
limit reached ... request_id ...". The visitor read a stack trace as an answer,
and the API said the request had succeeded.

These tests pin the contract that replaced it:
  - a failed model answers 503 with a sentence a reader can act on;
  - the provider's error text (quota, account, request id) never reaches the
    client - it stays in the log;
  - an open deployment does not depend on ONE account: an anonymous visitor
    goes to the free cascade, so a depleted plan on the first provider is not
    a dead demo.
"""

from contextlib import ExitStack, contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from api.dependencies import get_llm, get_vector_store
from api.routers.chat import router as chat_router

# The provider's request id: a fake value in a test, not a credential.
PROVIDER_REQUEST_ID = "0758129658f4725cd02a62429c6bd8a8"  # pragma: allowlist secret

# What the provider said. None of it may reach the client.
PROVIDER_ERROR = (
    "Error code: 429 - {'type': 'error', 'error': {'type': 'rate_limit_error', "
    "'message': 'Token Plan usage limit reached (2056)', 'http_code': '429'}, "
    f"'request_id': '{PROVIDER_REQUEST_ID}'}}"
)


def _mock_settings():
    settings = MagicMock()
    settings.chat_sources_max_items = 50
    settings.chat_source_content_max_chars = 500
    settings.chat_sources_max_total_bytes = 100000
    settings.stream_heartbeat_interval_seconds = 15
    settings.stream_timeout_seconds = 45
    settings.stream_metrics_enabled = False
    settings.context_max_utilization_percent = 80.0
    settings.context_metrics_enabled = False
    settings.internet_enabled = False
    settings.searxng_url = None
    settings.web_search_max_results = 5
    settings.web_fetch_timeout_seconds = 10.0
    settings.web_fetch_max_bytes = 300_000
    settings.web_allowlist_domains = []
    # A private deployment: the API key identifies it, and its own provider
    # answers. The open-deployment case turns the bypass on.
    settings.demo_api_key_bypass = False
    settings.demo_llm_mode = False
    return settings


def _agent(answer: str, error: str | None = None):
    agent = MagicMock()
    result = {"answer": answer, "source_documents": [], "method": "rag"}
    if error is not None:
        result["error"] = error
    agent.process_query.return_value = result
    agent.astream_query = AsyncMock()
    agent.analyzer = None
    return agent


@contextmanager
def _router(settings, agent):
    """The chat router with the agent and the settings in place."""
    with ExitStack() as stack:
        stack.enter_context(patch("api.routers.chat.create_hybrid_agent", return_value=agent))
        stack.enter_context(patch("api.routers.chat.get_settings", return_value=settings))
        stack.enter_context(patch("api.routers.chat.get_context_manager", return_value=MagicMock()))
        stack.enter_context(
            patch(
                "api.routers.chat.get_optimized_memory",
                return_value=(MagicMock(), None),
            )
        )
        yield


@pytest.fixture
async def chat_client():
    test_app = FastAPI()
    test_app.include_router(chat_router, prefix="/api/v1")

    test_app.dependency_overrides[get_llm] = lambda: MagicMock()
    test_app.dependency_overrides[get_vector_store] = lambda: MagicMock()

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    test_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# The failure is not an answer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_failed_model_answers_503(chat_client):
    agent = _agent(
        "I could not answer that right now: the model is temporarily unavailable. "
        "Please try again in a moment.",
        error=PROVIDER_ERROR,
    )
    with _router(_mock_settings(), agent):
        response = await chat_client.post("/api/v1/chat", json={"message": "any question"})

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    detail = response.json()["detail"]
    assert "temporarily unavailable" in detail


@pytest.mark.asyncio
async def test_the_provider_error_never_reaches_the_client(chat_client):
    """The quota, the account and the request id are the server's business."""
    agent = _agent(
        "I could not answer that right now: the model is temporarily unavailable. "
        "Please try again in a moment.",
        error=PROVIDER_ERROR,
    )
    with _router(_mock_settings(), agent):
        response = await chat_client.post("/api/v1/chat", json={"message": "any question"})

    body = response.text
    assert "429" not in body
    assert "Token Plan" not in body
    assert "request_id" not in body
    assert PROVIDER_REQUEST_ID not in body


@pytest.mark.asyncio
async def test_an_answer_is_still_an_answer(chat_client):
    """The fix does not touch the happy path."""
    agent = _agent("Two listings match.")
    with _router(_mock_settings(), agent):
        response = await chat_client.post("/api/v1/chat", json={"message": "any question"})

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["response"] == "Two listings match."


# ---------------------------------------------------------------------------
# The agent itself
# ---------------------------------------------------------------------------


def test_the_agent_does_not_answer_with_the_provider_error():
    """The agent's own answer is what every other surface shows."""
    from langchain_core.callbacks import CallbackManagerForLLMRun
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.outputs import ChatResult

    from agents.hybrid_agent import HybridPropertyAgent
    from agents.query_analyzer import Complexity, QueryAnalysis, QueryIntent

    class _ExplodingModel(BaseChatModel):
        """A model whose provider answered with the quota error."""

        @property
        def _llm_type(self) -> str:
            return "exploding"

        def _generate(
            self,
            messages: list,
            stop: list | None = None,
            run_manager: CallbackManagerForLLMRun | None = None,
            **kwargs,
        ) -> ChatResult:
            raise RuntimeError(PROVIDER_ERROR)

    class _OneListing(BaseRetriever):
        """A retriever that always returns one document."""

        def _get_relevant_documents(self, query, *, run_manager=None):
            return [Document(page_content="a listing")]

    agent = HybridPropertyAgent(llm=_ExplodingModel(), retriever=_OneListing())

    analysis = QueryAnalysis(
        query="what is there?",
        intent=QueryIntent.SIMPLE_RETRIEVAL,
        complexity=Complexity.SIMPLE,
        extracted_filters={},
        confidence=0.9,
    )

    result = agent._process_with_rag("what is there?", analysis)

    assert "429" not in result["answer"]
    assert "Token Plan" not in result["answer"]
    assert result["error"]  # the raw failure is still there, for the log
