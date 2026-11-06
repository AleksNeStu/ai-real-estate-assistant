"""
Regression test for issue #377: user input must reach the agent unmodified.

The control-character filter used to be a ``bytes`` table passed to
``str.translate()``. Because ``str.translate()`` looks a bytes table up by
ordinal, the table rewrote every code point below 0x3E - spaces, digits and
punctuation - so the agent received mangled queries like
``2\\x97bedroom\\x82apartment``.
"""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.dependencies import get_llm, get_vector_store
from api.main import app
from config.settings import get_settings

client = TestClient(app)

MESSAGE = "2 bedroom apartment under 500000 EUR"


class _CapturingAgent:
    """Agent double that records the message it was asked to answer."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    def process_query(self, message: str) -> dict:
        self.messages.append(message)
        return {"answer": "ok", "sources": []}


def _post_chat(agent: _CapturingAgent, message: str):
    settings = get_settings()
    mock_llm = MagicMock()
    mock_store = MagicMock()
    mock_store.get_retriever.return_value = MagicMock()
    app.dependency_overrides[get_llm] = lambda: mock_llm
    app.dependency_overrides[get_vector_store] = lambda: mock_store
    try:
        with patch("api.routers.chat.create_hybrid_agent", return_value=agent):
            response = client.post(
                "/api/v1/chat",
                json={"message": message},
                headers={"X-API-Key": settings.api_access_key},
            )
    finally:
        app.dependency_overrides = {}
    return response


def test_chat_reaches_the_agent_with_digits_and_spaces_intact():
    agent = _CapturingAgent()

    response = _post_chat(agent, MESSAGE)

    assert response.status_code == 200
    assert agent.messages == [MESSAGE]


def test_chat_reaches_the_agent_with_cjk_digits_intact():
    agent = _CapturingAgent()
    message = "预算是50万人民币"

    response = _post_chat(agent, message)

    assert response.status_code == 200
    assert agent.messages == [message]
