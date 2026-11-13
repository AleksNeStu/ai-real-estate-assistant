"""
The assistant reads the buyer's memory back (Task #80).

The invariant under test: a buyer with no facts gets EXACTLY the prompt they
got before the memory existed - not nearly, not a prompt with an empty header.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.retrievers import BaseRetriever
from pydantic import Field

from agents.hybrid_agent import HybridPropertyAgent
from agents.intent_prompts import (
    BUYER_MEMORY_HEADER,
    BUYER_MEMORY_MAX_CHARS,
    BUYER_MEMORY_MAX_FACTS,
    build_buyer_memory_block,
)
from agents.query_analyzer import Complexity, QueryAnalysis, QueryIntent

try:
    from langchain.chains import ConversationalRetrievalChain
except ImportError:  # pragma: no cover - the langchain 1.x layout
    from langchain_classic.chains import ConversationalRetrievalChain


class RecordingChatModel(GenericFakeChatModel):
    """A chat model that keeps every prompt it was given."""

    recorded: list = Field(default_factory=list)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.recorded.append(messages)
        return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)


class StubRetriever(BaseRetriever):
    """A retriever that always returns the same document."""

    docs: list = Field(default_factory=list)

    def _get_relevant_documents(self, query, *, run_manager=None):
        return self.docs


def make_facts(*pairs):
    """Build facts shaped like the ones the buyer memory service returns."""
    return [SimpleNamespace(kind=kind, content=content) for kind, content in pairs]


def make_agent(llm, retriever):
    """Build an agent without touching the real chain and tool factories."""
    with (
        patch("agents.hybrid_agent.HybridPropertyAgent._create_rag_chain"),
        patch("agents.hybrid_agent.HybridPropertyAgent._create_tool_agent"),
        patch("agents.hybrid_agent.create_property_tools", return_value=[]),
    ):
        return HybridPropertyAgent(llm=llm, retriever=retriever)


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content="Mocked answer")
    return llm


@pytest.fixture
def mock_retriever():
    retriever = MagicMock()
    retriever.invoke.return_value = [Document(page_content="Listing A", metadata={"id": "1"})]
    retriever.search_with_filters.return_value = [
        Document(page_content="Filtered Listing A", metadata={"id": "f1"})
    ]
    return retriever


@pytest.fixture
def agent(mock_llm, mock_retriever):
    return make_agent(mock_llm, mock_retriever)


@pytest.fixture
def memory_block():
    return build_buyer_memory_block(
        make_facts(
            ("budget", "up to 500000 EUR"),
            ("ruled_out_area", "the city centre"),
        )
    )


@pytest.fixture
def filtered_analysis():
    return QueryAnalysis(
        query="apartment in Krakow under 500k",
        intent=QueryIntent.FILTERED_SEARCH,
        complexity=Complexity.SIMPLE,
        extracted_filters={"city": "Krakow", "max_price": 500000},
    )


@pytest.fixture
def recording_llm():
    return RecordingChatModel(
        messages=iter([AIMessage(content="Mocked answer") for _ in range(50)])
    )


@pytest.fixture
def chain_agent(recording_llm):
    """An agent whose RAG chain is a real one, so its prompt can be read."""
    retriever = StubRetriever(docs=[Document(page_content="Listing A", metadata={"id": "1"})])
    agent = make_agent(recording_llm, retriever)
    agent.rag_chain = ConversationalRetrievalChain.from_llm(
        llm=recording_llm,
        retriever=retriever,
        memory=agent.memory,
        return_source_documents=True,
    )
    return agent


class TestTheMemoryBlock:
    """The block itself: what it says and how big it is allowed to be."""

    def test_a_buyer_with_no_facts_gets_no_block(self):
        assert build_buyer_memory_block([]) == ""
        assert build_buyer_memory_block(None) == ""

    def test_the_block_says_what_the_buyer_already_told_us(self, memory_block):
        assert memory_block.startswith(BUYER_MEMORY_HEADER)
        assert "up to 500000 EUR" in memory_block

    def test_the_block_stays_within_its_cap(self):
        facts = make_facts(*[("note", f"fact number {i} " + "x" * 500) for i in range(30)])

        block = build_buyer_memory_block(facts)

        assert len(block) <= BUYER_MEMORY_MAX_CHARS
        lines = [line for line in block.splitlines() if line.startswith("- ")]
        assert len(lines) <= BUYER_MEMORY_MAX_FACTS

    def test_a_single_huge_fact_stays_within_the_cap(self):
        block = build_buyer_memory_block(make_facts(("note", "y" * 5000)))

        assert len(block) <= BUYER_MEMORY_MAX_CHARS

    def test_the_agent_caps_a_block_it_is_handed(self):
        agent = make_agent(MagicMock(), MagicMock())

        capped = agent._memory_section("z" * 5000)

        assert len(capped) <= BUYER_MEMORY_MAX_CHARS


class TestTheFactsReachThePrompt:
    """The facts the buyer gave us are in the prompt the agent builds."""

    def test_the_filtered_rag_prompt_carries_the_facts(self, agent, mock_llm, memory_block):
        analysis = QueryAnalysis(
            query="apartment in Krakow under 500k",
            intent=QueryIntent.FILTERED_SEARCH,
            complexity=Complexity.SIMPLE,
            extracted_filters={"city": "Krakow"},
        )

        agent._process_with_rag(
            "apartment in Krakow under 500k", analysis, buyer_memory=memory_block
        )

        prompt = mock_llm.invoke.call_args[0][0]
        assert "up to 500000 EUR" in prompt
        assert "the city centre" in prompt
        assert BUYER_MEMORY_HEADER in prompt

    def test_the_tool_agent_prompt_carries_the_facts(self, agent, memory_block):
        analysis = QueryAnalysis(
            query="compare these two flats",
            intent=QueryIntent.COMPARISON,
            complexity=Complexity.COMPLEX,
            extracted_filters={"city": "Warsaw"},
        )
        tool_agent = MagicMock()
        tool_agent.invoke.return_value = {"output": "Agent Answer"}

        with patch.object(agent, "_get_tool_agent_for_intent", return_value=tool_agent):
            agent._process_with_agent(
                "compare these two flats", analysis, buyer_memory=memory_block
            )

        input_text = tool_agent.invoke.call_args[0][0]["input"]
        assert "up to 500000 EUR" in input_text
        assert "the city centre" in input_text

    def test_the_standard_rag_chain_prompt_carries_the_facts(self, chain_agent, memory_block):
        analysis = QueryAnalysis(
            query="q",
            intent=QueryIntent.SIMPLE_RETRIEVAL,
            complexity=Complexity.SIMPLE,
            extracted_filters={},
        )

        chain_agent._process_with_rag("q", analysis, buyer_memory=memory_block)

        messages = chain_agent.llm.recorded[-1]
        prompt_text = "\n".join(str(message.content) for message in messages)
        assert "up to 500000 EUR" in prompt_text
        # The retrieved document is still there - the memory did not replace it.
        assert "Listing A" in prompt_text

    @pytest.mark.asyncio
    async def test_the_streaming_prompt_carries_the_facts(self, agent, memory_block):
        analysis = QueryAnalysis(
            query="compare these two flats",
            intent=QueryIntent.COMPARISON,
            complexity=Complexity.COMPLEX,
            extracted_filters={},
        )
        captured = {}

        async def fake_stream(inputs, version="v1"):
            captured["input"] = inputs["input"]
            yield {"event": "on_chat_model_stream", "data": {"chunk": MagicMock(content="Chunk")}}

        agent.tool_agent.astream_events = fake_stream

        chunks = [
            chunk
            async for chunk in agent._astream_with_agent(
                "compare these two flats", analysis, buyer_memory=memory_block
            )
        ]

        assert chunks == ['{"content": "Chunk"}']
        assert "up to 500000 EUR" in captured["input"]


class TestTheEmptyMemoryChangesNothing:
    """A buyer with no facts gets exactly the prompt they got today."""

    def test_the_filtered_rag_prompt_is_byte_for_byte_the_same(self, agent, mock_llm):
        analysis = QueryAnalysis(
            query="apartment in Krakow under 500k",
            intent=QueryIntent.FILTERED_SEARCH,
            complexity=Complexity.SIMPLE,
            extracted_filters={"city": "Krakow"},
        )
        expected = (
            "Answer the question based only on the following context:\n\n"
            "Filtered Listing A\n\n"
            "Question: apartment in Krakow under 500k"
        )

        agent._process_with_rag("apartment in Krakow under 500k", analysis)
        without_memory = mock_llm.invoke.call_args[0][0]

        mock_llm.invoke.reset_mock()
        agent._process_with_rag("apartment in Krakow under 500k", analysis, buyer_memory="")
        with_empty_memory = mock_llm.invoke.call_args[0][0]

        assert without_memory == expected
        assert with_empty_memory == expected

    def test_the_tool_agent_prompt_is_byte_for_byte_the_same(self, agent):
        analysis = QueryAnalysis(
            query="compare these two flats",
            intent=QueryIntent.COMPARISON,
            complexity=Complexity.COMPLEX,
            extracted_filters={"city": "Warsaw"},
        )
        tool_agent = MagicMock()
        tool_agent.invoke.return_value = {"output": "Agent Answer"}

        with patch.object(agent, "_get_tool_agent_for_intent", return_value=tool_agent):
            agent._process_with_agent("compare these two flats", analysis)
            without_memory = tool_agent.invoke.call_args[0][0]["input"]

            agent._process_with_agent("compare these two flats", analysis, buyer_memory="")
            with_empty_memory = tool_agent.invoke.call_args[0][0]["input"]

        assert without_memory == with_empty_memory
        assert without_memory.startswith("compare these two flats\n\nRelevant properties:")

    def test_the_standard_rag_chain_prompt_is_byte_for_byte_the_same(self, chain_agent):
        analysis = QueryAnalysis(
            query="q",
            intent=QueryIntent.SIMPLE_RETRIEVAL,
            complexity=Complexity.SIMPLE,
            extracted_filters={},
        )

        chain_agent._process_with_rag("q", analysis)
        without_memory = list(chain_agent.llm.recorded[-1])

        # The chain keeps the conversation, so the second run starts empty.
        chain_agent.clear_memory()
        chain_agent._process_with_rag("q", analysis, buyer_memory="")
        with_empty_memory = list(chain_agent.llm.recorded[-1])

        assert [m.content for m in without_memory] == [m.content for m in with_empty_memory]

    def test_process_query_without_memory_builds_the_old_prompt(self, agent, mock_llm):
        analysis = QueryAnalysis(
            query="apartment in Krakow under 500k",
            intent=QueryIntent.FILTERED_SEARCH,
            complexity=Complexity.SIMPLE,
            extracted_filters={"city": "Krakow"},
        )
        agent.analyzer.analyze = MagicMock(return_value=analysis)

        with patch.object(agent, "_determine_route", return_value="rag"):
            agent.process_query("apartment in Krakow under 500k")
            without_memory = mock_llm.invoke.call_args[0][0]

            mock_llm.invoke.reset_mock()
            agent.process_query("apartment in Krakow under 500k", buyer_memory="")
            with_empty_memory = mock_llm.invoke.call_args[0][0]

        assert without_memory == with_empty_memory
        assert "What the buyer has already told us" not in without_memory
