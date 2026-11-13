"""Integration tests for the chat path's buyer memory (Task #79).

The chat path READS the buyer's memory (the answer uses what the buyer has
already told us) and WRITES it (the turn teaches the memory). These tests run
the real router against a stub model and a stub agent: no provider is called
and no answer is produced by a real model.
"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.chat_history import BaseChatMessageHistory
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_api_key
from api.dependencies import get_llm, get_vector_store
from api.main import app
from config.settings import get_settings
from core.jwt import create_access_token
from db.database import get_db
from db.models import User
from services.buyer_memory_service import BuyerMemoryService

# The facts the stub model reads out of the turn.
EXTRACTED_FACTS = [
    {"kind": "budget", "content": "400000 PLN", "confidence": 0.9},
    {"kind": "ruled_out_area", "content": "Krakow"},
]


class StubModel:
    """A chat model that answers the extraction with a fixed payload.

    It carries the one method the extractor uses - ``invoke`` - so a change in
    the extractor that reaches for anything else fails loudly here.
    """

    def __init__(self, payload: str) -> None:
        self.payload = payload
        self.calls: list[str] = []

    def invoke(self, prompt: str):
        self.calls.append(prompt)
        return type("Answer", (), {"content": self.payload})()


class FakeAgent:
    """The agent, with the memory it was given."""

    def __init__(self, answer: str = "Here are three flats in Warsaw.") -> None:
        self.answer = answer
        self.calls: list[dict] = []

    def process_query(self, message, **kwargs):
        self.calls.append({"message": message, "kwargs": kwargs})
        return {"answer": self.answer, "source_documents": []}


class StreamingFakeAgent(FakeAgent):
    """The agent on the streaming path, which yields JSON envelopes."""

    def __init__(self, answer: str = "Here are three flats in Warsaw.", documents=()) -> None:
        super().__init__(answer)
        # The real agent keeps the documents its answer was built from; the
        # streaming generator yields strings only, so this is the only way the
        # caller learns what the buyer was shown.
        self.last_source_documents = list(documents)

    async def astream_query(self, message, **kwargs):
        self.calls.append({"message": message, "kwargs": kwargs})
        for piece in ("Here are ", "three flats in Warsaw."):
            yield json.dumps({"content": piece})


class MockHistory(BaseChatMessageHistory):
    """A session history that needs no Redis."""

    messages = []

    def add_message(self, message):
        pass

    def clear(self):
        pass


@pytest.fixture
async def buyer(db_session: AsyncSession) -> str:
    """A signed-in buyer."""
    user = User(email="chat-memory@example.com", full_name="Buyer")
    db_session.add(user)
    await db_session.flush()
    await db_session.commit()
    return user.id


@pytest.fixture
def buyer_headers(buyer: str) -> dict[str, str]:
    """The headers of a signed-in buyer."""
    token = create_access_token(subject=buyer, roles=["user"])
    settings = get_settings()
    return {
        "Authorization": f"Bearer {token}",
        "X-API-Key": settings.api_access_key,
    }


@pytest.fixture
def anonymous_headers() -> dict[str, str]:
    """The headers of a visitor who did not sign in."""
    settings = get_settings()
    return {"X-API-Key": settings.api_access_key}


@pytest.fixture
def model() -> StubModel:
    """The model the chat path resolves - one provider, never a second one."""
    return StubModel(json.dumps(EXTRACTED_FACTS))


@pytest.fixture
async def chat_client(db_session: AsyncSession, model: StubModel):
    """The app, wired to the test database and a stub model."""
    mock_store = MagicMock()
    mock_store.get_retriever.return_value = MagicMock()

    async def override_get_db():
        yield db_session

    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_llm] = lambda: model
    app.dependency_overrides[get_vector_store] = lambda: mock_store
    app.dependency_overrides[get_api_key] = lambda: "test-key"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides = previous


@pytest.fixture
def agent_patch():
    """The agent the chat path builds, and the session history it uses."""
    agent = FakeAgent()

    with patch("api.routers.chat.create_hybrid_agent", lambda **_: agent):
        with patch("ai.memory.get_session_history", lambda _session_id: MockHistory()):
            yield agent


class TestTheWritePath:
    """What the turn taught the memory."""

    async def test_a_signed_in_turn_persists_the_extracted_facts(
        self, chat_client, agent_patch, buyer, buyer_headers
    ):
        response = await chat_client.post(
            "/api/v1/chat",
            json={"message": "I do not want Krakow, and my budget is 400k PLN."},
            headers=buyer_headers,
        )

        assert response.status_code == 200
        assert response.json()["response"] == "Here are three flats in Warsaw."

    async def test_the_facts_are_read_back_from_the_database(
        self, chat_client, agent_patch, db_session, buyer, buyer_headers
    ):
        response = await chat_client.post(
            "/api/v1/chat",
            json={"message": "I do not want Krakow, and my budget is 400k PLN."},
            headers=buyer_headers,
        )
        assert response.status_code == 200

        service = BuyerMemoryService(db_session)
        recalled = await service.recall_for_user(buyer)

        assert {fact.content for fact in recalled} == {"400000 PLN", "Krakow"}
        assert {fact.kind for fact in recalled} == {"budget", "ruled_out_area"}
        assert {fact.source for fact in recalled} == {"chat"}

    async def test_the_extraction_reads_the_turn_and_the_answer(
        self, chat_client, agent_patch, model, buyer_headers
    ):
        await chat_client.post(
            "/api/v1/chat",
            json={"message": "I do not want Krakow, and my budget is 400k PLN."},
            headers=buyer_headers,
        )

        # The model the chat path resolved is the model that read the turn.
        assert len(model.calls) == 1
        prompt = model.calls[0]
        assert "I do not want Krakow" in prompt
        assert "Here are three flats in Warsaw." in prompt

    async def test_an_anonymous_turn_persists_nothing(
        self, chat_client, agent_patch, model, db_session, buyer, anonymous_headers
    ):
        response = await chat_client.post(
            "/api/v1/chat",
            json={"message": "I do not want Krakow, and my budget is 400k PLN."},
            headers=anonymous_headers,
        )

        assert response.status_code == 200

        # Nothing was extracted at all - an anonymous turn teaches nothing.
        assert model.calls == []

        service = BuyerMemoryService(db_session)
        assert await service.recall_for_user(buyer) == []

    async def test_a_raising_extractor_still_answers(self, chat_client, agent_patch, buyer_headers):
        async def raising_extractor(**_kwargs):
            raise RuntimeError("the extractor is down")

        with patch("api.routers.chat.extract_buyer_facts", raising_extractor):
            response = await chat_client.post(
                "/api/v1/chat",
                json={"message": "I do not want Krakow, and my budget is 400k PLN."},
                headers=buyer_headers,
            )

        assert response.status_code == 200
        assert response.json()["response"] == "Here are three flats in Warsaw."


class TestTheReadPath:
    """What the memory gave to the answer."""

    async def test_the_answer_carries_the_memory_block(
        self, chat_client, agent_patch, db_session, buyer, buyer_headers
    ):
        service = BuyerMemoryService(db_session)
        await service.record_fact(
            user_id=buyer,
            kind="budget",
            content="400000 PLN",
            source="manual",
        )

        response = await chat_client.post(
            "/api/v1/chat",
            json={"message": "Show me what I can afford."},
            headers=buyer_headers,
        )

        assert response.status_code == 200

        call = agent_patch.calls[0]
        assert "400000 PLN" in call["kwargs"]["buyer_memory"]

    async def test_an_anonymous_turn_gets_no_memory(
        self, chat_client, agent_patch, anonymous_headers
    ):
        response = await chat_client.post(
            "/api/v1/chat",
            json={"message": "Show me what I can afford."},
            headers=anonymous_headers,
        )

        assert response.status_code == 200

        call = agent_patch.calls[0]
        assert call["kwargs"].get("buyer_memory") is None


class TestTheStreamingPath:
    """The streamed answer reaches the extractor as prose.

    The agent streams JSON envelopes (``{"content": "..."}``). The extractor
    reads the ANSWER, so handing it the envelopes would make it reason over
    JSON fragments.
    """

    async def test_the_extraction_reads_the_prose_and_not_the_envelopes(
        self, chat_client, model, buyer_headers
    ):
        agent = StreamingFakeAgent()

        with patch("api.routers.chat.create_hybrid_agent", lambda **_: agent):
            with patch("ai.memory.get_session_history", lambda _session_id: MockHistory()):
                response = await chat_client.post(
                    "/api/v1/chat",
                    json={
                        "message": "I do not want Krakow, and my budget is 400k PLN.",
                        "stream": True,
                    },
                    headers=buyer_headers,
                )

        assert response.status_code == 200

        assert len(model.calls) == 1
        prompt = model.calls[0]
        assert "Here are three flats in Warsaw." in prompt
        assert '{"content"' not in prompt

    async def test_a_listing_the_answer_used_is_kept(
        self, chat_client, db_session, buyer, buyer_headers
    ):
        """A listing the buyer read in the prose can be spoken about.

        The streaming path used to validate a listing fact against the
        citations alone - a second, independent retrieval - so a fact about
        the listing the answer was built from was dropped as "unknown
        listing" while the same fact survived on the non-streaming path.
        """
        document = SimpleNamespace(metadata={"id": "listing-1", "title": "Flat on Orla"})
        agent = StreamingFakeAgent(documents=[document])
        liking_model = StubModel(
            json.dumps(
                [{"kind": "liked", "content": "the balcony flat", "listing_id": "listing-1"}]
            )
        )
        app.dependency_overrides[get_llm] = lambda: liking_model

        with patch("api.routers.chat.create_hybrid_agent", lambda **_: agent):
            with patch("ai.memory.get_session_history", lambda _session_id: MockHistory()):
                response = await chat_client.post(
                    "/api/v1/chat",
                    json={
                        "message": "I like the flat on Orla.",
                        "stream": True,
                    },
                    headers=buyer_headers,
                )

        assert response.status_code == 200

        service = BuyerMemoryService(db_session)
        recalled = await service.recall_for_user(buyer)
        assert [fact.content for fact in recalled] == ["the balcony flat"]
        assert recalled[0].listing_id == "listing-1"
