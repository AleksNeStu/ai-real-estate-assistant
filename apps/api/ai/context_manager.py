"""
Context window management for LLM conversations.

This module provides token counting, context compression, summarization,
and optimization for managing conversation context windows across providers.
"""

import asyncio
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)

from ai.context_metrics import (
    ContextUsageMetrics,
    init_context_metrics_db,
    log_context_metrics,
)
from core.security_utils import sanitize_for_log

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

    from config.settings import AppSettings

logger = logging.getLogger(__name__)

# Default context window limits by provider (fallback values)
DEFAULT_CONTEXT_WINDOWS: Dict[str, int] = {
    "openai": 128000,
    "anthropic": 200000,
    "google": 1000000,
    "grok": 128000,
    "deepseek": 64000,
    "ollama": 4096,
}

# Characters per token estimate for non-OpenAI providers
CHARS_PER_TOKEN_ESTIMATE = 4


@dataclass
class ContextMetrics:
    """Metrics for a context optimization operation."""

    session_id: str
    timestamp: datetime
    total_tokens: int
    input_tokens: int
    context_window_limit: int
    utilization_percent: float
    estimated_cost_usd: float
    compression_applied: bool
    summarization_applied: bool
    messages_before: int
    messages_after: int
    model_id: str
    provider: str
    processing_time_ms: float = 0.0


class TokenCounter:
    """Multi-provider token counting utility."""

    def __init__(self) -> None:
        """Initialize token counter with tiktoken encoding cache."""
        self._encoding_cache: Dict[str, Any] = {}

    def _get_tiktoken_encoding(self, model_id: str) -> Any:
        """Get tiktoken encoding for a model (OpenAI models only)."""
        try:
            import tiktoken

            # Map model names to encodings
            if "gpt-4" in model_id or "gpt-4o" in model_id:
                encoding_name = "cl100k_base"
            elif "gpt-3.5" in model_id:
                encoding_name = "cl100k_base"
            else:
                encoding_name = "cl100k_base"

            if encoding_name not in self._encoding_cache:
                self._encoding_cache[encoding_name] = tiktoken.get_encoding(encoding_name)

            return self._encoding_cache[encoding_name]
        except ImportError:
            logger.warning("tiktoken not installed, using estimate")
            return None

    def count_tokens(self, text: str, model_id: str) -> int:
        """
        Count tokens in text for a specific model.

        Args:
            text: Text to count tokens for
            model_id: Model identifier

        Returns:
            Estimated token count
        """
        if not text:
            return 0

        # Determine provider from model_id
        provider = self._get_provider_from_model(model_id)

        # Use tiktoken for OpenAI models
        if provider == "openai":
            encoding = self._get_tiktoken_encoding(model_id)
            if encoding:
                return len(encoding.encode(text))

        # Use character-based estimate for other providers
        return len(text) // CHARS_PER_TOKEN_ESTIMATE

    def count_messages_tokens(self, messages: List[BaseMessage], model_id: str) -> int:
        """
        Count total tokens in a list of messages.

        Args:
            messages: List of LangChain messages
            model_id: Model identifier

        Returns:
            Total token count
        """
        total = 0
        for msg in messages:
            # Count message content
            content = getattr(msg, "content", "") or ""
            total += self.count_tokens(content, model_id)

            # Add overhead for message structure (role, etc.)
            total += 4  # Approximate overhead per message

        return total

    def get_context_window_limit(self, model_id: str) -> int:
        """
        Get context window limit for a model.

        Args:
            model_id: Model identifier

        Returns:
            Context window token limit
        """
        provider = self._get_provider_from_model(model_id)

        # Try to get from ModelProviderFactory
        try:
            from models.provider_factory import ModelProviderFactory

            result = ModelProviderFactory.get_model_by_id(model_id)
            if result:
                _, model_info = result
                return model_info.context_window
        except Exception:
            pass

        # Fallback to defaults
        return DEFAULT_CONTEXT_WINDOWS.get(provider, 4096)

    def _get_provider_from_model(self, model_id: str) -> str:
        """Infer provider from model ID."""
        model_lower = model_id.lower()

        if "gpt" in model_lower or "o1" in model_lower or "o3" in model_lower:
            return "openai"
        elif "claude" in model_lower:
            return "anthropic"
        elif "gemini" in model_lower:
            return "google"
        elif "grok" in model_lower:
            return "grok"
        elif "deepseek" in model_lower:
            return "deepseek"
        elif "llama" in model_lower or "mistral" in model_lower:
            return "ollama"

        return "openai"  # Default


class ContextCompressor:
    """Content compression utility for reducing context size."""

    def compress_repeated_content(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """
        Compress messages by removing repeated content.

        Args:
            messages: List of messages to compress

        Returns:
            Compressed message list
        """
        if len(messages) <= 1:
            return messages

        compressed: List[BaseMessage] = []

        for msg in messages:
            # Skip if identical to previous
            if compressed:
                prev_content = getattr(compressed[-1], "content", "") or ""
                curr_content = getattr(msg, "content", "") or ""

                if prev_content == curr_content:
                    continue

            # Compress property listing patterns
            content = self._compress_property_patterns(getattr(msg, "content", "") or "")

            # Create new message with compressed content
            compressed_msg = self._create_message_with_content(msg, content)
            compressed.append(compressed_msg)

        return compressed

    def _compress_property_patterns(self, content: str) -> str:
        """Compress repeated property listing patterns."""
        # Pattern for repeated property listings
        pattern = r"(Property \d+:.*?)(\nProperty \d+:.*){3,}"

        def replace_repeated(match: re.Match) -> str:
            first = match.group(1)
            return f"{first}\n... [additional properties summarized]"

        return re.sub(pattern, replace_repeated, content, flags=re.DOTALL)

    def _create_message_with_content(self, original: BaseMessage, new_content: str) -> BaseMessage:
        """Create a new message with modified content."""
        if isinstance(original, HumanMessage):
            return HumanMessage(content=new_content)
        elif isinstance(original, AIMessage):
            return AIMessage(content=new_content)
        elif isinstance(original, SystemMessage):
            return SystemMessage(content=new_content)
        else:
            return HumanMessage(content=new_content)

    def deduplicate_consecutive(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """Remove consecutive duplicate messages."""
        if not messages:
            return messages

        result: List[BaseMessage] = [messages[0]]

        for msg in messages[1:]:
            curr_content = getattr(msg, "content", "") or ""
            prev_content = getattr(result[-1], "content", "") or ""

            if curr_content != prev_content:
                result.append(msg)

        return result


class ContextSummarizer:
    """LLM-based conversation summarization."""

    SUMMARIZATION_PROMPT = """Summarize the following conversation history concisely, preserving:
1. Key user questions and requests
2. Important property references (addresses, prices)
3. Decisions or conclusions reached
4. Any pending questions or tasks

Conversation:
{conversation}

Provide a brief summary (2-3 sentences) that captures the essential context:"""

    def __init__(self, max_summary_tokens: int = 500):
        """
        Initialize summarizer.

        Args:
            max_summary_tokens: Maximum tokens for summary output
        """
        self.max_summary_tokens = max_summary_tokens

    def summarize_history(self, messages: List[BaseMessage], llm: "BaseChatModel") -> str:
        """
        Summarize conversation history using LLM.

        Args:
            messages: Messages to summarize
            llm: LLM instance for summarization

        Returns:
            Summary text
        """
        if not messages:
            return ""

        # Format conversation for summarization
        conversation_text = self._format_conversation(messages)

        # Create summarization prompt
        prompt = self.SUMMARIZATION_PROMPT.format(conversation=conversation_text)

        try:
            # Call LLM for summarization
            response = llm.invoke(prompt)
            summary = getattr(response, "content", str(response))
            return summary.strip()
        except Exception as e:
            logger.warning("Summarization failed: %s", e)
            # Fallback: return truncated conversation
            return self._fallback_summary(messages)

    def should_summarize(
        self,
        token_count: int,
        threshold_percent: float,
        context_window: int,
    ) -> bool:
        """
        Determine if summarization should be triggered.

        Args:
            token_count: Current token count
            threshold_percent: Threshold percentage (0-100)
            context_window: Model's context window limit

        Returns:
            True if summarization should be triggered
        """
        threshold = (threshold_percent / 100.0) * context_window
        return token_count >= threshold

    def _format_conversation(self, messages: List[BaseMessage]) -> str:
        """Format messages as conversation text."""
        lines = []
        for msg in messages:
            role = msg.__class__.__name__.replace("Message", "").upper()
            content = getattr(msg, "content", "") or ""
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def _fallback_summary(self, messages: List[BaseMessage]) -> str:
        """Create fallback summary when LLM summarization fails."""
        # Take first and last few messages
        if len(messages) <= 4:
            return self._format_conversation(messages)

        first_two = messages[:2]
        last_two = messages[-2:]

        summary_parts = [
            "Earlier conversation:",
            self._format_conversation(first_two),
            "...",
            "Recent messages:",
            self._format_conversation(last_two),
        ]
        return "\n".join(summary_parts)


class ContextManager:
    """
    Main orchestrator for context window optimization.

    Coordinates token counting, compression, summarization, and sliding window
    to keep conversations within model context limits.
    """

    def __init__(self, settings: "AppSettings"):
        """
        Initialize context manager.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.token_counter = TokenCounter()
        self.compressor = ContextCompressor()
        self.summarizer = ContextSummarizer()

        # Initialize metrics database (async)
        if settings.context_metrics_enabled:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(init_context_metrics_db())
            except RuntimeError:
                asyncio.run(init_context_metrics_db())

    def optimize_context(
        self,
        session_id: str,
        messages: List[BaseMessage],
        model_id: str,
        llm: Optional["BaseChatModel"] = None,
        max_utilization: Optional[float] = None,
    ) -> Tuple[List[BaseMessage], Optional[ContextMetrics]]:
        """
        Optimize conversation context for a model.

        Args:
            session_id: Session identifier
            messages: Original messages
            model_id: Target model ID
            llm: Optional LLM for summarization
            max_utilization: Max utilization (0.0-1.0), uses settings if not provided

        Returns:
            Tuple of (optimized_messages, metrics)
        """
        start_time = time.time()

        if not messages:
            return messages, None

        # Get context window for model
        context_window = self.token_counter.get_context_window_limit(model_id)
        max_util = max_utilization or (self.settings.context_max_utilization_percent / 100.0)
        max_tokens = int(context_window * max_util)

        # Count initial tokens
        initial_tokens = self.token_counter.count_messages_tokens(messages, model_id)
        initial_utilization = (initial_tokens / context_window) * 100

        # If under limit, no optimization needed
        if initial_tokens <= max_tokens:
            return messages, None

        logger.info(
            "Context optimization triggered: session=%s tokens=%d/%d utilization=%.1f%%",
            sanitize_for_log(session_id),
            initial_tokens,
            context_window,
            initial_utilization,
        )

        # Track optimization steps
        compression_applied = False
        summarization_applied = False
        optimized = list(messages)

        # Step 1: Apply compression if enabled
        if self.settings.context_compression_enabled:
            optimized = self.compressor.compress_repeated_content(optimized)
            optimized = self.compressor.deduplicate_consecutive(optimized)
            compression_applied = True

        # Check if compression was enough
        current_tokens = self.token_counter.count_messages_tokens(optimized, model_id)

        # Step 2: Apply sliding window if still over limit
        if current_tokens > max_tokens:
            optimized = self.apply_sliding_window(
                optimized,
                self.settings.context_sliding_window_messages,
            )

        # Check again
        current_tokens = self.token_counter.count_messages_tokens(optimized, model_id)

        # Step 3: Apply priority selection if still over limit
        if current_tokens > max_tokens:
            optimized = self.prioritize_messages(
                optimized,
                max_tokens,
                model_id,
                system_weight=self.settings.context_priority_system_weight,
                recent_weight=self.settings.context_priority_recent_weight,
            )

        # Check again
        current_tokens = self.token_counter.count_messages_tokens(optimized, model_id)

        # Step 4: Apply summarization if still over limit and LLM available
        if current_tokens > max_tokens and llm:
            summary = self.summarizer.summarize_history(
                messages[: -self.settings.context_sliding_window_messages],
                llm,
            )

            # Replace old messages with summary
            recent_messages = optimized[-self.settings.context_sliding_window_messages :]
            summary_msg = SystemMessage(content=f"[Previous conversation summary: {summary}]")
            optimized = [summary_msg] + recent_messages
            summarization_applied = True

        # Calculate final metrics
        final_tokens = self.token_counter.count_messages_tokens(optimized, model_id)
        final_utilization = (final_tokens / context_window) * 100
        processing_time = (time.time() - start_time) * 1000

        # Estimate cost
        provider = self.token_counter._get_provider_from_model(model_id)
        estimated_cost = self._estimate_cost(model_id, final_tokens, 0)

        metrics = ContextMetrics(
            session_id=session_id,
            timestamp=datetime.now(),
            total_tokens=final_tokens,
            input_tokens=final_tokens,
            context_window_limit=context_window,
            utilization_percent=final_utilization,
            estimated_cost_usd=estimated_cost,
            compression_applied=compression_applied,
            summarization_applied=summarization_applied,
            messages_before=len(messages),
            messages_after=len(optimized),
            model_id=model_id,
            provider=provider,
            processing_time_ms=processing_time,
        )

        # Log metrics if enabled
        if self.settings.context_metrics_enabled:
            self._log_metrics(metrics)

        logger.info(
            "Context optimization complete: tokens=%d->%d (%.1f%%->%.1f%%) "
            "messages=%d->%d time=%.1fms",
            initial_tokens,
            final_tokens,
            initial_utilization,
            final_utilization,
            len(messages),
            len(optimized),
            processing_time,
        )

        return optimized, metrics

    def apply_sliding_window(
        self, messages: List[BaseMessage], window_size: int
    ) -> List[BaseMessage]:
        """
        Apply sliding window to keep only recent messages.

        Args:
            messages: Original messages
            window_size: Number of messages to keep

        Returns:
            Messages within sliding window
        """
        if len(messages) <= window_size:
            return messages

        # Always keep system messages
        system_messages = [m for m in messages if isinstance(m, SystemMessage)]
        non_system = [m for m in messages if not isinstance(m, SystemMessage)]

        # Keep most recent non-system messages
        recent = non_system[-window_size:] if len(non_system) > window_size else non_system

        # Return system messages + recent messages (preserve order)
        # Note: System messages typically go first
        return system_messages + recent

    def prioritize_messages(
        self,
        messages: List[BaseMessage],
        max_tokens: int,
        model_id: str,
        system_weight: float = 1.0,
        recent_weight: float = 0.8,
    ) -> List[BaseMessage]:
        """
        Prioritize messages using weighted scoring.

        Args:
            messages: Messages to prioritize
            max_tokens: Maximum tokens to include
            model_id: Model identifier
            system_weight: Weight for system messages
            recent_weight: Decay factor for older messages

        Returns:
            Prioritized messages within token limit
        """
        if not messages:
            return messages

        # Score each message
        scored: List[Tuple[float, int, BaseMessage]] = []

        for i, msg in enumerate(messages):
            score = 0.0

            # System messages always get highest priority
            if isinstance(msg, SystemMessage):
                score = system_weight
            else:
                # Recency score (newer = higher)
                recency = (i + 1) / len(messages)
                score = recency * recent_weight

                # Bonus for human messages (questions are important)
                if isinstance(msg, HumanMessage):
                    score += 0.1

            scored.append((score, i, msg))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        # Select messages until token limit
        selected: List[Tuple[int, BaseMessage]] = []
        total_tokens = 0

        for _score, orig_idx, msg in scored:
            msg_tokens = self.token_counter.count_tokens(
                getattr(msg, "content", "") or "", model_id
            )

            if total_tokens + msg_tokens <= max_tokens:
                selected.append((orig_idx, msg))
                total_tokens += msg_tokens

        # Restore original order
        selected.sort(key=lambda x: x[0])

        return [msg for _, msg in selected]

    def _estimate_cost(self, model_id: str, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for token usage."""
        try:
            from models.provider_factory import ModelProviderFactory

            result = ModelProviderFactory.get_model_by_id(model_id)
            if result:
                provider, model_info = result
                cost = provider.estimate_cost(model_id, input_tokens, output_tokens)
                return cost or 0.0
        except Exception:
            pass

        return 0.0

    def _log_metrics(self, metrics: ContextMetrics) -> None:
        """Log metrics to database (fire-and-forget async)."""
        try:
            usage_metrics = ContextUsageMetrics(
                timestamp=metrics.timestamp,
                session_id=metrics.session_id,
                model_id=metrics.model_id,
                provider=metrics.provider,
                input_tokens=metrics.input_tokens,
                output_tokens=0,
                context_window_limit=metrics.context_window_limit,
                utilization_percent=metrics.utilization_percent,
                estimated_cost_usd=metrics.estimated_cost_usd,
                compression_applied=metrics.compression_applied,
                summarization_applied=metrics.summarization_applied,
                messages_before=metrics.messages_before,
                messages_after=metrics.messages_after,
                processing_time_ms=metrics.processing_time_ms,
            )
            # Schedule async logging without blocking the caller
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(log_context_metrics(usage_metrics))
            except RuntimeError:
                # No running loop — run in a new one
                asyncio.run(log_context_metrics(usage_metrics))
        except Exception as e:
            logger.warning("Failed to log context metrics: %s", e)
