import asyncio
import json
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from agents.query_analyzer import Complexity, QueryAnalysis, QueryIntent, Tool
from api.dependencies import get_llm, get_vector_store
from api.main import app
from config.settings import get_settings

client = TestClient(app)


def _make_sse_agent(chunks):
    class _Agent:
        async def astream_query(self, message: str):
            for c in chunks:
                await asyncio.sleep(0)
                yield c

    return _Agent()


def test_chat_sse_stream_success():
    settings = get_settings()
    key = settings.api_access_key

    mock_llm = MagicMock()
    mock_store = MagicMock()
    mock_store.get_retriever.return_value = MagicMock()
    app.dependency_overrides[get_llm] = lambda: mock_llm
    app.dependency_overrides[get_vector_store] = lambda: mock_store

    agent = _make_sse_agent(['{"content": "chunk-1"}', '{"content": "chunk-2"}'])

    with patch("api.routers.chat.create_hybrid_agent", return_value=agent):
        with client.stream(
            "POST",
            "/api/v1/chat",
            json={"message": "Hello", "stream": True},
            headers={"X-API-Key": key},
        ) as r:
            assert r.status_code == 200
            ct = r.headers.get("content-type", "")
            assert ct.startswith("text/event-stream")
            body = b"".join(list(r.iter_bytes())).decode("utf-8")
            assert 'data: {"content": "chunk-1"}' in body
            assert 'data: {"content": "chunk-2"}' in body
            assert "event: meta" in body
            assert '"sources"' in body
            assert "data: [DONE]" in body

    app.dependency_overrides = {}


def test_chat_sse_includes_request_id_in_meta_event():
    """Test that request_id is included in SSE meta events for correlation."""
    settings = get_settings()
    key = settings.api_access_key
    test_request_id = "test-req-12345"

    mock_llm = MagicMock()
    mock_store = MagicMock()
    mock_store.get_retriever.return_value = MagicMock()
    app.dependency_overrides[get_llm] = lambda: mock_llm
    app.dependency_overrides[get_vector_store] = lambda: mock_store

    agent = _make_sse_agent([])

    with patch("api.routers.chat.create_hybrid_agent", return_value=agent):
        with client.stream(
            "POST",
            "/api/v1/chat",
            json={"message": "Hello", "stream": True},
            headers={"X-API-Key": key, "X-Request-ID": test_request_id},
        ) as r:
            assert r.status_code == 200
            body = b"".join(list(r.iter_bytes())).decode("utf-8")
            # Check that request_id is in meta event
            assert "event: meta" in body
            assert f'"request_id": "{test_request_id}"' in body

    app.dependency_overrides = {}


def test_chat_sse_error_event_on_streaming_failure():
    """Test that streaming failures send explicit error events with request_id."""
    settings = get_settings()
    key = settings.api_access_key
    test_request_id = "test-req-failed"

    class _FailingAgent:
        async def astream_query(self, message: str):
            await asyncio.sleep(0)
            if False:
                yield ""
            raise RuntimeError("streaming failed")

    mock_llm = MagicMock()
    mock_store = MagicMock()
    mock_store.get_retriever.return_value = MagicMock()
    app.dependency_overrides[get_llm] = lambda: mock_llm
    app.dependency_overrides[get_vector_store] = lambda: mock_store

    agent = _FailingAgent()

    with patch("api.routers.chat.create_hybrid_agent", return_value=agent):
        with client.stream(
            "POST",
            "/api/v1/chat",
            json={"message": "Hello", "stream": True},
            headers={"X-API-Key": key, "X-Request-ID": test_request_id},
        ) as r:
            assert r.status_code == 200
            body = b"".join(list(r.iter_bytes())).decode("utf-8")
            # Check that error event is sent with request_id
            assert "event: error" in body
            assert f'"request_id": "{test_request_id}"' in body
            # The reader gets a sentence they can act on; the provider's own
            # error text stays in the log.
            assert "temporarily unavailable" in body
            assert "streaming failed" not in body
            # Stream should still terminate properly
            assert "data: [DONE]" in body

    app.dependency_overrides = {}


def test_chat_sse_web_path_includes_sanitized_intermediate_steps():
    settings = get_settings()
    key = settings.api_access_key

    mock_llm = MagicMock()
    mock_store = MagicMock()
    mock_store.get_retriever.return_value = MagicMock()
    app.dependency_overrides[get_llm] = lambda: mock_llm
    app.dependency_overrides[get_vector_store] = lambda: mock_store

    analysis = QueryAnalysis(
        query="Hello",
        intent=QueryIntent.GENERAL_QUESTION,
        complexity=Complexity.SIMPLE,
        requires_external_data=True,
        tools_needed=[Tool.WEB_SEARCH],
    )

    class _Analyzer:
        def __init__(self, value):
            self._value = value

        def analyze(self, message):
            return self._value

    class _WebAgent:
        def __init__(self, value, result):
            self.analyzer = _Analyzer(value)
            self._result = result

        def process_query(self, message):
            return self._result

    result = {
        "answer": "From web",
        "sources": [{"content": "Web content", "metadata": {"url": "https://example.com"}}],
        "intermediate_steps": [{"tool": "search", "input": {"api_key": "sk-abc123"}}],
    }
    agent = _WebAgent(analysis, result)

    with patch("api.routers.chat.create_hybrid_agent", return_value=agent):
        with client.stream(
            "POST",
            "/api/v1/chat",
            json={"message": "Hello", "stream": True, "include_intermediate_steps": True},
            headers={"X-API-Key": key},
        ) as r:
            assert r.status_code == 200
            body = b"".join(list(r.iter_bytes())).decode("utf-8")
            lines = [line for line in body.splitlines() if line.strip()]
            meta_line = next(
                line for line in lines if line.startswith("data: {") and '"sources"' in line
            )
            meta = json.loads(meta_line[len("data: ") :])
            assert meta["sources"] == [
                {"content": "Web content", "metadata": {"url": "https://example.com"}}
            ]
            assert meta["sources_truncated"] is False
            assert "intermediate_steps" in meta
            assert "From web" in body
            assert "sk-abc123" not in body
            assert "sk-***" in body
            assert "event: meta" in body
            assert "data: [DONE]" in body

    app.dependency_overrides = {}
