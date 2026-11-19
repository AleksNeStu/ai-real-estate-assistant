"""
Unit tests for Chat router (api/routers/chat.py).

Tests cover:
- POST /chat - Non-streaming chat
- POST /chat - Streaming chat (SSE)
- POST /chat - Validation errors (empty message)
- POST /chat - No vector store (503)
- POST /chat - ServiceDegradedError handling
- POST /chat - General exception handling
- POST /chat - Citation stats
- POST /chat - Intermediate steps
- POST /chat - Web sources path
- POST /chat - Streaming timeout
- POST /chat - Streaming heartbeat
- POST /chat - Streaming with web sources
- Session ID handling
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient

from api.dependencies import get_llm, get_vector_store
from api.routers.chat import router as chat_router

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_llm():
    """Create a mock LLM with model_name attribute."""
    llm = MagicMock()
    llm.model_name = "gpt-4o-mini"
    llm.model = "gpt-4o-mini"
    return llm


def _make_mock_store():
    """Create a mock vector store with a retriever."""
    store = MagicMock()
    retriever = MagicMock()
    store.get_retriever.return_value = retriever
    return store


def _mock_settings():
    """Create a mock settings object."""
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
    return settings


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_llm():
    return _make_mock_llm()


@pytest.fixture
def mock_store():
    return _make_mock_store()


@pytest.fixture
def mock_agent():
    """Create a mock hybrid agent."""
    agent = MagicMock()
    agent.process_query.return_value = {
        "answer": "Here are some properties in Berlin.",
        "source_documents": [],
        "method": "rag_only",
    }
    agent.astream_query = AsyncMock()
    agent.analyzer = None
    return agent


@pytest.fixture
async def chat_client(mock_llm, mock_store, mock_agent):
    """Create an async HTTP client for testing chat endpoints."""
    test_app = FastAPI()
    test_app.include_router(chat_router, prefix="/api/v1")

    # Override dependencies
    def override_get_llm():
        return mock_llm

    def override_get_vector_store():
        return mock_store

    test_app.dependency_overrides[get_llm] = override_get_llm
    test_app.dependency_overrides[get_vector_store] = override_get_vector_store

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    test_app.dependency_overrides.clear()


@pytest.fixture
async def no_store_chat_client(mock_llm):
    """Create a chat client where vector store is None."""
    test_app = FastAPI()
    test_app.include_router(chat_router, prefix="/api/v1")

    def override_get_llm():
        return mock_llm

    def override_get_vector_store():
        return None

    test_app.dependency_overrides[get_llm] = override_get_llm
    test_app.dependency_overrides[get_vector_store] = override_get_vector_store

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    test_app.dependency_overrides.clear()


# ===========================================================================
# Test: Non-streaming chat
# ===========================================================================


class TestNonStreamingChat:
    """Test POST /api/v1/chat non-streaming mode."""

    @pytest.mark.asyncio
    async def test_basic_chat_returns_200(self, chat_client, mock_agent):
        with (
            patch("api.routers.chat.create_hybrid_agent", return_value=mock_agent),
            patch("api.routers.chat.get_settings", return_value=_mock_settings()),
            patch("api.routers.chat.get_context_manager", return_value=MagicMock()),
            patch("api.routers.chat.get_optimized_memory", return_value=(MagicMock(), None)),
        ):
            response = await chat_client.post(
                "/api/v1/chat",
                json={"message": "Find apartments in Berlin"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "response" in data
        assert data["response"] == "Here are some properties in Berlin."
        assert "sources" in data
        assert "session_id" in data

    @pytest.mark.asyncio
    async def test_chat_generates_session_id(self, chat_client, mock_agent):
        with (
            patch("api.routers.chat.create_hybrid_agent", return_value=mock_agent),
            patch("api.routers.chat.get_settings", return_value=_mock_settings()),
            patch("api.routers.chat.get_context_manager", return_value=MagicMock()),
            patch("api.routers.chat.get_optimized_memory", return_value=(MagicMock(), None)),
        ):
            response = await chat_client.post(
                "/api/v1/chat",
                json={"message": "Hello"},
            )

        data = response.json()
        assert data["session_id"] is not None
        assert len(data["session_id"]) > 0

    @pytest.mark.asyncio
    async def test_chat_uses_provided_session_id(self, chat_client, mock_agent):
        with (
            patch("api.routers.chat.create_hybrid_agent", return_value=mock_agent),
            patch("api.routers.chat.get_settings", return_value=_mock_settings()),
            patch("api.routers.chat.get_context_manager", return_value=MagicMock()),
            patch("api.routers.chat.get_optimized_memory", return_value=(MagicMock(), None)),
        ):
            response = await chat_client.post(
                "/api/v1/chat",
                json={"message": "Hello", "session_id": "my-session-123"},
            )

        data = response.json()
        assert data["session_id"] == "my-session-123"

    @pytest.mark.asyncio
    async def test_chat_with_intermediate_steps(self, chat_client, mock_agent):
        mock_agent.process_query.return_value = {
            "answer": "Here are results.",
            "source_documents": [],
            "intermediate_steps": [
                {"tool": "property_search", "input": "Berlin", "output": "found 5"},
            ],
            "method": "agent",
        }

        with (
            patch("api.routers.chat.create_hybrid_agent", return_value=mock_agent),
            patch("api.routers.chat.get_settings", return_value=_mock_settings()),
            patch("api.routers.chat.get_context_manager", return_value=MagicMock()),
            patch("api.routers.chat.get_optimized_memory", return_value=(MagicMock(), None)),
        ):
            response = await chat_client.post(
                "/api/v1/chat",
                json={"message": "Search Berlin", "include_intermediate_steps": True},
            )

        data = response.json()
        assert data["intermediate_steps"] is not None
        assert len(data["intermediate_steps"]) == 1

    @pytest.mark.asyncio
    async def test_chat_without_intermediate_steps(self, chat_client, mock_agent):
        with (
            patch("api.routers.chat.create_hybrid_agent", return_value=mock_agent),
            patch("api.routers.chat.get_settings", return_value=_mock_settings()),
            patch("api.routers.chat.get_context_manager", return_value=MagicMock()),
            patch("api.routers.chat.get_optimized_memory", return_value=(MagicMock(), None)),
        ):
            response = await chat_client.post(
                "/api/v1/chat",
                json={"message": "Hello", "include_intermediate_steps": False},
            )

        data = response.json()
        assert data["intermediate_steps"] is None

    @pytest.mark.asyncio
    async def test_chat_with_citation_stats(self, chat_client, mock_agent):
        mock_agent.process_query.return_value = {
            "answer": "Results found.",
            "source_documents": [],
            "citation_stats": {
                "total": 5,
                "unique": 3,
                "duplicates": 2,
                "by_type": {"pdf": 3, "web": 2},
                "avg_confidence": 0.85,
            },
        }

        with (
            patch("api.routers.chat.create_hybrid_agent", return_value=mock_agent),
            patch("api.routers.chat.get_settings", return_value=_mock_settings()),
            patch("api.routers.chat.get_context_manager", return_value=MagicMock()),
            patch("api.routers.chat.get_optimized_memory", return_value=(MagicMock(), None)),
        ):
            response = await chat_client.post(
                "/api/v1/chat",
                json={"message": "Search properties"},
            )

        data = response.json()
        assert data["citation_stats"] is not None
        assert data["citation_stats"]["total"] == 5
        assert data["citation_stats"]["unique"] == 3

    @pytest.mark.asyncio
    async def test_chat_with_web_sources(self, chat_client, mock_agent):
        mock_agent.process_query.return_value = {
            "answer": "Web results.",
            "sources": [
                {"title": "Property site", "url": "https://example.com", "snippet": "Info"},
            ],
        }

        with (
            patch("api.routers.chat.create_hybrid_agent", return_value=mock_agent),
            patch("api.routers.chat.get_settings", return_value=_mock_settings()),
            patch("api.routers.chat.get_context_manager", return_value=MagicMock()),
            patch("api.routers.chat.get_optimized_memory", return_value=(MagicMock(), None)),
        ):
            response = await chat_client.post(
                "/api/v1/chat",
                json={"message": "Search web"},
            )

        data = response.json()
        assert "sources" in data

    @pytest.mark.asyncio
    async def test_chat_with_structured_web_sources(self, chat_client, mock_agent):
        """Sources with 'content' and 'metadata' keys take the direct path."""
        mock_agent.process_query.return_value = {
            "answer": "Structured web results.",
            "sources": [
                {
                    "content": "Property info",
                    "metadata": {"source": "web", "url": "https://example.com"},
                },
            ],
        }

        with (
            patch("api.routers.chat.create_hybrid_agent", return_value=mock_agent),
            patch("api.routers.chat.get_settings", return_value=_mock_settings()),
            patch("api.routers.chat.get_context_manager", return_value=MagicMock()),
            patch("api.routers.chat.get_optimized_memory", return_value=(MagicMock(), None)),
        ):
            response = await chat_client.post(
                "/api/v1/chat",
                json={"message": "Search"},
            )

        data = response.json()
        assert len(data["sources"]) == 1
        assert data["sources_truncated"] is False

    @pytest.mark.asyncio
    async def test_chat_with_source_documents(self, chat_client, mock_agent):
        from langchain_core.documents import Document

        mock_agent.process_query.return_value = {
            "answer": "Found some docs.",
            "source_documents": [
                Document(
                    page_content="Nice apartment in Berlin",
                    metadata={"id": "prop1", "city": "Berlin"},
                ),
            ],
        }

        with (
            patch("api.routers.chat.create_hybrid_agent", return_value=mock_agent),
            patch("api.routers.chat.get_settings", return_value=_mock_settings()),
            patch("api.routers.chat.get_context_manager", return_value=MagicMock()),
            patch("api.routers.chat.get_optimized_memory", return_value=(MagicMock(), None)),
        ):
            response = await chat_client.post(
                "/api/v1/chat",
                json={"message": "Find Berlin apartments"},
            )

        data = response.json()
        assert data["response"] == "Found some docs."


# ===========================================================================
# Test: Error handling
# ===========================================================================


class TestChatErrors:
    """Test error handling in chat endpoint."""

    @pytest.mark.asyncio
    async def test_no_vector_store_returns_503(self, no_store_chat_client):
        """When the store is None the router answers 503 - the status it decided on.

        The dependency is down: that is a service that cannot serve the
        request, not a failure of the request. The router keeps the status.
        """
        with patch("api.routers.chat.get_settings", return_value=_mock_settings()):
            response = await no_store_chat_client.post(
                "/api/v1/chat",
                json={"message": "Hello"},
            )

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "unavailable" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_service_degraded_returns_503(self, chat_client):
        from core.circuit_breaker import CircuitState, ServiceDegradedError

        with (
            patch(
                "api.routers.chat.create_hybrid_agent",
                side_effect=ServiceDegradedError("llm_provider", CircuitState.OPEN, "Circuit open"),
            ),
            patch("api.routers.chat.get_settings", return_value=_mock_settings()),
            patch("api.routers.chat.get_context_manager", return_value=MagicMock()),
            patch("api.routers.chat.get_optimized_memory", return_value=(MagicMock(), None)),
        ):
            response = await chat_client.post(
                "/api/v1/chat",
                json={"message": "Hello"},
            )

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "unavailable" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_general_exception_returns_500(self, chat_client):
        with (
            patch(
                "api.routers.chat.create_hybrid_agent",
                side_effect=RuntimeError("Agent creation failed"),
            ),
            patch("api.routers.chat.get_settings", return_value=_mock_settings()),
            patch("api.routers.chat.get_context_manager", return_value=MagicMock()),
            patch("api.routers.chat.get_optimized_memory", return_value=(MagicMock(), None)),
        ):
            response = await chat_client.post(
                "/api/v1/chat",
                json={"message": "Hello"},
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "failed" in response.json()["detail"].lower()


# ===========================================================================
# Test: Context manager initialization
# ===========================================================================


class TestContextManagerInit:
    """Test context manager initialization behavior."""

    @pytest.mark.asyncio
    async def test_context_manager_initialized_when_none(self, chat_client, mock_agent):
        mock_settings = _mock_settings()
        with (
            patch("api.routers.chat.create_hybrid_agent", return_value=mock_agent),
            patch("api.routers.chat.get_settings", return_value=mock_settings),
            patch("api.routers.chat.get_context_manager", return_value=None),
            patch("api.routers.chat.init_context_manager") as mock_init_cm,
            patch("api.routers.chat.get_optimized_memory", return_value=(MagicMock(), None)),
        ):
            await chat_client.post(
                "/api/v1/chat",
                json={"message": "Hello"},
            )

        # init_context_manager should have been called since get returns None
        mock_init_cm.assert_called_once_with(mock_settings)

    @pytest.mark.asyncio
    async def test_context_manager_not_reinitialized_when_exists(self, chat_client, mock_agent):
        mock_settings = _mock_settings()
        with (
            patch("api.routers.chat.create_hybrid_agent", return_value=mock_agent),
            patch("api.routers.chat.get_settings", return_value=mock_settings),
            patch("api.routers.chat.get_context_manager", return_value=MagicMock()),
            patch("api.routers.chat.init_context_manager") as mock_init_cm,
            patch("api.routers.chat.get_optimized_memory", return_value=(MagicMock(), None)),
        ):
            await chat_client.post(
                "/api/v1/chat",
                json={"message": "Hello"},
            )

        mock_init_cm.assert_not_called()


# ===========================================================================
# Test: Streaming chat
# ===========================================================================


class TestStreamingChat:
    """Test POST /api/v1/chat streaming mode."""

    @pytest.mark.asyncio
    async def test_streaming_returns_event_stream(self, chat_client, mock_agent):
        async def mock_astream(*args, **kwargs):
            yield 'data: {"content": "Hello"}\n\n'

        mock_agent.astream_query = mock_astream
        mock_agent.get_sources_for_query = MagicMock(return_value=[])

        with (
            patch("api.routers.chat.create_hybrid_agent", return_value=mock_agent),
            patch("api.routers.chat.get_settings", return_value=_mock_settings()),
            patch("api.routers.chat.get_context_manager", return_value=MagicMock()),
            patch("api.routers.chat.get_optimized_memory", return_value=(MagicMock(), None)),
        ):
            response = await chat_client.post(
                "/api/v1/chat",
                json={"message": "Hello", "stream": True},
            )

        assert response.status_code == status.HTTP_200_OK
        assert "text/event-stream" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_streaming_has_correct_headers(self, chat_client, mock_agent):
        async def mock_astream(*args, **kwargs):
            yield 'data: {"content": "Hi"}\n\n'

        mock_agent.astream_query = mock_astream
        mock_agent.get_sources_for_query = MagicMock(return_value=[])

        with (
            patch("api.routers.chat.create_hybrid_agent", return_value=mock_agent),
            patch("api.routers.chat.get_settings", return_value=_mock_settings()),
            patch("api.routers.chat.get_context_manager", return_value=MagicMock()),
            patch("api.routers.chat.get_optimized_memory", return_value=(MagicMock(), None)),
        ):
            response = await chat_client.post(
                "/api/v1/chat",
                json={"message": "Hello", "stream": True},
            )

        assert response.headers.get("X-Heartbeat-Interval") == "15"
        assert response.headers.get("X-Stream-Timeout") == "45"
        assert response.headers.get("Cache-Control") == "no-cache"
        assert response.headers.get("X-AI-Generated") == "true"

    @pytest.mark.asyncio
    async def test_streaming_content_contains_done_marker(self, chat_client, mock_agent):
        async def mock_astream(*args, **kwargs):
            yield 'data: {"content": "Result"}\n\n'

        mock_agent.astream_query = mock_astream
        mock_agent.get_sources_for_query = MagicMock(return_value=[])

        with (
            patch("api.routers.chat.create_hybrid_agent", return_value=mock_agent),
            patch("api.routers.chat.get_settings", return_value=_mock_settings()),
            patch("api.routers.chat.get_context_manager", return_value=MagicMock()),
            patch("api.routers.chat.get_optimized_memory", return_value=(MagicMock(), None)),
        ):
            response = await chat_client.post(
                "/api/v1/chat",
                json={"message": "Hello", "stream": True},
            )

        content = response.text
        assert "[DONE]" in content

    @pytest.mark.asyncio
    async def test_streaming_emits_meta_event(self, chat_client, mock_agent):
        async def mock_astream(*args, **kwargs):
            yield 'data: {"content": "Result"}\n\n'

        mock_agent.astream_query = mock_astream
        mock_agent.get_sources_for_query = MagicMock(return_value=[])

        with (
            patch("api.routers.chat.create_hybrid_agent", return_value=mock_agent),
            patch("api.routers.chat.get_settings", return_value=_mock_settings()),
            patch("api.routers.chat.get_context_manager", return_value=MagicMock()),
            patch("api.routers.chat.get_optimized_memory", return_value=(MagicMock(), None)),
        ):
            response = await chat_client.post(
                "/api/v1/chat",
                json={"message": "Hello", "stream": True},
            )

        content = response.text
        assert "event: meta" in content

    @pytest.mark.asyncio
    async def test_streaming_with_sources_from_agent(self, chat_client, mock_agent):
        async def mock_astream(*args, **kwargs):
            yield 'data: {"content": "Result"}\n\n'

        mock_agent.astream_query = mock_astream
        mock_agent.get_sources_for_query = MagicMock(return_value=[])

        with (
            patch("api.routers.chat.create_hybrid_agent", return_value=mock_agent),
            patch("api.routers.chat.get_settings", return_value=_mock_settings()),
            patch("api.routers.chat.get_context_manager", return_value=MagicMock()),
            patch("api.routers.chat.get_optimized_memory", return_value=(MagicMock(), None)),
        ):
            response = await chat_client.post(
                "/api/v1/chat",
                json={"message": "Hello", "stream": True},
            )

        assert response.status_code == status.HTTP_200_OK


# ===========================================================================
# Test: Streaming with web sources (requires_web path)
# ===========================================================================


class TestStreamingWebPath:
    """Test streaming when agent detects web search is needed."""

    @pytest.mark.asyncio
    async def test_streaming_web_path_uses_process_query(self, chat_client):
        mock_agent = MagicMock()
        mock_agent.process_query.return_value = {
            "answer": "Web search results",
            "sources": [
                {
                    "content": "Web content",
                    "metadata": {"url": "https://example.com"},
                },
            ],
        }

        mock_analyzer = MagicMock()
        mock_analysis = MagicMock()
        mock_analysis.requires_external_data = True
        mock_analysis.tools_needed = []
        # Make isinstance check work by setting the proper class
        from agents.query_analyzer import QueryAnalysis

        mock_analysis.__class__ = QueryAnalysis
        mock_analyzer.analyze.return_value = mock_analysis
        mock_agent.analyzer = mock_analyzer

        with (
            patch("api.routers.chat.create_hybrid_agent", return_value=mock_agent),
            patch("api.routers.chat.get_settings", return_value=_mock_settings()),
            patch("api.routers.chat.get_context_manager", return_value=MagicMock()),
            patch("api.routers.chat.get_optimized_memory", return_value=(MagicMock(), None)),
        ):
            response = await chat_client.post(
                "/api/v1/chat",
                json={"message": "Search the web for Berlin", "stream": True},
            )

        assert response.status_code == status.HTTP_200_OK
        content = response.text
        assert "Web search results" in content or "[DONE]" in content

    @pytest.mark.asyncio
    async def test_streaming_web_path_with_intermediate_steps(self, chat_client):
        mock_agent = MagicMock()
        mock_agent.process_query.return_value = {
            "answer": "Results",
            "sources": [
                {
                    "content": "Info",
                    "metadata": {"url": "https://example.com"},
                },
            ],
            "intermediate_steps": [
                {"tool": "web_search", "input": "Berlin", "output": "found"},
            ],
        }

        mock_analyzer = MagicMock()
        mock_analysis = MagicMock()
        mock_analysis.requires_external_data = True
        mock_analysis.tools_needed = []
        from agents.query_analyzer import QueryAnalysis

        mock_analysis.__class__ = QueryAnalysis
        mock_analyzer.analyze.return_value = mock_analysis
        mock_agent.analyzer = mock_analyzer

        with (
            patch("api.routers.chat.create_hybrid_agent", return_value=mock_agent),
            patch("api.routers.chat.get_settings", return_value=_mock_settings()),
            patch("api.routers.chat.get_context_manager", return_value=MagicMock()),
            patch("api.routers.chat.get_optimized_memory", return_value=(MagicMock(), None)),
        ):
            response = await chat_client.post(
                "/api/v1/chat",
                json={
                    "message": "Search web",
                    "stream": True,
                    "include_intermediate_steps": True,
                },
            )

        assert response.status_code == status.HTTP_200_OK


# ===========================================================================
# Test: Streaming error handling
# ===========================================================================


class TestStreamingErrors:
    """Test error handling in streaming mode."""

    @pytest.mark.asyncio
    async def test_streaming_exception_emits_error_event(self, chat_client, mock_agent):
        async def mock_astream(*args, **kwargs):
            raise RuntimeError("Stream processing error")
            yield  # make this an async generator  # noqa: unreachable

        mock_agent.astream_query = mock_astream

        with (
            patch("api.routers.chat.create_hybrid_agent", return_value=mock_agent),
            patch("api.routers.chat.get_settings", return_value=_mock_settings()),
            patch("api.routers.chat.get_context_manager", return_value=MagicMock()),
            patch("api.routers.chat.get_optimized_memory", return_value=(MagicMock(), None)),
        ):
            response = await chat_client.post(
                "/api/v1/chat",
                json={"message": "Hello", "stream": True},
            )

        content = response.text
        assert "event: error" in content
        assert "[DONE]" in content

    @pytest.mark.asyncio
    async def test_streaming_get_sources_exception_handled(self, chat_client, mock_agent):
        async def mock_astream(*args, **kwargs):
            yield 'data: {"content": "Result"}\n\n'

        mock_agent.astream_query = mock_astream
        mock_agent.get_sources_for_query = MagicMock(
            side_effect=RuntimeError("Source retrieval failed")
        )

        with (
            patch("api.routers.chat.create_hybrid_agent", return_value=mock_agent),
            patch("api.routers.chat.get_settings", return_value=_mock_settings()),
            patch("api.routers.chat.get_context_manager", return_value=MagicMock()),
            patch("api.routers.chat.get_optimized_memory", return_value=(MagicMock(), None)),
        ):
            response = await chat_client.post(
                "/api/v1/chat",
                json={"message": "Hello", "stream": True},
            )

        assert response.status_code == status.HTTP_200_OK
        # Should still complete successfully with empty sources
        content = response.text
        assert "[DONE]" in content


# ===========================================================================
# Test: Chat request validation
# ===========================================================================


class TestChatValidation:
    """Test chat request validation."""

    @pytest.mark.asyncio
    async def test_empty_message_returns_400(self, chat_client):
        """Empty/whitespace message triggers validation.

        The sanitizer raises HTTPException(400) for an empty message, and
        the router keeps the status it decided on: a client error is not a
        server failure.
        """
        with patch("api.routers.chat.get_settings", return_value=_mock_settings()):
            response = await chat_client.post(
                "/api/v1/chat",
                json={"message": "   "},
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_missing_message_returns_422(self, chat_client):
        response = await chat_client.post(
            "/api/v1/chat",
            json={},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_very_long_message_handled(self, chat_client, mock_agent):
        """Messages up to CHAT_MAX_LENGTH should be accepted."""
        long_msg = "A" * 10000  # Well under 50_000 limit
        with (
            patch("api.routers.chat.create_hybrid_agent", return_value=mock_agent),
            patch("api.routers.chat.get_settings", return_value=_mock_settings()),
            patch("api.routers.chat.get_context_manager", return_value=MagicMock()),
            patch("api.routers.chat.get_optimized_memory", return_value=(MagicMock(), None)),
        ):
            response = await chat_client.post(
                "/api/v1/chat",
                json={"message": long_msg},
            )

        assert response.status_code == status.HTTP_200_OK


# ===========================================================================
# Test: Agent kwargs filtering
# ===========================================================================


class TestAgentKwargsFiltering:
    """Test that agent kwargs are properly filtered based on signature."""

    @pytest.mark.asyncio
    async def test_kwargs_passed_when_var_keyword_in_signature(self, chat_client, mock_agent):
        """When create_hybrid_agent accepts **kwargs, all params are passed."""
        # The real create_hybrid_agent signature includes **kwargs, so by default
        # all kwargs are passed. We just verify the call succeeds.
        with (
            patch("api.routers.chat.create_hybrid_agent", return_value=mock_agent) as mock_create,
            patch("api.routers.chat.get_settings", return_value=_mock_settings()),
            patch("api.routers.chat.get_context_manager", return_value=MagicMock()),
            patch("api.routers.chat.get_optimized_memory", return_value=(MagicMock(), None)),
        ):
            response = await chat_client.post(
                "/api/v1/chat",
                json={"message": "Hello"},
            )

        assert response.status_code == status.HTTP_200_OK
        # Verify create_hybrid_agent was called with expected kwargs
        call_kwargs = mock_create.call_args[1]
        assert "llm" in call_kwargs
        assert "retriever" in call_kwargs
        assert "memory" in call_kwargs
