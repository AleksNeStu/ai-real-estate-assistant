from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.documents import Document

from agents.hybrid_agent import HybridPropertyAgent, SimpleRAGAgent
from agents.query_analyzer import Complexity, QueryAnalysis, QueryIntent, Tool


def test_hybrid_property_agent_get_sources_for_query_uses_retrieve_documents():
    llm = MagicMock()
    retriever = MagicMock()

    with (
        patch(
            "agents.hybrid_agent.HybridPropertyAgent._create_rag_chain", return_value=MagicMock()
        ),
        patch(
            "agents.hybrid_agent.HybridPropertyAgent._create_tool_agent", return_value=MagicMock()
        ),
        patch("agents.hybrid_agent.create_property_tools", return_value=[]),
    ):
        agent = HybridPropertyAgent(llm=llm, retriever=retriever)

    analysis = QueryAnalysis(
        query="q",
        intent=QueryIntent.FILTERED_SEARCH,
        complexity=Complexity.SIMPLE,
        extracted_filters={"city": "Krakow"},
    )
    agent.analyzer.analyze = MagicMock(return_value=analysis)
    expected = [Document(page_content="Doc", metadata={"id": "x"})]

    with patch.object(agent, "_retrieve_documents", return_value=expected) as mock_retrieve:
        docs = agent.get_sources_for_query("q", k=3)
        assert docs == expected
        mock_retrieve.assert_called_once_with("q", analysis, k=3)


def test_hybrid_property_agent_get_sources_for_query_skips_calculation_intent():
    llm = MagicMock()
    retriever = MagicMock()

    with (
        patch(
            "agents.hybrid_agent.HybridPropertyAgent._create_rag_chain", return_value=MagicMock()
        ),
        patch(
            "agents.hybrid_agent.HybridPropertyAgent._create_tool_agent", return_value=MagicMock()
        ),
        patch("agents.hybrid_agent.create_property_tools", return_value=[]),
    ):
        agent = HybridPropertyAgent(llm=llm, retriever=retriever)

    analysis = QueryAnalysis(
        query="q",
        intent=QueryIntent.CALCULATION,
        complexity=Complexity.SIMPLE,
        extracted_filters={},
    )
    agent.analyzer.analyze = MagicMock(return_value=analysis)
    assert agent.get_sources_for_query("q") == []


def test_simple_rag_agent_get_sources_for_query_returns_empty_on_error():
    retriever = MagicMock()
    retriever.invoke.side_effect = RuntimeError("fail")
    with patch(
        "agents.hybrid_agent.ConversationalRetrievalChain.from_llm", return_value=MagicMock()
    ):
        agent = SimpleRAGAgent(llm=MagicMock(), retriever=retriever)
    assert agent.get_sources_for_query("q") == []


@pytest.mark.asyncio
async def test_hybrid_property_agent_astream_query_hybrid_path():
    llm = MagicMock()
    retriever = MagicMock()
    rag_chain = MagicMock()
    tool_agent = MagicMock()

    with (
        patch("agents.hybrid_agent.HybridPropertyAgent._create_rag_chain", return_value=rag_chain),
        patch(
            "agents.hybrid_agent.HybridPropertyAgent._create_tool_agent", return_value=tool_agent
        ),
        patch("agents.hybrid_agent.create_property_tools", return_value=[]),
    ):
        agent = HybridPropertyAgent(llm=llm, retriever=retriever)

    analysis = QueryAnalysis(
        query="q",
        intent=QueryIntent.FILTERED_SEARCH,
        complexity=Complexity.MEDIUM,
        tools_needed=[Tool.RAG_RETRIEVAL],
        extracted_filters={},
    )
    agent.analyzer.analyze = MagicMock(return_value=analysis)
    agent.rag_chain.ainvoke = AsyncMock(return_value={"answer": "RAG Answer"})

    chunks = [chunk async for chunk in agent.astream_query("q")]
    assert chunks == ['{"content": "RAG Answer"}']


@pytest.mark.asyncio
async def test_hybrid_property_agent_astream_query_fallbacks():
    llm = MagicMock()
    retriever = MagicMock()
    rag_chain = MagicMock()
    tool_agent = MagicMock()

    with (
        patch("agents.hybrid_agent.HybridPropertyAgent._create_rag_chain", return_value=rag_chain),
        patch(
            "agents.hybrid_agent.HybridPropertyAgent._create_tool_agent", return_value=tool_agent
        ),
        patch("agents.hybrid_agent.create_property_tools", return_value=[]),
    ):
        agent = HybridPropertyAgent(llm=llm, retriever=retriever)

    analysis = QueryAnalysis(
        query="q",
        intent=QueryIntent.ANALYSIS,
        complexity=Complexity.COMPLEX,
        extracted_filters={},
    )
    agent.analyzer.analyze = MagicMock(return_value=analysis)

    async def failing_stream(*_args, **_kwargs):
        raise RuntimeError("boom")
        yield '{"content": "never"}'

    agent.process_query = MagicMock(return_value={"answer": "Fallback"})

    with patch.object(agent, "_astream_with_agent", new=failing_stream):
        chunks = [chunk async for chunk in agent.astream_query("q")]
        assert chunks == ['{"content": "Fallback"}']


@pytest.mark.asyncio
async def test_hybrid_property_agent_astream_with_rag_emits_chunk():
    llm = MagicMock()
    retriever = MagicMock()
    rag_chain = MagicMock()
    tool_agent = MagicMock()

    with (
        patch("agents.hybrid_agent.HybridPropertyAgent._create_rag_chain", return_value=rag_chain),
        patch(
            "agents.hybrid_agent.HybridPropertyAgent._create_tool_agent", return_value=tool_agent
        ),
        patch("agents.hybrid_agent.create_property_tools", return_value=[]),
    ):
        agent = HybridPropertyAgent(llm=llm, retriever=retriever)

    async def fake_astream_events(_inputs, version="v1"):
        yield {
            "event": "on_chat_model_stream",
            "data": {"chunk": MagicMock(content="RAG Chunk")},
        }

    agent.rag_chain.astream_events = fake_astream_events
    analysis = QueryAnalysis(
        query="q",
        intent=QueryIntent.SIMPLE_RETRIEVAL,
        complexity=Complexity.SIMPLE,
        extracted_filters={},
    )

    chunks = [chunk async for chunk in agent._astream_with_rag("q", analysis)]
    assert chunks == ['{"content": "RAG Chunk"}']


@pytest.mark.asyncio
async def test_hybrid_property_agent_aretrieve_documents_with_filters():
    llm = MagicMock()
    retriever = MagicMock()
    retriever.asearch_with_filters = AsyncMock(
        return_value=[Document(page_content="Filtered", metadata={"id": "f1"})]
    )
    rag_chain = MagicMock()
    tool_agent = MagicMock()

    with (
        patch("agents.hybrid_agent.HybridPropertyAgent._create_rag_chain", return_value=rag_chain),
        patch(
            "agents.hybrid_agent.HybridPropertyAgent._create_tool_agent", return_value=tool_agent
        ),
        patch("agents.hybrid_agent.create_property_tools", return_value=[]),
    ):
        agent = HybridPropertyAgent(llm=llm, retriever=retriever)

    analysis = QueryAnalysis(
        query="q",
        intent=QueryIntent.FILTERED_SEARCH,
        complexity=Complexity.MEDIUM,
        extracted_filters={"city": "Krakow"},
    )

    docs = await agent._aretrieve_documents("q", analysis)
    assert docs[0].metadata["id"] == "f1"
