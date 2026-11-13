"""
Intent-specific system prompts for the Real Estate Assistant.

This module provides tailored system prompts based on the detected
query intent, optimized for each type of user interaction.
"""

from typing import Any, Dict, Iterable, Optional

from agents.query_analyzer import QueryIntent

# System prompts tailored for each intent type
INTENT_SYSTEM_PROMPTS: Dict[QueryIntent, str] = {
    QueryIntent.PROPERTY_SEARCH: """You are a real estate search assistant.
Focus on finding properties matching user criteria.
Present results in a structured format with key details highlighted.
Be specific about property types, sizes, features, and pricing.
Use concise but thorough language.""",
    QueryIntent.MARKET_ANALYSIS: """You are a real estate market analyst.
Focus on analyzing market data: trends, statistics, averages.
Provide data-driven insights to help users understand the market.
Use statistics and comparisons where available.
Present findings in clear, structured formats.""",
    QueryIntent.COMPARISON: """You are a property comparison specialist.
Focus on presenting side-by-side comparisons highlighting pros, cons,
and trade-offs.
Use tables or structured lists for clarity.
Be specific about differences in pricing, features, and locations.""",
    QueryIntent.MORTGAGE: """You are a mortgage advisor.
Focus on calculating payments, explaining terms, and providing
financial guidance for home buying decisions.
Always include total cost over loan lifetime and interest breakdown.
Be precise with numbers and explain financial concepts clearly.""",
    QueryIntent.LOCATION: """You are a neighborhood expert.
Focus on providing insights on amenities, transport, safety, and
lifestyle factors for different areas.
Include practical information for decision-making.
Be specific about nearby facilities and neighborhood characteristics.""",
    QueryIntent.DOCUMENT_QA: """You are answering questions about specific
properties from the context provided.
Reference the property details when answering.
Be precise and factual.
Focus on the specific property or listing the user is asking about.""",
    QueryIntent.GENERAL: """You are a helpful real estate assistant.
Answer general questions about the real estate process.
If the question is outside real estate, politely redirect.
Provide practical, actionable advice.""",
    # Legacy intent support (map to same prompts)
    QueryIntent.SIMPLE_RETRIEVAL: """You are a real estate search assistant.
Focus on finding properties matching user criteria.
Present results in a structured format with key details highlighted.
Use concise but thorough language.""",
    QueryIntent.FILTERED_SEARCH: """You are a real estate search assistant.
Focus on finding properties matching the user's specific criteria.
Present filtered results with key details highlighted.
Use concise but thorough language.""",
    QueryIntent.ANALYSIS: """You are a real estate market analyst.
Focus on analyzing market data: trends, statistics, averages.
Provide data-driven insights to help users understand the market.
Use statistics and comparisons where available.""",
    QueryIntent.CALCULATION: """You are a mortgage and calculations advisor.
Focus on calculating payments, costs, and providing financial guidance.
Always include total cost over loan lifetime and interest breakdown.
Be precise with numbers and explain calculations clearly.""",
    QueryIntent.RECOMMENDATION: """You are a real estate recommendation expert.
Focus on finding the best properties based on user criteria.
Highlight value, quality, and fit for the user's needs.
Explain your reasoning for recommendations.""",
    QueryIntent.CONVERSATION: """You are continuing a conversation about
real estate properties.
Reference previous context when answering follow-up questions.
Be precise and factual about the properties discussed.""",
    QueryIntent.GENERAL_QUESTION: """You are a helpful real estate assistant.
Answer general questions about the real estate process.
If the question is outside real estate, politely redirect.
Provide practical, actionable advice.""",
}


def get_system_prompt_for_intent(intent: QueryIntent) -> str:
    """
    Get the appropriate system prompt for a given intent.

    Args:
        intent: The detected query intent

    Returns:
        System prompt string optimized for that intent
    """
    return INTENT_SYSTEM_PROMPTS.get(intent, INTENT_SYSTEM_PROMPTS[QueryIntent.GENERAL])


# The buyer's memory block: what this buyer has already told us.
#
# The wording lives here, next to the other prompts, so the agent stays a
# consumer of the block and never owns a sentence of it.
BUYER_MEMORY_HEADER = "What the buyer has already told us:"

# The caps. The memory is about the buyer, not about the listings, so it is
# never allowed to crowd the retrieved documents.
BUYER_MEMORY_MAX_FACTS = 10
BUYER_MEMORY_MAX_CHARS = 2000


def build_buyer_memory_block(facts: Optional[Iterable[Any]]) -> str:
    """
    Assemble the buyer's memory into a prompt block.

    A fact is anything carrying a `kind` and a `content` - a
    BuyerMemoryFact, or anything shaped like one.

    Args:
        facts: The buyer's facts, newest and most relevant first.

    Returns:
        The block, holding at most BUYER_MEMORY_MAX_FACTS facts and at most
        BUYER_MEMORY_MAX_CHARS characters. An empty string when the buyer has
        told us nothing - the caller then builds exactly the prompt it built
        before the memory existed.
    """
    if not facts:
        return ""

    lines: list[str] = []
    for fact in facts:
        if len(lines) >= BUYER_MEMORY_MAX_FACTS:
            break
        kind = str(getattr(fact, "kind", "") or "").strip()
        content = str(getattr(fact, "content", "") or "").strip()
        if not content:
            continue
        lines.append(f"- {kind}: {content}" if kind else f"- {content}")

    if not lines:
        return ""

    # A fact is never cut in half: when the block no longer fits, the next
    # fact is left out instead.
    kept: list[str] = []
    for line in lines:
        candidate = BUYER_MEMORY_HEADER + "\n" + "\n".join([*kept, line])
        if len(candidate) > BUYER_MEMORY_MAX_CHARS:
            break
        kept.append(line)

    if not kept:
        # A single fact larger than the cap - take what fits of it.
        first = lines[0]
        room = BUYER_MEMORY_MAX_CHARS - len(BUYER_MEMORY_HEADER) - 1
        if room <= 0:
            return ""
        kept = [first[:room].rstrip()]

    return BUYER_MEMORY_HEADER + "\n" + "\n".join(kept)
