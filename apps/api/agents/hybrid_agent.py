"""
Hybrid agent system combining RAG and tool-based agents.

This module provides intelligent orchestration between:
- Simple RAG for straightforward queries
- Tool-based agent for complex tasks
- Hybrid approach combining both

Enhanced with:
- Context-aware classification using session history
- Intent-specific prompts for better responses
- Classification metrics logging for quality tracking
- Confidence-based routing decisions
"""

import json
import logging
import time
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional, cast

from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from langchain_core.retrievers import BaseRetriever

from core.security_utils import sanitize_for_log

try:
    from langchain.agents import AgentExecutor, create_openai_tools_agent
    from langchain.chains import ConversationalRetrievalChain
except ImportError:
    from langchain_classic.agents import (  # type: ignore[no-redef]
        AgentExecutor,
        create_openai_tools_agent,
    )
    from langchain_classic.chains import ConversationalRetrievalChain  # type: ignore[no-redef]

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain_core.tools import BaseTool

from agents.classification_metrics import (
    ClassificationMetrics,
    init_metrics_db,
    log_classification_metrics,
)
from agents.intent_prompts import BUYER_MEMORY_MAX_CHARS, get_system_prompt_for_intent
from agents.query_analyzer import (
    Complexity,
    QueryAnalysis,
    QueryAnalyzer,
    QueryIntent,
    RoutingThresholds,
    Tool,
)
from agents.web_research_agent import WebResearchAgent, WebResearchConfig
from ai.buffer_memory import ConversationBufferMemory
from tools.property_tools import create_property_tools
from utils.tool_calls import build_tool_call

logger = logging.getLogger(__name__)


class HybridPropertyAgent:
    """
    Hybrid agent that intelligently routes queries to RAG or tool-based processing.

    This agent:
    1. Analyzes incoming queries
    2. Routes simple queries to RAG
    3. Routes complex queries to tool-based agent
    4. Combines both approaches when needed
    """

    def __init__(
        self,
        llm: BaseChatModel,
        retriever: BaseRetriever,
        memory: Optional[ConversationBufferMemory] = None,
        tools: Optional[List[BaseTool]] = None,
        internet_enabled: bool = False,
        searxng_url: Optional[str] = None,
        web_search_max_results: int = 5,
        web_fetch_timeout_seconds: float = 10.0,
        web_fetch_max_bytes: int = 300_000,
        web_allowlist_domains: Optional[List[str]] = None,
        verbose: bool = False,
    ):
        """
        Initialize hybrid agent.

        Args:
            llm: Language model
            retriever: Vector store retriever
            memory: Conversation memory
            tools: List of tools (defaults to property tools)
            verbose: Enable verbose output
        """
        self.llm = llm
        self.retriever = retriever
        self.memory = memory or ConversationBufferMemory(
            memory_key="chat_history", return_messages=True, output_key="answer"
        )

        # Try to extract vector_store from retriever to enable tool actions
        vector_store = getattr(retriever, "vector_store", None)
        self.tools = tools or create_property_tools(vector_store=vector_store, llm=llm)

        self.verbose = verbose
        self.internet_enabled = bool(internet_enabled)
        self.searxng_url = str(searxng_url).strip() if searxng_url else None
        self.web_search_max_results = int(web_search_max_results)
        self.web_fetch_timeout_seconds = float(web_fetch_timeout_seconds)
        self.web_fetch_max_bytes = int(web_fetch_max_bytes)
        self.web_allowlist_domains = list(web_allowlist_domains) if web_allowlist_domains else []

        # Initialize query analyzer
        self.analyzer = QueryAnalyzer()

        # Initialize metrics database for classification tracking
        try:
            init_metrics_db()
        except Exception as e:
            logger.warning("Failed to initialize metrics database: %s", sanitize_for_log(e))

        # Cache for intent-specific tool agents
        self._tool_agent_cache: Dict[QueryIntent, AgentExecutor] = {}

        # Initialize RAG chain
        self.rag_chain = self._create_rag_chain()

        # Initialize default tool agent
        self.tool_agent = self._create_tool_agent()

    def _create_rag_chain(self) -> ConversationalRetrievalChain:
        """Create RAG chain for simple queries."""
        return ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self.retriever,
            memory=self.memory,
            return_source_documents=True,
            verbose=self.verbose,
        )

    @staticmethod
    def _join_prompt_sections(*sections: Optional[str]) -> str:
        """
        Join prompt sections with a blank line between them.

        An empty section is dropped, so a buyer with no memory gets exactly
        the prompt that was built before the memory existed.
        """
        return "\n\n".join(section for section in sections if section)

    @staticmethod
    def _memory_section(buyer_memory: Optional[str]) -> str:
        """
        The buyer's memory block, capped so it can never crowd the listings.

        Args:
            buyer_memory: The already-assembled block, or nothing.

        Returns:
            The block, or an empty string when there is no memory.
        """
        if not buyer_memory:
            return ""
        block = buyer_memory[:BUYER_MEMORY_MAX_CHARS]
        if len(buyer_memory) > BUYER_MEMORY_MAX_CHARS:
            # Never leave half a fact behind.
            cut = block.rfind("\n")
            if cut > 0:
                block = block[:cut]
        return block

    def _rag_chain_for(self, buyer_memory: Optional[str]):
        """
        The RAG chain to answer with, carrying the buyer's memory.

        The chain owns its own prompt, so the memory is added to the combine
        step - a copy of the chain whose answer prompt carries the block. The
        retrieved documents are untouched.

        Args:
            buyer_memory: The already-assembled block, or nothing.

        Returns:
            The chain to use. Without memory it is the chain itself, unchanged.
        """
        block = self._memory_section(buyer_memory)
        if not block:
            return self.rag_chain

        combine = getattr(self.rag_chain, "combine_docs_chain", None)
        llm_chain = getattr(combine, "llm_chain", None)
        prompt = getattr(llm_chain, "prompt", None)
        if llm_chain is None or prompt is None:
            logger.warning("RAG chain does not expose its prompt - memory not carried")
            return self.rag_chain

        new_prompt = self._prompt_with_memory(prompt, block)
        new_combine = combine.copy(
            update={"llm_chain": llm_chain.copy(update={"prompt": new_prompt})}
        )
        return self.rag_chain.copy(update={"combine_docs_chain": new_combine})

    @staticmethod
    def _prompt_with_memory(prompt, memory: str):
        """
        A copy of the chain's prompt with the buyer's memory added to it.

        Args:
            prompt: The prompt the chain owns.
            memory: The buyer's memory block.

        Returns:
            The prompt to use. The original is never modified.
        """
        if isinstance(prompt, ChatPromptTemplate):
            return ChatPromptTemplate.from_messages([*prompt.messages, ("system", memory)])
        if isinstance(prompt, PromptTemplate):
            # The memory becomes part of the template, so its braces are escaped.
            safe_memory = memory.replace("{", "{{").replace("}", "}}")
            return PromptTemplate(
                template=f"{safe_memory}\n\n{prompt.template}",
                input_variables=list(prompt.input_variables),
                partial_variables=dict(prompt.partial_variables),
            )
        logger.warning("Unsupported prompt type for the buyer memory - memory not carried")
        return prompt

    def _create_tool_agent(self, intent: Optional[QueryIntent] = None) -> AgentExecutor:
        """Create tool-based agent for complex queries.

        Args:
            intent: Optional intent to select intent-specific system prompt.
                   If None, uses default generic prompt.
        """

        # Get intent-specific system prompt or use default
        if intent:
            intent_prompt = get_system_prompt_for_intent(intent)
            base_prompt = f"""{intent_prompt}

Scope:
- Answer questions about properties, real estate markets, mortgages, financing, negotiation, neighborhood/location insights, and related decision support.
- If the user asks for something unrelated to real estate (e.g. cooking, medical, legal outside real estate context), refuse briefly and steer back to real estate.

Your capabilities:
- Search property database for listings
- Calculate mortgage payments and costs
- Compare properties side-by-side
- Analyze prices and market trends
- Evaluate locations and neighborhoods

When answering:
1. Use tools when needed for calculations or analysis
2. Provide specific numbers and facts
3. Explain your reasoning
4. Be concise but thorough
5. Always cite sources when using property data

Context from property database will be provided when relevant."""
        else:
            base_prompt = """You are a specialized Real Estate Assistant.

Scope:
- Answer questions about properties, real estate markets, mortgages, financing, negotiation, neighborhood/location insights, and related decision support.
- If the user asks for something unrelated to real estate (e.g. cooking, medical, legal outside real estate context), refuse briefly and steer back to real estate.

Your capabilities:
- Search property database for listings
- Calculate mortgage payments and costs
- Compare properties side-by-side
- Analyze prices and market trends
- Evaluate locations and neighborhoods

When answering:
1. Use tools when needed for calculations or analysis
2. Provide specific numbers and facts
3. Explain your reasoning
4. Be concise but thorough
5. Always cite sources when using property data

Context from property database will be provided when relevant."""

        # Create prompt template for tool agent
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", base_prompt),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        try:
            if create_openai_tools_agent is None:
                raise ImportError("create_openai_tools_agent not available")
            agent = create_openai_tools_agent(llm=self.llm, tools=self.tools, prompt=prompt)
            return AgentExecutor(
                agent=agent,
                tools=self.tools,
                memory=self.memory,
                verbose=self.verbose,
                return_intermediate_steps=True,
            )
        except Exception as e:
            # Fallback for older LangChain versions or missing function
            logger.warning("openai_tools_agent not available, falling back to react_agent: %s", e)
            from langchain_core.prompts import PromptTemplate

            try:
                from langchain.agents import create_react_agent
            except ImportError:
                from langchain_classic.agents import create_react_agent  # type: ignore[no-redef]

            # nosemgrep: langchain.prompt-injection - template is static, no user input
            prompt = PromptTemplate.from_template(  # type: ignore[assignment]
                """You are a specialized Real Estate Assistant.

Scope:
- Answer questions about properties, real estate markets, mortgages, financing, negotiation, neighborhood/location insights, and related decision support.
- If the user asks for something unrelated to real estate (e.g. cooking, medical, legal outside real estate context), refuse briefly and steer back to real estate.

Your capabilities:
- Search property database for listings
- Calculate mortgage payments and costs
- Compare properties side-by-side
- Analyze prices and market trends
- Evaluate locations and neighborhoods

When answering:
1. Use tools when needed for calculations or analysis
2. Provide specific numbers and facts
3. Explain your reasoning
4. Be concise but thorough
5. Always cite sources when using property data

Context from property database will be provided when relevant.

{tools}

Use a json blob to specify a tool by providing an action key (tool name) and an action_input key (tool input).

Valid "action" values: "Final Answer" or {tool_names}

Provide only ONE action per $JSON_BLOB, as shown:

```
{{
  "action": $TOOL_NAME,
  "action_input": $INPUT
}}
```

Follow this format:

Question: the input question you must answer
Thought: you should always think about what to do
Action:
```
$JSON_BLOB
```
Observation: the result of the action
... (this Thought/Action/Observation can repeat N times)
Thought: I now know the final answer
Action:
```
{{
  "action": "Final Answer",
  "action_input": "Final response to human"
}}
```

Begin!

Question: {input}
Thought: {agent_scratchpad}"""
            )

            agent = create_react_agent(llm=self.llm, tools=self.tools, prompt=prompt)
            return AgentExecutor(
                agent=agent,
                tools=self.tools,
                memory=self.memory,
                verbose=self.verbose,
                return_intermediate_steps=True,
            )

    def _get_tool_agent_for_intent(self, intent: QueryIntent) -> AgentExecutor:
        """Get or create a tool agent with intent-specific prompts.

        Uses caching to avoid recreating agents for the same intent.

        Args:
            intent: The query intent to get agent for

        Returns:
            AgentExecutor configured with intent-specific prompt
        """
        if intent not in self._tool_agent_cache:
            self._tool_agent_cache[intent] = self._create_tool_agent(intent)
        return self._tool_agent_cache[intent]

    def _domain_guard(self, query: str) -> Optional[Dict[str, Any]]:
        q = (query or "").strip()
        ql = q.lower()
        if not q:
            return None

        capability_markers = [
            "what can you do",
            "how can you help",
            "what are your capabilities",
            "what are the possibilities",
            "help me",
            "what can i ask",
            "что ты умеешь",
            "как ты можешь помочь",
            "какие возможности",
            "что ты можешь",
        ]
        if any(m in ql for m in capability_markers):
            internet_hint = (
                "Web research is enabled: I can search the web and cite sources."
                if self.internet_enabled
                else "Web research is currently disabled: I won't use the internet unless it is enabled."
            )
            answer = (
                "I'm a specialized Real Estate Assistant. I can help with:\n"
                "- Finding and filtering listings (city, price, rooms, amenities)\n"
                "- Comparing properties and explaining tradeoffs\n"
                "- Mortgage calculations and affordability scenarios\n"
                "- Market questions (pricing, trends) using either your data or web sources when enabled\n"
                "- Drafting messages to agents/landlords and negotiation checklists\n\n"
                f"{internet_hint}"
            )
            try:
                self.memory.save_context({"input": q}, {"answer": answer})
            except Exception as e:
                logger.warning("Failed to save capabilities response to memory: %s", e)
            return {
                "answer": answer,
                "source_documents": [],
                "method": "capabilities",
                "intent": QueryIntent.GENERAL_QUESTION.value,
            }

        out_of_domain_markers = [
            "recipe",
            "cook",
            "cooking",
            "bake",
            "cookie",
            "cake",
            "pizza",
            "пирож",
            "рецепт",
            "готов",
            "печь",
        ]
        if any(m in ql for m in out_of_domain_markers):
            answer = (
                "I can't help with that because I'm specialized in real estate.\n"
                "Ask me about finding a property, comparing options, mortgages, locations, or market conditions."
            )
            try:
                self.memory.save_context({"input": q}, {"answer": answer})
            except Exception as e:
                logger.warning("Failed to save out-of-domain response to memory: %s", e)
            return {
                "answer": answer,
                "source_documents": [],
                "method": "out_of_domain",
                "intent": QueryIntent.GENERAL_QUESTION.value,
            }

        return None

    def process_query(
        self,
        query: str,
        return_analysis: bool = False,
        session_id: Optional[str] = None,
        session_history: Optional[List[Any]] = None,
        buyer_memory: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process a query using the hybrid approach.

        Args:
            query: User query
            return_analysis: Whether to include query analysis in response
            session_id: Optional session ID for metrics tracking
            session_history: Optional list of recent chat messages for context
            buyer_memory: Optional block of what the buyer has already told
                us, already assembled by the caller. Without it the prompt is
                exactly the one this agent built before the memory existed.

        Returns:
            Dictionary with answer, sources, and optional analysis
        """
        start_time = time.time()

        guard = self._domain_guard(query)
        if guard:
            if return_analysis:
                guard["analysis"] = self.analyzer.analyze(query).dict()
            return guard

        # Use context-aware classification if session history provided
        if session_history:
            analysis = self.analyzer.analyze_with_context(query, session_history=session_history)
        else:
            analysis = self.analyzer.analyze(query)

        processing_time_ms = (time.time() - start_time) * 1000

        if self.internet_enabled and (
            analysis.requires_external_data or Tool.WEB_SEARCH in analysis.tools_needed
        ):
            result = self._process_with_web_search(query, analysis)
            if return_analysis:
                result["analysis"] = analysis.dict()
            self._log_metrics(
                analysis=analysis,
                session_id=session_id,
                query=query,
                processing_time_ms=processing_time_ms,
                route_taken="web_search",
            )
            return result
        if (
            analysis.requires_external_data or Tool.WEB_SEARCH in analysis.tools_needed
        ) and not self.internet_enabled:
            result = {
                "answer": (
                    "This question likely requires up-to-date web data, but internet tools are disabled. "
                    "Enable INTERNET_ENABLED and start the search service profile to use web search."
                ),
                "source_documents": [],
                "method": "web_search_disabled",
                "intent": analysis.intent.value,
            }
            if return_analysis:
                result["analysis"] = analysis.dict()
            self._log_metrics(
                analysis=analysis,
                session_id=session_id,
                query=query,
                processing_time_ms=processing_time_ms,
                route_taken="web_search_disabled",
            )
            return result

        if self.verbose:
            logger.info("Query Analysis: %s", analysis.reasoning)
            logger.info("Confidence: %.2f", analysis.confidence)
            logger.info("Should use agent: %s", analysis.should_use_agent())

        # Route based on confidence thresholds and complexity
        route_taken = self._determine_route(analysis)

        if route_taken == "rag":
            result = self._process_with_rag(query, analysis, buyer_memory=buyer_memory)
        elif route_taken == "agent":
            result = self._process_with_agent(query, analysis, buyer_memory=buyer_memory)
        else:
            # Medium complexity or confidence - try RAG first, agent if needed
            result = self._process_hybrid(query, analysis, buyer_memory=buyer_memory)

        # Add analysis to result if requested
        if return_analysis:
            result["analysis"] = analysis.dict()

        # Log classification metrics
        self._log_metrics(
            analysis=analysis,
            session_id=session_id,
            query=query,
            processing_time_ms=processing_time_ms,
            route_taken=route_taken,
            tools_used=result.get("intermediate_steps", []),
        )

        return result

    def _determine_route(self, analysis: QueryAnalysis) -> str:
        """Determine routing based on confidence and complexity.

        Args:
            analysis: Query analysis result

        Returns:
            Route name: "rag", "agent", or "hybrid"
        """
        confidence = analysis.confidence

        # High confidence - use classified route directly
        if confidence >= RoutingThresholds.HIGH_CONFIDENCE:
            if analysis.should_use_rag_only():
                return "rag"
            elif analysis.should_use_agent():
                return "agent"
            else:
                return "hybrid"

        # Medium confidence - use hybrid approach
        if confidence >= RoutingThresholds.MEDIUM_CONFIDENCE:
            return "hybrid"

        # Low confidence - default to hybrid for safety
        # (could trigger LLM fallback or clarification in future)
        return "hybrid"

    def _log_metrics(
        self,
        analysis: QueryAnalysis,
        session_id: Optional[str],
        query: str,
        processing_time_ms: float,
        route_taken: str,
        tools_used: Optional[List[Any]] = None,
    ) -> None:
        """Log classification metrics for quality tracking.

        Args:
            analysis: Query analysis result
            session_id: Session identifier
            query: Original query
            processing_time_ms: Processing time in milliseconds
            route_taken: Route that was used (rag, agent, hybrid)
            tools_used: List of tools/interactions used
        """
        try:
            # Extract tool names from intermediate steps if available
            tool_names: List[str] = []
            if tools_used:
                for step in tools_used:
                    if isinstance(step, tuple) and len(step) > 0:
                        action = step[0]
                        if hasattr(action, "tool"):
                            tool_names.append(action.tool)
                        elif isinstance(action, dict):
                            tool_names.append(action.get("tool", "unknown"))

            metrics = ClassificationMetrics(
                timestamp=datetime.now(),
                session_id=session_id,
                query=query[:500] if len(query) > 500 else query,
                query_length=len(query),
                primary_intent=analysis.intent,
                secondary_intents=analysis.secondary_intents,
                confidence=analysis.confidence,
                complexity=analysis.complexity,
                processing_time_ms=processing_time_ms,
                route_taken=route_taken,
                tools_used=tool_names,
                user_feedback=None,
                language_detected="en",  # Could be enhanced with language detection
                ambiguity_signals=[],  # Could be extracted from analysis
            )
            log_classification_metrics(metrics)
        except Exception as e:
            logger.warning("Failed to log classification metrics: %s", sanitize_for_log(e))

    def get_sources_for_query(self, query: str, k: int = 5) -> List[Document]:
        analysis = self.analyzer.analyze(query)
        if analysis.intent in [QueryIntent.CALCULATION, QueryIntent.GENERAL_QUESTION]:
            return []
        return self._retrieve_documents(query, analysis, k=k)

    def _retrieve_documents(
        self, query: str, analysis: QueryAnalysis, k: int = 5
    ) -> List[Document]:
        """
        Retrieve documents using hybrid search with explicit filters if available.

        Args:
            query: User query
            analysis: Query analysis result
            k: Number of documents to retrieve

        Returns:
            List of relevant documents
        """
        # Check if we have extracted filters
        filters = analysis.extracted_filters

        # Check if retriever supports explicit filtering (HybridPropertyRetriever)
        if filters and hasattr(self.retriever, "search_with_filters"):
            if self.verbose:
                logger.info("Using hybrid search with filters: %s", sanitize_for_log(filters))
            return cast(List[Document], self.retriever.search_with_filters(query, filters, k=k))

        # Fallback to standard retrieval
        if self.verbose:
            logger.info("Using standard retrieval")
        docs = self.retriever.invoke(query)  # type: ignore[attr-defined]
        return docs[:k]  # type: ignore[no-any-return]

    async def _aretrieve_documents(
        self, query: str, analysis: QueryAnalysis, k: int = 5
    ) -> List[Document]:
        filters = analysis.extracted_filters

        if filters and hasattr(self.retriever, "asearch_with_filters"):
            if self.verbose:
                logger.info("Using async hybrid search with filters: %s", filters)
            return cast(
                List[Document], await self.retriever.asearch_with_filters(query, filters, k=k)
            )

        if self.verbose:
            logger.info("Using async standard retrieval")
        docs = await self.retriever.ainvoke(query)  # type: ignore[attr-defined]
        return docs[:k]  # type: ignore[no-any-return]

    def _process_with_rag(
        self,
        query: str,
        analysis: QueryAnalysis,
        buyer_memory: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Process simple query with RAG only."""
        if self.verbose:
            logger.info("Processing with RAG only")

        memory_block = self._memory_section(buyer_memory)

        try:
            # If we have filters, we should use them for better retrieval
            if analysis.extracted_filters:
                docs = self._retrieve_documents(query, analysis)

                # Construct context from docs
                context_text = "\n\n".join([doc.page_content for doc in docs])

                # Simple generation without history rephrasing for now
                # (Or we could implement rephrasing if needed)
                prompt = self._join_prompt_sections(
                    f"Answer the question based only on the following context:\n\n{context_text}",
                    memory_block,
                    f"Question: {query}",
                )

                response_msg = self.llm.invoke(prompt)
                answer = (
                    response_msg.content if hasattr(response_msg, "content") else str(response_msg)
                )

                return {
                    "answer": answer,
                    "source_documents": docs,
                    "method": "rag_filtered",
                    "intent": analysis.intent.value,
                }

            # Standard RAG chain
            response = self._rag_chain_for(memory_block)({"question": query})
            source_documents = response.get("source_documents", [])
            if not source_documents and analysis.intent in {
                QueryIntent.SIMPLE_RETRIEVAL,
                QueryIntent.FILTERED_SEARCH,
                QueryIntent.RECOMMENDATION,
            }:
                return {
                    "answer": (
                        "I don't have any local listings/data to answer this yet. "
                        "Enable internet tools or ingest property data first."
                    ),
                    "source_documents": [],
                    "method": "rag",
                    "intent": analysis.intent.value,
                }

            return {
                "answer": response["answer"],
                "source_documents": source_documents,
                "method": "rag",
                "intent": analysis.intent.value,
            }

        except Exception as e:
            return {
                "answer": f"Error processing query with RAG: {str(e)}",
                "source_documents": [],
                "method": "rag",
                "error": str(e),
            }

    def _process_with_web_search(
        self,
        query: str,
        analysis: QueryAnalysis,
    ) -> Dict[str, Any]:
        try:
            cfg = WebResearchConfig(
                searxng_url=self.searxng_url,
                web_search_max_results=self.web_search_max_results,
                web_fetch_timeout_seconds=self.web_fetch_timeout_seconds,
                web_fetch_max_bytes=self.web_fetch_max_bytes,
                web_allowlist_domains=self.web_allowlist_domains,
            )
            agent = WebResearchAgent(llm=self.llm, config=cfg)
            result = agent.research(query)
            content = str(result.get("answer") or "")
            sources = list(result.get("sources") or [])
            intermediate_steps = list(result.get("intermediate_steps") or [])
        except Exception as e:
            content = f"Error processing query with web search: {str(e)}"
            sources = []
            intermediate_steps = []

        try:
            self.memory.save_context({"input": query}, {"answer": content})
        except Exception as e:
            logger.warning("Failed to save web search response to memory: %s", e)

        return {
            "answer": content,
            "source_documents": [],
            "sources": sources,
            "method": "web_search",
            "intent": analysis.intent.value,
            "intermediate_steps": intermediate_steps,
        }

    def _process_with_agent(
        self,
        query: str,
        analysis: QueryAnalysis,
        buyer_memory: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Process complex query with tool agent.

        Uses intent-specific agent prompts for better responses.
        """
        if self.verbose:
            logger.info("Processing with tool agent (intent: %s)", analysis.intent.value)

        memory_block = self._memory_section(buyer_memory)

        try:
            # First, get relevant context from RAG if needed
            context_docs = []
            if analysis.intent not in [
                QueryIntent.CALCULATION,
                QueryIntent.GENERAL_QUESTION,
            ]:
                # Use hybrid retrieval with filters
                context_docs = self._retrieve_documents(query, analysis, k=3)

            # Add context to query if available
            enhanced_query = query
            if context_docs:
                context_text = "\n\n".join(
                    [
                        f"Property {i + 1}: {doc.page_content[:200]}..."
                        for i, doc in enumerate(context_docs)
                    ]
                )
                enhanced_query = self._join_prompt_sections(
                    memory_block,
                    query,
                    f"Relevant properties:\n{context_text}",
                )
            elif memory_block:
                enhanced_query = self._join_prompt_sections(memory_block, query)

            # Get intent-specific agent
            agent = self._get_tool_agent_for_intent(analysis.intent)

            # Run agent
            response = agent.invoke({"input": enhanced_query})

            return {
                "answer": response["output"],
                "source_documents": context_docs,
                "method": "agent",
                "intent": analysis.intent.value,
                "intermediate_steps": response.get("intermediate_steps", []),
            }

        except Exception as e:
            return {
                "answer": f"Error processing query with agent: {str(e)}",
                "source_documents": [],
                "method": "agent",
                "error": str(e),
            }

    def _process_hybrid(
        self,
        query: str,
        analysis: QueryAnalysis,
        buyer_memory: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Process with hybrid approach - RAG + agent capabilities."""
        if self.verbose:
            logger.info("Processing with hybrid approach")

        memory_block = self._memory_section(buyer_memory)

        try:
            # Start with RAG for property retrieval (using filtered search if applicable)
            if memory_block:
                rag_response = self._process_with_rag(query, analysis, buyer_memory=memory_block)
            else:
                rag_response = self._process_with_rag(query, analysis)

            # Check if RAG answer is sufficient
            answer = rag_response["answer"]
            source_docs = rag_response.get("source_documents", [])

            # If query needs computation or deeper analysis, enhance with agent
            if analysis.requires_computation or analysis.complexity == Complexity.COMPLEX:
                # Use agent to enhance the answer
                enhanced_query = self._join_prompt_sections(
                    memory_block,
                    f"Based on this information about properties:\n\n{answer}",
                    f"Now answer this: {query}",
                )

                agent_response = self.tool_agent.invoke({"input": enhanced_query})

                answer = agent_response["output"]

            return {
                "answer": answer,
                "source_documents": source_docs,
                "method": "hybrid",
                "intent": analysis.intent.value,
            }

        except Exception as e:
            # Fallback to RAG-only
            logger.warning("Hybrid processing failed, falling back to RAG-only: %s", e)
            if memory_block:
                return self._process_with_rag(query, analysis, buyer_memory=memory_block)
            return self._process_with_rag(query, analysis)

    async def astream_query(
        self,
        query: str,
        buyer_memory: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """
        Process a query using the hybrid approach and stream the response.

        Args:
            query: The user's question.
            buyer_memory: Optional block of what the buyer has already told
                us, already assembled by the caller.

        Yields:
            JSON string chunks containing 'content' or 'error'.
        """
        memory_block = self._memory_section(buyer_memory)
        try:
            guard = self._domain_guard(query)
            if guard:
                content = str(guard.get("answer") or "")
                if content:
                    yield json.dumps({"content": content})
                    return
            analysis = self.analyzer.analyze(query)
            # Without memory the helpers are called exactly as they were before
            # it existed.
            if analysis.should_use_rag_only():
                if memory_block:
                    stream = self._astream_with_rag(query, analysis, buyer_memory=memory_block)
                else:
                    stream = self._astream_with_rag(query, analysis)
                async for chunk in stream:
                    yield chunk
            elif analysis.should_use_agent():
                if memory_block:
                    stream = self._astream_with_agent(query, analysis, buyer_memory=memory_block)
                else:
                    stream = self._astream_with_agent(query, analysis)
                async for chunk in stream:
                    yield chunk
            else:
                if memory_block:
                    stream = self._astream_hybrid(query, analysis, buyer_memory=memory_block)
                else:
                    stream = self._astream_hybrid(query, analysis)
                async for chunk in stream:
                    yield chunk
        except Exception as e:
            logger.error("Streaming failed: %s", sanitize_for_log(e))
            try:
                result = self.process_query(query, buyer_memory=memory_block)
                answer = result.get("answer", "")
                if answer:
                    yield json.dumps({"content": answer})
                    return
            except Exception as fallback_error:
                logger.error("Streaming fallback failed: %s", sanitize_for_log(fallback_error))
            yield json.dumps({"error": str(e)})

    async def _astream_with_rag(
        self,
        query: str,
        analysis: QueryAnalysis,
        buyer_memory: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Stream RAG response."""
        chain = self._rag_chain_for(self._memory_section(buyer_memory))
        async for event in chain.astream_events({"question": query}, version="v1"):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    yield json.dumps({"content": content})

    async def _astream_with_agent(
        self,
        query: str,
        analysis: QueryAnalysis,
        rag_context: str = "",
        buyer_memory: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Stream Agent response."""

        memory_block = self._memory_section(buyer_memory)

        # Prepare input
        input_text = self._join_prompt_sections(memory_block, query)
        if rag_context:
            input_text = self._join_prompt_sections(
                memory_block,
                f"Based on this information about properties:\n\n{rag_context}",
                f"Now answer this: {query}",
            )
        elif analysis.intent not in [QueryIntent.CALCULATION, QueryIntent.GENERAL_QUESTION]:
            try:
                context_docs = await self._aretrieve_documents(query, analysis, k=3)
                if context_docs:
                    context_text = "\n\n".join(
                        [
                            f"Property {i + 1}: {doc.page_content[:200]}..."
                            for i, doc in enumerate(context_docs)
                        ]
                    )
                    input_text = self._join_prompt_sections(
                        memory_block,
                        query,
                        f"Relevant properties:\n{context_text}",
                    )
            except Exception as e:
                logger.warning("Retrieval failed in stream: %s", sanitize_for_log(e))

        async for event in self.tool_agent.astream_events({"input": input_text}, version="v1"):
            kind = event["event"]
            if kind == "on_tool_end":
                # The call itself travels as data - the tool's name, the
                # arguments it was called with and what it answered. The
                # router collects these into the stream's meta event, so the
                # client draws the card from the fields instead of parsing
                # the agent's stringified step.
                call = build_tool_call(
                    event.get("name"),
                    (event.get("data") or {}).get("input"),
                    (event.get("data") or {}).get("output"),
                )
                if call:
                    yield json.dumps({"tool_call": call})
                continue
            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    yield json.dumps({"content": content})

    async def _astream_hybrid(
        self,
        query: str,
        analysis: QueryAnalysis,
        buyer_memory: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Stream Hybrid response."""
        memory_block = self._memory_section(buyer_memory)
        rag_response = await self._rag_chain_for(memory_block).ainvoke({"question": query})
        answer = rag_response["answer"]

        if analysis.requires_computation or analysis.complexity == Complexity.COMPLEX:
            if memory_block:
                chunks = self._astream_with_agent(
                    query, analysis, rag_context=answer, buyer_memory=memory_block
                )
            else:
                chunks = self._astream_with_agent(query, analysis, rag_context=answer)
            async for chunk in chunks:
                yield chunk
        else:
            yield json.dumps({"content": answer})

    def clear_memory(self) -> None:
        """Clear conversation memory."""
        self.memory.clear()

    def get_memory_summary(self) -> str:
        """Get summary of conversation memory."""
        return str(self.memory.load_memory_variables({}))


class SimpleRAGAgent:
    """
    Simple RAG-only agent for when tools aren't needed.

    This is a lightweight alternative to the full hybrid agent.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        retriever: BaseRetriever,
        memory: Optional[ConversationBufferMemory] = None,
        verbose: bool = False,
    ) -> None:
        """Initialize simple RAG agent."""
        self.llm = llm
        self.retriever = retriever
        self.memory = memory or ConversationBufferMemory(
            memory_key="chat_history", return_messages=True, output_key="answer"
        )
        self.verbose = verbose

        self.chain = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=retriever,
            memory=self.memory,
            return_source_documents=True,
            verbose=verbose,
        )

    def process_query(self, query: str) -> Dict[str, Any]:
        """Process query with RAG."""
        try:
            response = self.chain({"question": query})

            return {
                "answer": response["answer"],
                "source_documents": response.get("source_documents", []),
                "method": "rag_only",
            }

        except Exception as e:
            return {
                "answer": f"Error: {str(e)}",
                "source_documents": [],
                "method": "rag_only",
                "error": str(e),
            }

    def get_sources_for_query(self, query: str, k: int = 5) -> List[Document]:
        try:
            return self.retriever.invoke(query)[:k]  # type: ignore[attr-defined,no-any-return]
        except Exception as e:
            logger.warning("SimpleRAGAgent retrieval failed: %s", e)
            return []

    def clear_memory(self) -> None:
        """Clear conversation memory."""
        self.memory.clear()


def create_hybrid_agent(
    llm: BaseChatModel,
    retriever: BaseRetriever,
    memory: Optional[ConversationBufferMemory] = None,
    use_tools: bool = True,
    internet_enabled: bool = False,
    searxng_url: Optional[str] = None,
    web_search_max_results: int = 5,
    web_fetch_timeout_seconds: float = 10.0,
    web_fetch_max_bytes: int = 300_000,
    web_allowlist_domains: Optional[List[str]] = None,
    verbose: bool = False,
) -> HybridPropertyAgent | SimpleRAGAgent:
    """
    Factory function to create an agent.

    Args:
        llm: Language model
        retriever: Vector store retriever
        memory: Optional memory instance
        use_tools: Whether to use tool-based agent (default: True)
        verbose: Enable verbose output

    Returns:
        HybridPropertyAgent or SimpleRAGAgent
    """
    if use_tools:
        return HybridPropertyAgent(
            llm=llm,
            retriever=retriever,
            memory=memory,
            internet_enabled=internet_enabled,
            searxng_url=searxng_url,
            web_search_max_results=web_search_max_results,
            web_fetch_timeout_seconds=web_fetch_timeout_seconds,
            web_fetch_max_bytes=web_fetch_max_bytes,
            web_allowlist_domains=web_allowlist_domains,
            verbose=verbose,
        )
    else:
        return SimpleRAGAgent(llm=llm, retriever=retriever, memory=memory, verbose=verbose)
