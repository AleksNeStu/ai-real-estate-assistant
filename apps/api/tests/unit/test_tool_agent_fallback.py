from unittest.mock import MagicMock

try:
    from langchain.agents import AgentExecutor
except ImportError:
    from langchain_classic.agents import AgentExecutor  # type: ignore[no-redef]

import agents.hybrid_agent as hybrid_agent
from ai.buffer_memory import ConversationBufferMemory


def test_tool_agent_falls_back_when_openai_tools_agent_fails(monkeypatch):
    monkeypatch.setattr(
        hybrid_agent,
        "create_openai_tools_agent",
        lambda **_: (_ for _ in ()).throw(RuntimeError("no tool calling")),
    )

    inst = hybrid_agent.HybridPropertyAgent.__new__(hybrid_agent.HybridPropertyAgent)
    inst.llm = MagicMock()
    inst.tools = []
    inst.memory = ConversationBufferMemory(
        memory_key="chat_history", return_messages=True, output_key="answer"
    )
    inst.verbose = False

    result = inst._create_tool_agent()
    assert isinstance(result, AgentExecutor)
