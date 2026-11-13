"""Integration tests for the buyer's memory in the search results (Task #84).

The personalization service held the rule but nothing called it: the memory
reached the answers and nothing else. These tests go through the real search
endpoint, with a stubbed catalogue and the real database, and say what the
buyer sees.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_vector_store
from api.main import app
from core.jwt import create_access_token
from db.database import get_db
from db.models import BuyerMemoryFact, User


def _document(doc_id: str, city: str, price: float) -> MagicMock:
    """One catalogue entry, the way the vector store hands it over."""
    doc = MagicMock()
    doc.page_content = f"A flat in {city}."
    doc.metadata = {
        "id": doc_id,
        "title": f"Flat in {city}",
        "city": city,
        "price": price,
        "currency": "PLN",
        "property_type": "apartment",
        "listing_type": "rent",
        "rooms": 2,
        "latitude": 50.0,
        "longitude": 20.0,
    }
    return doc


@pytest.fixture
async def buyer(db_session: AsyncSession) -> str:
    """A signed-in buyer."""
    user = User(email="search-personalization@example.com", full_name="Buyer")
    db_session.add(user)
    await db_session.flush()
    await db_session.commit()
    return user.id


@pytest.fixture
def catalogue():
    """The catalogue the search returns: one flat in Kraków, one in Warszawa."""
    store = MagicMock()
    # The store's search is synchronous - the router awaits the breaker, not
    # the store.
    store.hybrid_search = MagicMock(
        return_value=[
            (_document("p1", "Kraków", 400000.0), 0.9),
            (_document("p2", "Warszawa", 450000.0), 0.8),
        ]
    )
    return store


@pytest.fixture
async def search_client(db_session: AsyncSession, catalogue):
    """The app, wired to the test database and the stub catalogue."""
    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_vector_store] = lambda: catalogue

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides = previous


def _headers(buyer_id: str | None = None) -> dict[str, str]:
    """The API key, and the buyer's token when there is a buyer."""
    from config.settings import get_settings

    headers = {"X-API-Key": get_settings().api_access_key}
    if buyer_id is not None:
        token = create_access_token(subject=buyer_id, roles=["user"])
        headers["Authorization"] = f"Bearer {token}"
    return headers


class TestTheBuyersMemoryInTheSearch:
    """What the buyer sees in the search results."""

    @pytest.mark.asyncio
    async def test_an_anonymous_visitor_gets_the_whole_catalogue(
        self, search_client, db_session: AsyncSession
    ):
        response = await search_client.post(
            "/api/v1/search", json={"query": "flats"}, headers=_headers()
        )

        assert response.status_code == 200
        assert response.json()["count"] == 2

    @pytest.mark.asyncio
    async def test_a_ruled_out_area_is_not_returned(
        self, search_client, db_session: AsyncSession, buyer: str
    ):
        """A place the buyer ruled out is a filter: it is not returned at all."""
        db_session.add(
            BuyerMemoryFact(
                user_id=buyer,
                kind="ruled_out_area",
                content="Kraków",
                confidence=1.0,
                source="chat",
            )
        )
        await db_session.commit()

        response = await search_client.post(
            "/api/v1/search", json={"query": "flats"}, headers=_headers(buyer)
        )

        assert response.status_code == 200
        cities = [item["property"]["city"] for item in response.json()["results"]]
        assert "Kraków" not in cities
        assert "Warszawa" in cities

    @pytest.mark.asyncio
    async def test_a_buyer_without_facts_gets_the_whole_catalogue(
        self, search_client, db_session: AsyncSession, buyer: str
    ):
        response = await search_client.post(
            "/api/v1/search", json={"query": "flats"}, headers=_headers(buyer)
        )

        assert response.status_code == 200
        assert response.json()["count"] == 2

    @pytest.mark.asyncio
    async def test_a_disliked_listing_is_not_returned(
        self, search_client, db_session: AsyncSession, buyer: str
    ):
        db_session.add(
            BuyerMemoryFact(
                user_id=buyer,
                kind="disliked",
                content="the flat on Orla",
                listing_id="p1",
                confidence=1.0,
                source="chat",
            )
        )
        await db_session.commit()

        response = await search_client.post(
            "/api/v1/search", json={"query": "flats"}, headers=_headers(buyer)
        )

        assert response.status_code == 200
        ids = [item["property"]["id"] for item in response.json()["results"]]
        assert "p1" not in ids
        assert "p2" in ids

    @pytest.mark.asyncio
    async def test_another_buyers_facts_do_not_touch_these_results(
        self, search_client, db_session: AsyncSession, buyer: str
    ):
        """The memory is per buyer: one buyer's rule is not another's."""
        other = User(email="other-search@example.com", full_name="Other")
        db_session.add(other)
        await db_session.flush()
        db_session.add(
            BuyerMemoryFact(
                user_id=other.id,
                kind="ruled_out_area",
                content="Kraków",
                confidence=1.0,
                source="chat",
            )
        )
        await db_session.commit()

        response = await search_client.post(
            "/api/v1/search", json={"query": "flats"}, headers=_headers(buyer)
        )

        assert response.status_code == 200
        assert response.json()["count"] == 2


class TestTheOrderTheBuyerSees:
    """The buyer's own rules change the order - not only the scores."""

    @pytest.mark.asyncio
    async def test_a_liked_listing_comes_first(
        self, search_client, db_session: AsyncSession, buyer: str
    ):
        """The router re-ranks: the liked listing overtakes the other."""
        app.state.response_cache = None
        db_session.add(
            BuyerMemoryFact(
                user_id=buyer,
                kind="liked",
                content="the flat on Orla",
                listing_id="p1",
                confidence=1.0,
                source="chat",
            )
        )
        await db_session.commit()

        # The catalogue brings the other flat first, and only a little ahead.
        app.state.response_cache = None
        store = app.dependency_overrides[get_vector_store]()
        store.hybrid_search.return_value = [
            (_document("p2", "Warszawa", 450000.0), 0.85),
            (_document("p1", "Kraków", 400000.0), 0.84),
        ]

        response = await search_client.post(
            "/api/v1/search", json={"query": "flats"}, headers=_headers(buyer)
        )

        assert response.status_code == 200
        ids = [item["property"]["id"] for item in response.json()["results"]]
        assert ids[0] == "p1"

    @pytest.mark.asyncio
    async def test_a_signed_in_search_is_not_cached(
        self, search_client, db_session: AsyncSession, buyer: str
    ):
        """A rule the buyer has just stated must not wait for the cache.

        The cached answer knows nothing about the memory, so a signed-in
        buyer's search is not cached at all.
        """
        cache = MagicMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock()
        app.state.response_cache = cache

        response = await search_client.post(
            "/api/v1/search", json={"query": "flats"}, headers=_headers(buyer)
        )

        assert response.status_code == 200
        cache.get.assert_not_called()
        cache.set.assert_not_called()
