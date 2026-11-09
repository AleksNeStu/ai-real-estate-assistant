"""What the catalogue endpoint reports.

The landing page states how many properties, in how many cities, with how many
agents. Those numbers have to come from the catalogue itself: a page that
hardcodes them starts lying the moment the seed changes. This test pins the
shape of the answer - the totals, the city breakdown and the order the cities
come in.
"""

from unittest.mock import patch

import pytest
from sqlalchemy import select

from api.routers import catalogue
from data.schemas import Property, PropertyCollection, PropertyType
from db.models import AgentProfile, User


def _property(city: str, price: float, currency: str = "PLN") -> Property:
    return Property(
        id=f"prop-{city}-{price}",
        city=city,
        rooms=2,
        bathrooms=1,
        price=price,
        area_sqm=50,
        has_parking=False,
        has_garden=False,
        property_type=PropertyType.APARTMENT,
        source_url="http://example.com/x",
        currency=currency,
    )


def _collection(*properties: Property) -> PropertyCollection:
    return PropertyCollection(
        properties=list(properties),
        total_count=len(properties),
        source="test",
    )


class TestCatalogueStats:
    """The live numbers of the catalogue."""

    async def test_reports_the_properties_the_cities_and_the_currencies(self, db_session):
        collection = _collection(
            _property("Kraków", 500000),
            _property("Kraków", 400000),
            _property("Warsaw", 300000, "EUR"),
        )

        with patch.object(catalogue, "load_collection", return_value=collection):
            stats = await catalogue.catalogue_stats(session=db_session)

        assert stats.total == 3
        assert [city.name for city in stats.cities] == ["Kraków", "Warsaw"]
        assert [city.count for city in stats.cities] == [2, 1]
        assert stats.currencies == ["EUR", "PLN"]

    async def test_the_cities_come_in_by_count_then_by_name(self, db_session):
        """Two cities with the same count are ordered by name, not by luck."""
        collection = _collection(
            _property("Wrocław", 400000),
            _property("Gdańsk", 400000),
            _property("Poznań", 500000),
        )

        with patch.object(catalogue, "load_collection", return_value=collection):
            stats = await catalogue.catalogue_stats(session=db_session)

        # Every city holds one property, so the count ties and the name
        # decides - the price does not enter into it.
        assert [city.name for city in stats.cities] == ["Gdańsk", "Poznań", "Wrocław"]
        assert [city.count for city in stats.cities] == [1, 1, 1]

    async def test_an_empty_catalogue_answers_with_zeros_not_an_error(self, db_session):
        """A deployment with no seed must still render the landing."""
        with patch.object(catalogue, "load_collection", return_value=None):
            stats = await catalogue.catalogue_stats(session=db_session)

        assert stats.total == 0
        assert stats.cities == []
        assert stats.currencies == []

    async def test_counts_the_agents_in_the_database(self, db_session):
        """The agent count is the live one, not a number from the seed file."""
        for index in range(2):
            user = User(email=f"agent-{index}@example.com", role="agent")
            db_session.add(user)
            await db_session.flush()
            db_session.add(AgentProfile(user_id=user.id, agency_name="Test Agency"))
        await db_session.commit()

        with patch.object(catalogue, "load_collection", return_value=_collection()):
            stats = await catalogue.catalogue_stats(session=db_session)

        assert stats.agents == 2

    async def test_the_currencies_are_the_listing_currencies(self, db_session):
        """A listing's own currency is reported, so the landing can say so."""
        collection = _collection(
            _property("Kraków", 500000, "PLN"),
            _property("London", 900000, "GBP"),
        )

        with patch.object(catalogue, "load_collection", return_value=collection):
            stats = await catalogue.catalogue_stats(session=db_session)

        assert stats.currencies == ["GBP", "PLN"]


class TestTheVectorStoreIsTheCatalogue:
    """The numbers come from the store the search answers with."""

    async def test_the_store_wins_over_the_cache_file(self, db_session):
        """A deployment that seeded its vector store reports the seeded numbers."""
        store = _FakeStore(
            total=2,
            metadatas=[
                {"city": "Kraków", "currency": "PLN"},
                {"city": "Kraków", "currency": "PLN"},
            ],
        )

        with patch.object(catalogue, "load_collection", return_value=_collection()):
            stats = await catalogue.catalogue_stats(session=db_session, store=store)

        assert stats.total == 2
        assert [city.name for city in stats.cities] == ["Kraków"]
        assert stats.currencies == ["PLN"]

    async def test_an_empty_store_falls_back_to_the_cache_file(self, db_session):
        """A deployment with a catalogue file and no store still reports numbers."""
        collection = _collection(_property("Warsaw", 300000))

        with patch.object(catalogue, "load_collection", return_value=collection):
            stats = await catalogue.catalogue_stats(session=db_session, store=_FakeStore())

        assert stats.total == 1
        assert [city.name for city in stats.cities] == ["Warsaw"]


class _FakeCollection:
    def __init__(self, total: int, metadatas: list[dict]) -> None:
        self._total = total
        self._metadatas = metadatas

    def count(self) -> int:
        return self._total

    def get(self, include=None, limit=None):
        return {"metadatas": self._metadatas}


class _FakeStore:
    """The shape of the vector store the endpoint reads."""

    def __init__(self, total: int = 0, metadatas: list[dict] | None = None) -> None:
        self.vector_store = _FakeVectorStore(_FakeCollection(total, metadatas or []))


class _FakeVectorStore:
    """The LangChain Chroma wrapper: the collection hangs under it."""

    def __init__(self, collection) -> None:
        self._collection = collection


@pytest.mark.parametrize("total", [0, 1, 7])
async def test_the_total_is_never_hardcoded(total, db_session):
    """Whatever the catalogue holds, the total is that number."""
    properties = tuple(_property(f"City{index}", 100000 * (index + 1)) for index in range(total))

    with patch.object(catalogue, "load_collection", return_value=_collection(*properties)):
        stats = await catalogue.catalogue_stats(session=db_session)

    assert stats.total == total


async def test_the_agent_count_is_read_from_the_table(db_session):
    """The count comes from the agents table, not from the property list."""
    rows = (await db_session.execute(select(AgentProfile))).scalars().all()
    assert len(rows) == 0

    with patch.object(catalogue, "load_collection", return_value=_collection()):
        stats = await catalogue.catalogue_stats(session=db_session)

    assert stats.agents == 0
