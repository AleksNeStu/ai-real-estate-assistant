from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.documents import Document

from agents.hybrid_agent import HybridPropertyAgent, SimpleRAGAgent
from agents.query_analyzer import Complexity, QueryAnalysis, QueryIntent, Tool


class TestHybridPropertyAgent:
    @pytest.fixture
    def mock_llm(self):
        llm = MagicMock()
        llm.invoke.return_value = MagicMock(content="Mocked answer")
        return llm

    @pytest.fixture
    def mock_retriever(self):
        retriever = MagicMock()
        retriever.invoke.return_value = [
            Document(page_content="Doc 1", metadata={"id": "1"}),
            Document(page_content="Doc 2", metadata={"id": "2"}),
        ]
        retriever.search_with_filters = MagicMock(
            return_value=[Document(page_content="Filtered Doc 1", metadata={"id": "f1"})]
        )
        retriever.asearch_with_filters = AsyncMock(
            return_value=[Document(page_content="Async Filtered Doc 1", metadata={"id": "af1"})]
        )
        retriever.ainvoke = AsyncMock(
            return_value=[Document(page_content="Async Doc 1", metadata={"id": "a1"})]
        )
        return retriever

    @pytest.fixture
    def agent(self, mock_llm, mock_retriever):
        # Patch creation methods to avoid instantiation validation
        with (
            patch("agents.hybrid_agent.HybridPropertyAgent._create_rag_chain") as mock_rag_create,
            patch("agents.hybrid_agent.HybridPropertyAgent._create_tool_agent") as mock_tool_create,
            patch("agents.hybrid_agent.create_property_tools", return_value=[]),
        ):
            # Setup mock returns
            mock_rag_create.return_value = MagicMock()
            mock_rag_create.return_value.invoke.return_value = {
                "answer": "RAG Answer",
                "source_documents": [],
            }
            # When chain is called directly: chain(inputs) -> returns dict
            mock_rag_create.return_value.return_value = {
                "answer": "RAG Answer",
                "source_documents": [],
            }

            mock_tool_create.return_value = MagicMock()
            mock_tool_create.return_value.invoke.return_value = {"output": "Agent Answer"}

            agent = HybridPropertyAgent(llm=mock_llm, retriever=mock_retriever)

            # Ensure attributes are set (mocks return new mocks)
            agent.rag_chain = mock_rag_create.return_value
            agent.tool_agent = mock_tool_create.return_value

            return agent

    def test_default_memory_output_key_is_answer(self, agent):
        assert getattr(agent.memory, "output_key", None) == "answer"

    def test_retrieve_documents_with_filters(self, agent, mock_retriever):
        """Test retrieval uses search_with_filters when filters are present."""
        query = "apartment in Krakow under 500k"
        analysis = QueryAnalysis(
            query=query,
            intent=QueryIntent.FILTERED_SEARCH,
            complexity=Complexity.MEDIUM,
            extracted_filters={"city": "Krakow", "max_price": 500000},
        )

        docs = agent._retrieve_documents(query, analysis)

        mock_retriever.search_with_filters.assert_called_once()
        args, kwargs = mock_retriever.search_with_filters.call_args
        assert args[0] == query
        assert args[1] == {"city": "Krakow", "max_price": 500000}
        assert docs[0].metadata["id"] == "f1"

    def test_retrieve_documents_without_filters(self, agent, mock_retriever):
        """Test retrieval falls back to get_relevant_documents when no filters."""
        query = "nice apartment"
        analysis = QueryAnalysis(
            query=query,
            intent=QueryIntent.SIMPLE_RETRIEVAL,
            complexity=Complexity.SIMPLE,
            extracted_filters={},
        )

        docs = agent._retrieve_documents(query, analysis)

        mock_retriever.search_with_filters.assert_not_called()
        mock_retriever.invoke.assert_called_once_with(query)
        assert docs[0].metadata["id"] == "1"

    def test_retrieve_documents_respects_k_without_filters(self, agent, mock_retriever):
        query = "nice apartment"
        analysis = QueryAnalysis(
            query=query,
            intent=QueryIntent.SIMPLE_RETRIEVAL,
            complexity=Complexity.SIMPLE,
            extracted_filters={},
        )

        docs = agent._retrieve_documents(query, analysis, k=1)

        mock_retriever.invoke.assert_called_once_with(query)
        assert len(docs) == 1
        assert docs[0].metadata["id"] == "1"

    @pytest.mark.asyncio
    async def test_aretrieve_documents_with_filters(self, agent, mock_retriever):
        query = "apartment in Krakow under 500k"
        analysis = QueryAnalysis(
            query=query,
            intent=QueryIntent.FILTERED_SEARCH,
            complexity=Complexity.MEDIUM,
            extracted_filters={"city": "Krakow", "max_price": 500000},
        )

        docs = await agent._aretrieve_documents(query, analysis)

        mock_retriever.asearch_with_filters.assert_called_once()
        args, kwargs = mock_retriever.asearch_with_filters.call_args
        assert args[0] == query
        assert args[1] == {"city": "Krakow", "max_price": 500000}
        assert docs[0].metadata["id"] == "af1"

    @pytest.mark.asyncio
    async def test_aretrieve_documents_without_filters(self, agent, mock_retriever):
        query = "nice apartment"
        analysis = QueryAnalysis(
            query=query,
            intent=QueryIntent.SIMPLE_RETRIEVAL,
            complexity=Complexity.SIMPLE,
            extracted_filters={},
        )

        docs = await agent._aretrieve_documents(query, analysis)

        mock_retriever.asearch_with_filters.assert_not_called()
        mock_retriever.ainvoke.assert_called_once_with(query)
        assert docs[0].metadata["id"] == "a1"

    @pytest.mark.asyncio
    async def test_aretrieve_documents_respects_k_without_filters(self, agent, mock_retriever):
        query = "nice apartment"
        analysis = QueryAnalysis(
            query=query,
            intent=QueryIntent.SIMPLE_RETRIEVAL,
            complexity=Complexity.SIMPLE,
            extracted_filters={},
        )

        docs = await agent._aretrieve_documents(query, analysis, k=1)

        mock_retriever.ainvoke.assert_called_once_with(query)
        assert len(docs) == 1
        assert docs[0].metadata["id"] == "a1"

    @pytest.mark.asyncio
    async def test_astream_with_agent_uses_async_retrieval(self, agent):
        query = "complex query with filters"
        analysis = QueryAnalysis(
            query=query,
            intent=QueryIntent.ANALYSIS,
            complexity=Complexity.COMPLEX,
            extracted_filters={"city": "Warsaw"},
        )

        async def fake_astream_events(inputs, version="v1"):
            assert "Relevant properties" in inputs["input"]
            assert "Filtered Context" in inputs["input"]
            yield {"event": "on_chat_model_stream", "data": {"chunk": MagicMock(content="Chunk")}}

        with patch.object(
            agent,
            "_aretrieve_documents",
            new=AsyncMock(return_value=[Document(page_content="Filtered Context", metadata={})]),
        ) as mock_retrieve:
            agent.tool_agent.astream_events = fake_astream_events
            chunks = [chunk async for chunk in agent._astream_with_agent(query, analysis)]
            assert chunks == ['{"content": "Chunk"}']
            mock_retrieve.assert_called_once_with(query, analysis, k=3)

    @pytest.mark.asyncio
    async def test_astream_query_rag_only_path(self, agent):
        analysis = QueryAnalysis(
            query="q",
            intent=QueryIntent.SIMPLE_RETRIEVAL,
            complexity=Complexity.SIMPLE,
            tools_needed=[Tool.RAG_RETRIEVAL],
            extracted_filters={},
        )
        agent.analyzer.analyze = MagicMock(return_value=analysis)

        stream_calls = MagicMock()

        async def fake_stream(_query, _analysis):
            stream_calls()
            yield '{"content": "RAG"}'

        with patch.object(agent, "_astream_with_rag", new=fake_stream):
            chunks = [chunk async for chunk in agent.astream_query("q")]
            assert chunks == ['{"content": "RAG"}']
            stream_calls.assert_called_once()

    @pytest.mark.asyncio
    async def test_astream_query_fallbacks_to_sync_result(self, agent):
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

        with patch("agents.hybrid_agent.logger") as mock_logger:
            with patch.object(agent, "_astream_with_agent", new=failing_stream):
                chunks = [chunk async for chunk in agent.astream_query("q")]
                assert chunks == ['{"content": "Fallback"}']
            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_astream_query_hybrid_path(self, agent):
        analysis = QueryAnalysis(
            query="q",
            intent=QueryIntent.FILTERED_SEARCH,
            complexity=Complexity.MEDIUM,
            tools_needed=[Tool.RAG_RETRIEVAL],
            extracted_filters={},
        )
        agent.analyzer.analyze = MagicMock(return_value=analysis)

        async def fake_stream(_query, _analysis):
            yield '{"content": "HYBRID"}'

        with patch.object(agent, "_astream_hybrid", new=fake_stream):
            chunks = [chunk async for chunk in agent.astream_query("q")]
            assert chunks == ['{"content": "HYBRID"}']

    @pytest.mark.asyncio
    async def test_astream_query_yields_error_when_fallback_fails(self, agent):
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

        agent.process_query = MagicMock(side_effect=RuntimeError("fallback failed"))

        with patch("agents.hybrid_agent.logger") as mock_logger:
            with patch.object(agent, "_astream_with_agent", new=failing_stream):
                chunks = [chunk async for chunk in agent.astream_query("q")]
                assert chunks == ['{"error": "boom"}']
            assert mock_logger.error.call_count >= 2

    @pytest.mark.asyncio
    async def test_astream_with_rag_emits_chunks(self, agent):
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
    async def test_astream_with_agent_uses_rag_context(self, agent):
        async def fake_astream_events(inputs, version="v1"):
            assert "Based on this information about properties" in inputs["input"]
            assert "RAG context" in inputs["input"]
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": MagicMock(content="Chunk")},
            }

        agent.tool_agent.astream_events = fake_astream_events
        analysis = QueryAnalysis(
            query="q",
            intent=QueryIntent.SIMPLE_RETRIEVAL,
            complexity=Complexity.SIMPLE,
            extracted_filters={},
        )
        chunks = [
            chunk
            async for chunk in agent._astream_with_agent("q", analysis, rag_context="RAG context")
        ]
        assert chunks == ['{"content": "Chunk"}']

    @pytest.mark.asyncio
    async def test_astream_with_agent_logs_on_retrieval_error(self, agent):
        async def fake_astream_events(_inputs, version="v1"):
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": MagicMock(content="Chunk")},
            }

        agent.tool_agent.astream_events = fake_astream_events
        analysis = QueryAnalysis(
            query="q",
            intent=QueryIntent.FILTERED_SEARCH,
            complexity=Complexity.MEDIUM,
            extracted_filters={"city": "Warsaw"},
        )

        with patch("agents.hybrid_agent.logger") as mock_logger:
            with patch.object(
                agent, "_aretrieve_documents", new=AsyncMock(side_effect=RuntimeError("fail"))
            ):
                chunks = [chunk async for chunk in agent._astream_with_agent("q", analysis)]
                assert chunks == ['{"content": "Chunk"}']
            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_astream_hybrid_returns_rag_answer_for_simple(self, agent):
        analysis = QueryAnalysis(
            query="q",
            intent=QueryIntent.SIMPLE_RETRIEVAL,
            complexity=Complexity.SIMPLE,
            extracted_filters={},
        )
        agent.rag_chain.ainvoke = AsyncMock(return_value={"answer": "RAG Answer"})
        chunks = [chunk async for chunk in agent._astream_hybrid("q", analysis)]
        assert chunks == ['{"content": "RAG Answer"}']

    @pytest.mark.asyncio
    async def test_aretrieve_documents_with_filters_falls_back_without_async_filter(self, agent):
        analysis = QueryAnalysis(
            query="q",
            intent=QueryIntent.FILTERED_SEARCH,
            complexity=Complexity.MEDIUM,
            extracted_filters={"city": "Krakow"},
        )
        retriever = MagicMock(spec_set=["ainvoke"])
        retriever.ainvoke = AsyncMock(
            return_value=[Document(page_content="Async Doc 1", metadata={"id": "fallback"})]
        )
        agent.retriever = retriever

        docs = await agent._aretrieve_documents("q", analysis)

        retriever.ainvoke.assert_called_once_with("q")
        assert docs[0].metadata["id"] == "fallback"

    def test_process_with_agent_uses_filtered_retrieval(self, agent, mock_retriever):
        """Test _process_with_agent calls _retrieve_documents."""
        query = "complex query with filters"
        analysis = QueryAnalysis(
            query=query,
            intent=QueryIntent.ANALYSIS,
            complexity=Complexity.COMPLEX,
            extracted_filters={"city": "Warsaw"},
        )

        # Mock the intent-specific agent so _get_tool_agent_for_intent returns it
        intent_agent_mock = MagicMock()
        intent_agent_mock.invoke.return_value = {"output": "Agent Answer"}

        # Spy on _retrieve_documents
        with (
            patch.object(
                agent,
                "_retrieve_documents",
                return_value=[Document(page_content="Filtered Context", metadata={})],
            ) as mock_retrieve,
            patch.object(
                agent,
                "_get_tool_agent_for_intent",
                return_value=intent_agent_mock,
            ),
        ):
            agent._process_with_agent(query, analysis)

            mock_retrieve.assert_called_once_with(query, analysis, k=3)

            # Check if intent-specific agent was invoked with context
            args, _ = intent_agent_mock.invoke.call_args
            input_text = args[0]["input"]
            assert "Filtered Context" in input_text

    def test_process_with_rag_uses_filtered_retrieval(self, agent, mock_llm):
        """Test _process_with_rag uses manual retrieval + LLM when filters exist."""
        query = "simple filtered query"
        analysis = QueryAnalysis(
            query=query,
            intent=QueryIntent.FILTERED_SEARCH,
            complexity=Complexity.SIMPLE,
            extracted_filters={"rooms": 2},
        )

        with patch.object(
            agent,
            "_retrieve_documents",
            return_value=[Document(page_content="Filtered RAG Doc", metadata={})],
        ) as mock_retrieve:
            result = agent._process_with_rag(query, analysis)

            mock_retrieve.assert_called_once()

            # Should invoke LLM directly, not rag_chain
            agent.rag_chain.assert_not_called()  # Should be .invoke, but we mocked the object
            # Wait, rag_chain is a Mock, so we can check it wasn't called.
            # However, I mocked rag_chain.invoke in fixture?
            # The code calls self.rag_chain({"question": query}) which is __call__
            agent.rag_chain.assert_not_called()

            mock_llm.invoke.assert_called_once()
            assert result["method"] == "rag_filtered"
            assert result["answer"] == "Mocked answer"

    def test_process_hybrid_uses_rag_filtered(self, agent):
        """Test _process_hybrid delegates to _process_with_rag."""
        query = "hybrid query"
        analysis = QueryAnalysis(
            query=query,
            intent=QueryIntent.RECOMMENDATION,
            complexity=Complexity.COMPLEX,
            extracted_filters={"has_pool": True},
        )

        with patch.object(
            agent,
            "_process_with_rag",
            return_value={
                "answer": "RAG Base Answer",
                "source_documents": [],
                "method": "rag_filtered",
            },
        ) as mock_rag:
            agent._process_hybrid(query, analysis)

            mock_rag.assert_called_once_with(query, analysis)

    def test_get_sources_for_query_skips_calculation_intent(self, agent):
        query = "calculate mortgage payment"
        analysis = QueryAnalysis(
            query=query,
            intent=QueryIntent.CALCULATION,
            complexity=Complexity.SIMPLE,
            extracted_filters={},
        )
        agent.analyzer.analyze = MagicMock(return_value=analysis)
        with patch.object(agent, "_retrieve_documents") as mock_retrieve:
            docs = agent.get_sources_for_query(query)
            assert docs == []
            mock_retrieve.assert_not_called()

    def test_get_sources_for_query_uses_retrieve_documents(self, agent):
        query = "apartments in Krakow"
        analysis = QueryAnalysis(
            query=query,
            intent=QueryIntent.FILTERED_SEARCH,
            complexity=Complexity.SIMPLE,
            extracted_filters={"city": "Krakow"},
        )
        agent.analyzer.analyze = MagicMock(return_value=analysis)
        expected = [Document(page_content="Doc", metadata={"id": "x"})]
        with patch.object(agent, "_retrieve_documents", return_value=expected) as mock_retrieve:
            docs = agent.get_sources_for_query(query)
            assert docs == expected
            mock_retrieve.assert_called_once_with(query, analysis, k=5)

    def test_simple_rag_agent_get_sources_for_query_returns_docs(self, mock_llm):
        retriever = MagicMock()
        retriever.invoke.return_value = [
            Document(page_content="Doc 1", metadata={"id": "1"}),
            Document(page_content="Doc 2", metadata={"id": "2"}),
        ]
        with patch(
            "agents.hybrid_agent.ConversationalRetrievalChain.from_llm", return_value=MagicMock()
        ):
            agent = SimpleRAGAgent(llm=mock_llm, retriever=retriever)
        docs = agent.get_sources_for_query("q", k=1)
        assert len(docs) == 1
        assert docs[0].metadata["id"] == "1"

    def test_simple_rag_agent_get_sources_for_query_returns_empty_on_error(self, mock_llm):
        retriever = MagicMock()
        retriever.invoke.side_effect = RuntimeError("fail")
        with patch(
            "agents.hybrid_agent.ConversationalRetrievalChain.from_llm", return_value=MagicMock()
        ):
            agent = SimpleRAGAgent(llm=mock_llm, retriever=retriever)
        assert agent.get_sources_for_query("q") == []
