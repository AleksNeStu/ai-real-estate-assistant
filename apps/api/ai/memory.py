"""
Memory management for AI agents.
Handles session persistence using SQLite with context window optimization.
"""

import logging
import os
from typing import TYPE_CHECKING, Optional, Tuple

try:
    from langchain.memory import ConversationBufferMemory
except ImportError:
    from langchain_classic.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

    from ai.context_manager import ContextManager, ContextMetrics
    from config.settings import AppSettings

logger = logging.getLogger(__name__)

# Define database path
DB_PATH = os.path.join(os.getcwd(), "data", "sessions.db")
CONNECTION_STRING = f"sqlite:///{DB_PATH}"

# Global context manager instance
_context_manager: Optional["ContextManager"] = None


def get_session_history(session_id: str) -> BaseChatMessageHistory:
    """
    Get chat message history for a session.

    Args:
        session_id: Unique session identifier

    Returns:
        BaseChatMessageHistory instance backed by SQLite
    """
    # langchain >= 1.3.9 + langchain-core >= 1.4.2 removed the legacy
    # `connection_string` kwarg from SQLChatMessageHistory.__init__.
    # Use the new `connection` parameter (accepts a URL string or an Engine).
    # SQLChatMessageHistory automatically creates the table 'message_store' if needed.
    return SQLChatMessageHistory(session_id=session_id, connection=CONNECTION_STRING)


def init_context_manager(settings: "AppSettings") -> "ContextManager":
    """
    Initialize the global context manager.

    Args:
        settings: Application settings

    Returns:
        ContextManager instance
    """
    global _context_manager

    if _context_manager is None:
        from ai.context_manager import ContextManager

        _context_manager = ContextManager(settings)
        logger.info("Context manager initialized")

    return _context_manager


def get_context_manager() -> Optional["ContextManager"]:
    """
    Get the global context manager instance.

    Returns:
        ContextManager if initialized, None otherwise
    """
    return _context_manager


def get_optimized_memory(
    session_id: str,
    model_id: str,
    llm: Optional["BaseChatModel"] = None,
    max_utilization: Optional[float] = None,
) -> Tuple[ConversationBufferMemory, Optional["ContextMetrics"]]:
    """
    Get memory with optimized context for a specific model.

    This function retrieves the session history and optimizes it to fit
    within the model's context window limits.

    Args:
        session_id: Session identifier
        model_id: Target model ID for token counting
        llm: Optional LLM instance for summarization
        max_utilization: Maximum context utilization (0.0-1.0)

    Returns:
        Tuple of (memory, metrics) where metrics may be None
    """
    # Get session history
    chat_history = get_session_history(session_id)
    messages = chat_history.messages

    # Check if context manager is available
    cm = get_context_manager()

    if cm is None:
        # No context manager - return unoptimized memory
        memory = ConversationBufferMemory(
            chat_memory=chat_history,
            memory_key="chat_history",
            return_messages=True,
            output_key="answer",
        )
        return memory, None

    # Optimize context
    optimized_messages, metrics = cm.optimize_context(
        session_id=session_id,
        messages=messages,
        model_id=model_id,
        llm=llm,
        max_utilization=max_utilization,
    )

    # If optimization occurred, create memory with optimized history
    if metrics is not None and len(optimized_messages) != len(messages):
        # Create a new history with optimized messages
        optimized_history = OptimizedSessionHistory(
            session_id=session_id,
            connection_string=CONNECTION_STRING,
            initial_messages=optimized_messages,
        )

        memory = ConversationBufferMemory(
            chat_memory=optimized_history,
            memory_key="chat_history",
            return_messages=True,
            output_key="answer",
        )
    else:
        # No optimization needed
        memory = ConversationBufferMemory(
            chat_memory=chat_history,
            memory_key="chat_history",
            return_messages=True,
            output_key="answer",
        )

    return memory, metrics


class OptimizedSessionHistory(BaseChatMessageHistory):
    """
    A chat message history that uses pre-optimized messages.

    This class wraps optimized messages in a history interface
    without modifying the underlying persistent storage.
    """

    def __init__(
        self,
        session_id: str,
        connection_string: str,
        initial_messages: Optional[list] = None,
    ):
        """
        Initialize optimized session history.

        Args:
            session_id: Session identifier
            connection_string: SQLite connection string
            initial_messages: Pre-optimized messages to use
        """
        self.session_id = session_id
        self.connection_string = connection_string
        self._messages = initial_messages or []

    @property
    def messages(self) -> list:
        """Get the optimized messages."""
        return self._messages

    def add_message(self, message) -> None:
        """Add a message to both optimized cache and persistent storage."""
        self._messages.append(message)

        # Also persist to underlying storage
        persistent_history = SQLChatMessageHistory(
            session_id=self.session_id,
            connection_string=self.connection_string,
        )
        persistent_history.add_message(message)

    def clear(self) -> None:
        """Clear both optimized cache and persistent storage."""
        self._messages = []

        persistent_history = SQLChatMessageHistory(
            session_id=self.session_id,
            connection_string=self.connection_string,
        )
        persistent_history.clear()
