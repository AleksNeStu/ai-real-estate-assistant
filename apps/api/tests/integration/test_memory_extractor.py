"""Integration tests for the buyer-memory extractor (Task #78).

The unit tests cover the extractor's parsing rules against a mock model. These
go one step further: they run the extractor against a stub model, write what it
produced through the real service, and read it back from the real database.
That is the path the chat write path (Task #79) will take.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from agents.memory_extractor import extract_buyer_facts
from api.dependencies import get_buyer_memory_service
from db.models import User
from services.buyer_memory_service import BuyerMemoryService

MESSAGES = [{"role": "user", "content": "I do not want Krakow, and my budget is 400k PLN."}]


class StubModel:
    """A chat model that answers with a fixed payload.

    It carries the one method the extractor uses - ``invoke`` - so a change in
    the extractor that reaches for anything else fails loudly here.
    """

    def __init__(self, payload: str) -> None:
        self.payload = payload
        self.calls: list[str] = []

    def invoke(self, prompt: str):
        self.calls.append(prompt)
        return type("Answer", (), {"content": self.payload})()


class FailingModel:
    """A chat model whose provider is down."""

    def invoke(self, prompt: str):
        raise RuntimeError("provider is down")


@pytest.fixture
async def buyer(db_session: AsyncSession) -> str:
    """A signed-in buyer."""
    user = User(email="extractor@example.com", full_name="Extractor")
    db_session.add(user)
    await db_session.flush()
    await db_session.commit()
    return user.id


@pytest.fixture
def service(db_session: AsyncSession) -> BuyerMemoryService:
    """The service, wired the way a router wires it."""
    return get_buyer_memory_service(db_session)


class TestExtractionIntoTheDatabase:
    """What the extractor produced, written and read back."""

    @pytest.mark.asyncio
    async def test_the_extracted_facts_are_stored_and_recalled(self, service, buyer):
        model = StubModel(
            '[{"kind": "budget", "content": "400000 PLN", "confidence": 0.9},'
            ' {"kind": "ruled_out_area", "content": "Krakow"}]'
        )

        facts = await extract_buyer_facts(MESSAGES, "Here are some flats.", (), llm=model)

        assert [fact.kind for fact in facts] == ["budget", "ruled_out_area"]

        for fact in facts:
            await service.record_fact(
                user_id=buyer,
                kind=fact.kind,
                content=fact.content,
                source="chat",
            )

        recalled = await service.recall_for_user(buyer)
        assert {fact.content for fact in recalled} == {"400000 PLN", "Krakow"}

    @pytest.mark.asyncio
    async def test_a_prose_answer_stores_nothing(self, service, buyer):
        model = StubModel("I found three apartments in Krakow for you.")

        facts = await extract_buyer_facts(MESSAGES, "Here are some flats.", (), llm=model)

        assert facts == []
        assert await service.recall_for_user(buyer) == []

    @pytest.mark.asyncio
    async def test_a_failing_provider_stores_nothing(self, service, buyer):
        facts = await extract_buyer_facts(MESSAGES, "Here are some flats.", (), llm=FailingModel())

        assert facts == []
        assert await service.recall_for_user(buyer) == []

    @pytest.mark.asyncio
    async def test_the_prompt_carries_the_turn_and_the_listings(self):
        model = StubModel("[]")

        await extract_buyer_facts(
            MESSAGES,
            "Here are some flats.",
            [{"id": "abc", "title": "A flat in Krakow"}],
            llm=model,
        )

        prompt = model.calls[0]
        assert "I do not want Krakow" in prompt
        assert "listing_id=abc" in prompt
