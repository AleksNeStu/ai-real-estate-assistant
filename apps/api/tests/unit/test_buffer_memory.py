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


class TestTheKeysOfTheTwoChains:
    """The memory sits on two chains and they name the question differently.

    The retrieval chain saves the question under ``question`` and the answer
    under ``answer``; the agent executor saves them under ``input`` and
    ``output``. The demo answered every question with "Input key input not
    found in inputs" before the memory learned to accept both.
    """

    def test_the_retrieval_chain_saves_the_question_under_question(self):
        memory = build_buffer_memory()

        memory.save_context({"question": "Two rooms in Krakow"}, {"answer": "Here are three."})

        messages = memory.load_memory_variables({})["chat_history"]
        assert messages[0] == HumanMessage(content="Two rooms in Krakow")
        assert messages[1] == AIMessage(content="Here are three.")

    def test_the_agent_executor_saves_the_answer_under_output(self):
        memory = build_buffer_memory()

        memory.save_context({"input": "Two rooms in Krakow"}, {"output": "Here are three."})

        messages = memory.load_memory_variables({})["chat_history"]
        assert messages[0] == HumanMessage(content="Two rooms in Krakow")
        assert messages[1] == AIMessage(content="Here are three.")

    def test_the_retrieval_chain_answers_with_this_memory(self):
        """The whole chain, not a stub of it: the answer comes back."""
        from langchain_core.documents import Document
        from langchain_core.language_models.fake_chat_models import FakeListChatModel
        from langchain_core.retrievers import BaseRetriever

        try:  # langchain 1.x moved the chains into langchain-classic
            from langchain_classic.chains import ConversationalRetrievalChain
        except ImportError:  # pragma: no cover - older layouts
            from langchain.chains import ConversationalRetrievalChain  # type: ignore[no-redef]

        class OneListing(BaseRetriever):
            def _get_relevant_documents(self, query, *, run_manager=None):
                return [Document(page_content="Krakow, 60 m2, 500000 PLN", metadata={"id": "p1"})]

        chain = ConversationalRetrievalChain.from_llm(
            # An empty history is not rephrased, so the first answer of the
            # model is the answer of the chain.
            llm=FakeListChatModel(responses=["A 60 m2 flat for 500000 PLN."]),
            retriever=OneListing(),
            memory=build_buffer_memory(),
            return_source_documents=True,
        )

        answer = chain.invoke({"question": "What is in Krakow?"})

        assert "500000" in answer["answer"]
        assert answer["source_documents"][0].metadata["id"] == "p1"
        # The question and the answer are in the history of the conversation.
        history = chain.memory.load_memory_variables({})["chat_history"]
        assert len(history) == 2


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
