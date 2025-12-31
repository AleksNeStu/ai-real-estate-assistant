"""
Hybrid agent system combining RAG and tool-based agents.

This module provides intelligent orchestration between:
- Simple RAG for straightforward queries
- Tool-based agent for complex tasks
- Hybrid approach combining both
"""

import logging
from typing import Dict, Any, List, Optional
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import BaseTool
from langchain_core.language_models import BaseChatModel
from langchain_core.retrievers import BaseRetriever
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory

from agents.query_analyzer import QueryAnalyzer, QueryAnalysis, QueryIntent, Complexity
from tools.property_tools import create_property_tools

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
        verbose: bool = False
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
            memory_key="chat_history",
            return_messages=True,
            output_key="output"
        )
        self.tools = tools or create_property_tools()
        self.verbose = verbose

        # Initialize query analyzer
        self.analyzer = QueryAnalyzer()

        # Initialize RAG chain
        self.rag_chain = self._create_rag_chain()

        # Initialize tool agent
        self.tool_agent = self._create_tool_agent()

    def _create_rag_chain(self) -> ConversationalRetrievalChain:
        """Create RAG chain for simple queries."""
        return ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self.retriever,
            memory=self.memory,
            return_source_documents=True,
            verbose=self.verbose
        )

    def _create_tool_agent(self) -> AgentExecutor:
        """Create tool-based agent for complex queries."""

        # Create prompt template for tool agent
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an intelligent real estate assistant with access to specialized tools.

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

Context from property database will be provided when relevant."""),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        # Create agent
        agent = create_openai_tools_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )

        # Create executor
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=self.verbose,
            return_intermediate_steps=True
        )

    def process_query(
        self,
        query: str,
        return_analysis: bool = False
    ) -> Dict[str, Any]:
        """
        Process a query using the hybrid approach.

        Args:
            query: User query
            return_analysis: Whether to include query analysis in response

        Returns:
            Dictionary with answer, sources, and optional analysis
        """
        # Analyze query
        analysis = self.analyzer.analyze(query)

        if self.verbose:
            logger.info("Query Analysis: %s", analysis.reasoning)
            logger.info("Should use agent: %s", analysis.should_use_agent())

        # Route to appropriate processor
        if analysis.should_use_rag_only():
            result = self._process_with_rag(query, analysis)
        elif analysis.should_use_agent():
            result = self._process_with_agent(query, analysis)
        else:
            # Medium complexity - try RAG first, agent if needed
            result = self._process_hybrid(query, analysis)

        # Add analysis to result if requested
        if return_analysis:
            result["analysis"] = analysis.dict()

        return result

    def _process_with_rag(
        self,
        query: str,
        analysis: QueryAnalysis
    ) -> Dict[str, Any]:
        """Process simple query with RAG only."""
        if self.verbose:
            logger.info("Processing with RAG only")

        try:
            response = self.rag_chain({"question": query})

            return {
                "answer": response["answer"],
                "source_documents": response.get("source_documents", []),
                "method": "rag",
                "intent": analysis.intent.value
            }

        except Exception as e:
            return {
                "answer": f"Error processing query with RAG: {str(e)}",
                "source_documents": [],
                "method": "rag",
                "error": str(e)
            }

    def _process_with_agent(
        self,
        query: str,
        analysis: QueryAnalysis
    ) -> Dict[str, Any]:
        """Process complex query with tool agent."""
        if self.verbose:
            logger.info("Processing with tool agent")

        try:
            # First, get relevant context from RAG if needed
            context_docs = []
            if analysis.intent not in [QueryIntent.CALCULATION, QueryIntent.GENERAL_QUESTION]:
                rag_results = self.retriever.get_relevant_documents(query)
                context_docs = rag_results[:3]  # Top 3 for context

            # Add context to query if available
            enhanced_query = query
            if context_docs:
                context_text = "\n\n".join([
                    f"Property {i+1}: {doc.page_content[:200]}..."
                    for i, doc in enumerate(context_docs)
                ])
                enhanced_query = f"{query}\n\nRelevant properties:\n{context_text}"

            # Run agent
            response = self.tool_agent.invoke({
                "input": enhanced_query
            })

            return {
                "answer": response["output"],
                "source_documents": context_docs,
                "method": "agent",
                "intent": analysis.intent.value,
                "intermediate_steps": response.get("intermediate_steps", [])
            }

        except Exception as e:
            return {
                "answer": f"Error processing query with agent: {str(e)}",
                "source_documents": [],
                "method": "agent",
                "error": str(e)
            }

    def _process_hybrid(
        self,
        query: str,
        analysis: QueryAnalysis
    ) -> Dict[str, Any]:
        """Process with hybrid approach - RAG + agent capabilities."""
        if self.verbose:
            logger.info("Processing with hybrid approach")

        try:
            # Start with RAG for property retrieval
            rag_response = self.rag_chain({"question": query})

            # Check if RAG answer is sufficient
            answer = rag_response["answer"]
            source_docs = rag_response.get("source_documents", [])

            # If query needs computation or deeper analysis, enhance with agent
            if analysis.requires_computation or analysis.complexity == Complexity.COMPLEX:
                # Use agent to enhance the answer
                enhanced_query = (
                    f"Based on this information about properties:\n\n"
                    f"{answer}\n\n"
                    f"Now answer this: {query}"
                )

                agent_response = self.tool_agent.invoke({
                    "input": enhanced_query
                })

                answer = agent_response["output"]

            return {
                "answer": answer,
                "source_documents": source_docs,
                "method": "hybrid",
                "intent": analysis.intent.value
            }

        except Exception as e:
            # Fallback to RAG-only
            return self._process_with_rag(query, analysis)

    def clear_memory(self):
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
        verbose: bool = False
    ):
        """Initialize simple RAG agent."""
        self.llm = llm
        self.retriever = retriever
        self.memory = memory or ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )
        self.verbose = verbose

        self.chain = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=retriever,
            memory=self.memory,
            return_source_documents=True,
            verbose=verbose
        )

    def process_query(self, query: str) -> Dict[str, Any]:
        """Process query with RAG."""
        try:
            response = self.chain({"question": query})

            return {
                "answer": response["answer"],
                "source_documents": response.get("source_documents", []),
                "method": "rag_only"
            }

        except Exception as e:
            return {
                "answer": f"Error: {str(e)}",
                "source_documents": [],
                "method": "rag_only",
                "error": str(e)
            }

    def clear_memory(self):
        """Clear conversation memory."""
        self.memory.clear()


def create_hybrid_agent(
    llm: BaseChatModel,
    retriever: BaseRetriever,
    use_tools: bool = True,
    verbose: bool = False
) -> Any:
    """
    Factory function to create an agent.

    Args:
        llm: Language model
        retriever: Vector store retriever
        use_tools: Whether to use tool-based agent (default: True)
        verbose: Enable verbose output

    Returns:
        HybridPropertyAgent or SimpleRAGAgent
    """
    if use_tools:
        return HybridPropertyAgent(
            llm=llm,
            retriever=retriever,
            verbose=verbose
        )
    else:
        return SimpleRAGAgent(
            llm=llm,
            retriever=retriever,
            verbose=verbose
        )
