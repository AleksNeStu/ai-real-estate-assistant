"""
The conversation buffer, without the deprecated LangChain class.

LangChain deprecated ``ConversationBufferMemory`` in 0.3.1 and announces its
removal in 2.0. The memory sits on the conversation path, so the next major
upgrade of the dependency would break the chat outright - and the warning
that announces it is printed once on every start and then scrolls away.

This module implements the same small surface on the stable primitives:

* ``BaseChatMessageHistory`` for the storage,
* ``BaseMemory`` for the contract the retrieval chain expects.

The behaviour is the one the application already relies on: the whole
history is kept, ``save_context`` appends a human and an AI message, and
``load_memory_variables`` returns the history under ``memory_key``.
"""

from typing import Any, Optional

from langchain_core.chat_history import (
    BaseChatMessageHistory,
    InMemoryChatMessageHistory,
)
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    get_buffer_string,
)
from pydantic import Field

try:  # langchain-core >= 1.0 moved BaseMemory out of langchain_core.memory
    from langchain_classic.base_memory import BaseMemory
except ImportError:  # pragma: no cover - older layouts
    from langchain_core.memory import BaseMemory  # type: ignore[no-redef]


class ConversationBufferMemory(BaseMemory):
    """A memory that keeps the entire conversation history.

    Args:
        chat_memory: Where the messages are stored. Defaults to an in-memory
            history, which is what the application used before.
        memory_key: The key the history is returned under.
        input_key: The key the incoming question is read from.
        output_key: The key the answer is read from.
        return_messages: Whether the history is returned as message objects
            instead of a formatted string.
    """

    human_prefix: str = "Human"
    ai_prefix: str = "AI"
    memory_key: str = "history"
    input_key: str = "input"
    output_key: str = "output"
    return_messages: bool = False
    chat_memory: BaseChatMessageHistory = Field(default_factory=InMemoryChatMessageHistory)

    @property
    def memory_variables(self) -> list[str]:
        """The keys this memory adds to the chain inputs."""
        return [self.memory_key]

    @property
    def buffer(self) -> Any:
        """The whole history, in the requested representation."""
        return self.buffer_as_messages if self.return_messages else self.buffer_as_str

    @property
    def buffer_as_messages(self) -> list[BaseMessage]:
        """The history as message objects."""
        return list(self.chat_memory.messages)

    @property
    def buffer_as_str(self) -> str:
        """The history as a formatted string."""
        return get_buffer_string(
            self.chat_memory.messages,
            human_prefix=self.human_prefix,
            ai_prefix=self.ai_prefix,
        )

    def load_memory_variables(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Return the history for the chain."""
        return {self.memory_key: self.buffer}

    def save_context(self, inputs: dict[str, Any], outputs: dict[str, str]) -> None:
        """Append the question and the answer to the history."""
        input_key = self.input_key
        output_key = self.output_key

        if input_key not in inputs:
            raise ValueError(f"Input key {input_key} not found in inputs")
        if output_key not in outputs:
            raise ValueError(f"Output key {output_key} not found in outputs")

        self.chat_memory.add_message(HumanMessage(content=inputs[input_key]))
        self.chat_memory.add_message(AIMessage(content=outputs[output_key]))

    def clear(self) -> None:
        """Forget the whole conversation."""
        self.chat_memory.clear()


def build_buffer_memory(
    chat_memory: Optional[BaseChatMessageHistory] = None,
    *,
    memory_key: str = "chat_history",
    output_key: str = "answer",
) -> ConversationBufferMemory:
    """Build the buffer the way this application uses it everywhere."""
    return ConversationBufferMemory(
        chat_memory=chat_memory or InMemoryChatMessageHistory(),
        memory_key=memory_key,
        return_messages=True,
        output_key=output_key,
    )
