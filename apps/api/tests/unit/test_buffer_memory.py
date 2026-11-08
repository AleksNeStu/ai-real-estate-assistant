"""
Tests for the project's own conversation buffer.

Task #40: the LangChain class was deprecated and scheduled for removal in
2.0, and the memory sits on the conversation path. The replacement has to
behave exactly like the class it replaces.
"""

import pytest
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import AIMessage, HumanMessage

from ai.buffer_memory import ConversationBufferMemory, build_buffer_memory


class TestConversationBufferMemory:
    def test_a_new_memory_is_empty(self):
        memory = build_buffer_memory()

        assert memory.load_memory_variables({}) == {"chat_history": []}

    def test_save_context_appends_the_question_and_the_answer(self):
        memory = build_buffer_memory()

        memory.save_context({"input": "Two rooms in Krakow"}, {"answer": "Here are three."})

        messages = memory.load_memory_variables({})["chat_history"]
        assert messages[0] == HumanMessage(content="Two rooms in Krakow")
        assert messages[1] == AIMessage(content="Here are three.")

    def test_the_history_survives_a_new_memory_over_the_same_store(self):
        store = InMemoryChatMessageHistory()

        first = build_buffer_memory(store)
        first.save_context({"input": "Hello"}, {"answer": "Hi"})

        second = build_buffer_memory(store)
        assert len(second.load_memory_variables({})["chat_history"]) == 2

    def test_clear_forgets_the_conversation(self):
        memory = build_buffer_memory()
        memory.save_context({"input": "Hello"}, {"answer": "Hi"})

        memory.clear()

        assert memory.load_memory_variables({})["chat_history"] == []

    def test_the_history_is_returned_as_messages(self):
        memory = build_buffer_memory()
        memory.save_context({"input": "Hello"}, {"answer": "Hi"})

        assert memory.return_messages is True
        assert isinstance(memory.load_memory_variables({})["chat_history"][0], HumanMessage)

    def test_the_history_can_be_returned_as_a_string(self):
        memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=False,
            output_key="answer",
        )
        memory.save_context({"input": "Hello"}, {"answer": "Hi"})

        history = memory.load_memory_variables({})["chat_history"]
        assert isinstance(history, str)
        assert "Hello" in history
        assert "Hi" in history

    def test_a_missing_question_is_reported(self):
        memory = build_buffer_memory()

        with pytest.raises(ValueError, match="Input key input not found"):
            memory.save_context({}, {"answer": "Hi"})

    def test_a_missing_answer_is_reported(self):
        memory = build_buffer_memory()

        with pytest.raises(ValueError, match="Output key answer not found"):
            memory.save_context({"input": "Hello"}, {})

    def test_the_memory_reports_the_keys_it_adds(self):
        memory = build_buffer_memory()

        assert memory.memory_variables == ["chat_history"]
        assert memory.memory_key == "chat_history"
        assert memory.output_key == "answer"


def test_the_module_does_not_use_the_deprecated_langchain_class():
    """The whole point of the local class: no deprecation warning."""
    import warnings

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        ConversationBufferMemory(
            chat_memory=InMemoryChatMessageHistory(),
            memory_key="chat_history",
            return_messages=True,
            output_key="answer",
        )

    messages = [str(w.message) for w in caught]
    assert not any("ConversationBufferMemory" in message for message in messages)
