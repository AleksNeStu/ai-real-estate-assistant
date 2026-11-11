"""The tool calls of an answer travel as data (Task #71).

The chat's cards used to be drawn by a parser on the client that read the
agent's stringified steps. The backend now sends the calls as data inside
the stream's meta event - the tool's name, the arguments it was called
with, what it answered - and the parser stays as the fallback.
"""

import json

from utils.tool_calls import build_tool_call, build_tool_calls_from_steps


class _Action:
    """What LangChain's AgentAction carries."""

    def __init__(self, tool, tool_input):
        self.tool = tool
        self.tool_input = tool_input


def test_a_call_carries_the_name_the_arguments_and_the_answer():
    call = build_tool_call("search_properties", {"query": "Kraków"}, "38 matches")

    assert call == {
        "name": "search_properties",
        "args": '{"query": "Kraków"}',
        "result": "38 matches",
    }


def test_a_call_without_a_name_is_not_a_call():
    assert build_tool_call(None, "{}", "result") is None
    assert build_tool_call("   ", "{}", "result") is None
    assert build_tool_call(42, "{}", "result") is None


def test_the_arguments_are_cut_so_one_call_cannot_fill_the_stream():
    call = build_tool_call("search_properties", "x" * 9000, "y" * 9000)

    assert len(call["args"]) < 2100
    assert call["args"].endswith("... (truncated)")
    assert len(call["result"]) < 4100
    assert call["result"].endswith("... (truncated)")


def test_a_secret_in_the_arguments_is_redacted():
    call = build_tool_call("call_tool", {"api_key": "sk-super-secret-value"}, "done")

    assert "sk-super-secret-value" not in call["args"]


def test_the_agents_own_step_becomes_a_call():
    steps = [(_Action("search_properties", {"query": "Kraków"}), "38 matches")]

    assert build_tool_calls_from_steps(steps) == [
        {
            "name": "search_properties",
            "args": '{"query": "Kraków"}',
            "result": "38 matches",
        }
    ]


def test_the_web_agents_step_becomes_a_call():
    steps = [
        {
            "tool": "web_search",
            "args": '{"query": "flats"}',
            "result": "3 pages",
            "sources": [{"content": "a page", "metadata": {"url": "https://example.org"}}],
        }
    ]

    calls = build_tool_calls_from_steps(steps)

    assert calls[0]["name"] == "web_search"
    assert calls[0]["result"] == "3 pages"
    assert calls[0]["sources"][0]["metadata"]["url"] == "https://example.org"


def test_a_stringified_step_is_the_clients_business():
    """The repr of a step is what the client parses - not what we guess at."""
    steps = ["(AgentAction(tool='x', tool_input='{}', log=''), 'y')"]

    assert build_tool_calls_from_steps(steps) == []


def test_a_trace_without_calls_is_an_empty_list():
    assert build_tool_calls_from_steps(None) == []
    assert build_tool_calls_from_steps([]) == []
    assert build_tool_calls_from_steps([{"note": "nothing to see"}]) == []


def test_the_meta_event_carries_the_calls_the_agent_made():
    """The stream's meta event carries the calls as data."""
    from unittest.mock import MagicMock, patch

    from fastapi.testclient import TestClient

    from api.dependencies import get_llm, get_vector_store
    from api.main import app
    from config.settings import get_settings

    class _Agent:
        async def astream_query(self, message: str):
            yield json.dumps(
                {"tool_call": {"name": "search_properties", "args": "{}", "result": "38"}}
            )
            yield json.dumps({"content": "the answer"})

    client = TestClient(app)
    mock_llm = MagicMock()
    mock_store = MagicMock()
    mock_store.get_retriever.return_value = MagicMock()
    app.dependency_overrides[get_llm] = lambda: mock_llm
    app.dependency_overrides[get_vector_store] = lambda: mock_store

    try:
        with patch("api.routers.chat.create_hybrid_agent", return_value=_Agent()):
            with client.stream(
                "POST",
                "/api/v1/chat",
                json={"message": "Hello", "stream": True},
                headers={"X-API-Key": get_settings().api_access_key},
            ) as response:
                body = b"".join(list(response.iter_bytes())).decode("utf-8")

        assert "event: meta" in body
        meta = body.split("event: meta\ndata: ", 1)[1].split("\n\n", 1)[0]
        payload = json.loads(meta)
        assert payload["tool_calls"] == [
            {"name": "search_properties", "args": "{}", "result": "38"}
        ]
        # The answer's text still travels, and the call does not travel twice.
        assert 'data: {"content": "the answer"}' in body
        # The call does not travel as a chunk of its own - only inside the
        # meta event.
        assert '"tool_call":' not in body
    finally:
        app.dependency_overrides = {}
