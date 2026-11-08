import uuid

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from ai.buffer_memory import ConversationBufferMemory
from ai.memory import get_session_history

# Use a file-based DB for this test to ensure persistence works on disk,
# or use :memory: if we just want to test logic.
# Given the code uses a global connection string, we should probably mock it
# or ensure it points to a test DB.
# The code in ai/memory.py uses `sqlite:///./chat_history.db`.
# We should probably patch the connection string for the test to avoid polluting the real DB.


@pytest.fixture
def test_db_path(tmp_path):
    # Create a temporary DB file
    db_file = tmp_path / "test_chat_history.db"
    return str(db_file)


@pytest.fixture
def mock_get_session_history(test_db_path):
    # We need to patch the CONNECTION_STRING in ai.memory, but it's a global variable.
    # Alternatively, we can just instantiate SQLChatMessageHistory directly with our test string
    # if we want to test the class, or patch the variable if we want to test get_session_history.

    # Let's test the helper function by patching the connection string used inside it.
    # Since get_session_history uses a global constant, let's patch the constant in the module.

    with pytest.MonkeyPatch.context() as m:
        test_conn_string = f"sqlite:///{test_db_path}"
        m.setattr("ai.memory.CONNECTION_STRING", test_conn_string)
        yield


def test_session_persistence_end_to_end(mock_get_session_history):
    """
    Test that messages added to one memory instance are visible to another
    instance with the same session_id.
    """
    session_id = str(uuid.uuid4())

    # 1. Simulate First Request: Create memory and add messages
    history1 = get_session_history(session_id)
    memory1 = ConversationBufferMemory(
        chat_memory=history1, memory_key="chat_history", return_messages=True
    )

    # Add context manually (simulating a conversation turn)
    memory1.chat_memory.add_user_message("Hello, I am looking for a house.")
    memory1.chat_memory.add_ai_message("I can help with that. What is your budget?")

    # 2. Simulate Second Request: Create NEW memory instance with SAME session_id
    history2 = get_session_history(session_id)
    memory2 = ConversationBufferMemory(
        chat_memory=history2, memory_key="chat_history", return_messages=True
    )

    # Load memory variables
    context = memory2.load_memory_variables({})
    messages = context["chat_history"]

    # Verify messages persisted
    assert len(messages) == 2
    assert isinstance(messages[0], HumanMessage)
    assert messages[0].content == "Hello, I am looking for a house."
    assert isinstance(messages[1], AIMessage)
    assert messages[1].content == "I can help with that. What is your budget?"


def test_multiple_sessions_isolation(mock_get_session_history):
    """
    Test that different session IDs have isolated histories.
    """
    session1 = str(uuid.uuid4())
    session2 = str(uuid.uuid4())

    # Session 1
    hist1 = get_session_history(session1)
    hist1.add_user_message("Message for session 1")

    # Session 2
    hist2 = get_session_history(session2)
    hist2.add_user_message("Message for session 2")

    # Verify Session 1
    msgs1 = get_session_history(session1).messages
    assert len(msgs1) == 1
    assert msgs1[0].content == "Message for session 1"

    # Verify Session 2
    msgs2 = get_session_history(session2).messages
    assert len(msgs2) == 1
    assert msgs2[0].content == "Message for session 2"
