"""The chat's answer is text, whatever shape the provider answered in.

A provider that answers in content blocks - Anthropic-style, and OpenRouter's
free models - put a LIST into `ChatResponse.response`, which is typed as a
string. The free-tier chat answered 500 instead of answering. These tests pin
the shape: the answer that reaches the client is text.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient

from api.dependencies import get_llm, get_vector_store
from api.routers.chat import router as chat_router
from utils.llm_content import content_to_text

BLOCKS = [{"type": "text", "text": "42"}]


# ---------------------------------------------------------------------------
# The helper
# ---------------------------------------------------------------------------


class TestContentToText:
    def test_a_string_is_its_own_text(self):
        assert content_to_text("42") == "42"

    def test_blocks_are_flattened_into_their_text(self):
        assert content_to_text(BLOCKS) == "42"

    def test_several_text_blocks_are_joined(self):
        blocks = [{"type": "text", "text": "two "}, {"type": "text", "text": "words"}]
        assert content_to_text(blocks) == "two words"

    def test_a_block_without_text_carries_no_answer(self):
        blocks = [{"type": "tool_use", "name": "search"}, {"type": "text", "text": "42"}]
        assert content_to_text(blocks) == "42"

    def test_nothing_is_no_text(self):
        assert content_to_text(None) == ""
        assert content_to_text([]) == ""

    def test_a_single_block_as_a_dict_is_its_text(self):
        assert content_to_text({"type": "text", "text": "42"}) == "42"


# ---------------------------------------------------------------------------
# The contract at the router
# ---------------------------------------------------------------------------


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
    return settings


@pytest.fixture
def mock_agent():
    """An agent whose provider answers in content blocks."""
    agent = MagicMock()
    agent.process_query.return_value = {
        "answer": BLOCKS,
        "source_documents": [],
        "method": "rag_only",
    }
    agent.astream_query = AsyncMock()
    agent.analyzer = None
    return agent


@pytest.fixture
async def chat_client():
    """A chat client with the chat router mounted."""
    test_app = FastAPI()
    test_app.include_router(chat_router, prefix="/api/v1")

    test_app.dependency_overrides[get_llm] = lambda: MagicMock()
    test_app.dependency_overrides[get_vector_store] = lambda: MagicMock()

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    test_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_the_answer_reaches_the_client_as_text(chat_client, mock_agent):
    """A provider that answers in blocks must not turn the chat into a 500."""
    with (
        patch("api.routers.chat.create_hybrid_agent", return_value=mock_agent),
        patch("api.routers.chat.get_settings", return_value=_mock_settings()),
        patch("api.routers.chat.get_context_manager", return_value=MagicMock()),
        patch("api.routers.chat.get_optimized_memory", return_value=(MagicMock(), None)),
    ):
        response = await chat_client.post(
            "/api/v1/chat",
            json={"message": "What is 17 plus 25?"},
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data["response"], str)
    assert data["response"] == "42"
