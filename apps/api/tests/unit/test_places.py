"""The place pages: the catalogue, the figures and the register behind them.

Task #117: /valuation/{city} and /valuation/{city}/{district} carry the
numbers the official register holds for that place.
"""

from datetime import date, timedelta

import pytest

from data.places import (
    PLACES,
    find_district_by_slug,
    find_place,
    find_place_by_slug,
    place_slug,
)
from data.rcn.rcn_models import RCNAddress, RCNTransaction
from services.rcn_valuation import place_figures


def a_sale(
    *,
    street: str = "FLORIANSKA",
    city: str = "KRAKÓW",
    area: float = 50.0,
    price: float = 500_000.0,
    days_ago: int = 30,
    rooms: int = 2,
) -> RCNTransaction:
    """One registered sale."""
    return RCNTransaction(
        external_id=f"sale-{street}-{days_ago}-{area}",
        teryt="12",
        address=RCNAddress(city=city, street=street, number="17"),
        area_sqm=area,
        price=price,
        transaction_date=date.today() - timedelta(days=days_ago),
        market="rynekWtorny",
        rooms=rooms,
    )


class TestTheCatalogue:
    """The places the site knows."""

    def test_every_city_carries_its_districts(self):
        assert len(PLACES) == 5
        for place in PLACES:
            assert place.districts
            for district in place.districts:
                assert district.streets

    def test_a_place_is_found_by_the_name_the_pages_use(self):
        place = find_place("Kraków")
        assert place is not None
        assert place.name == "Kraków"

    def test_a_place_is_found_by_the_register_s_own_spelling(self):
        place = find_place("WARSZAWA")
        assert place is not None
        assert place.register_city == "WARSZAWA"

    def test_a_place_is_found_by_the_name_the_listings_use(self):
        place = find_place("Warsaw")
        assert place is not None
        assert place.name == "Warszawa"

    def test_a_place_the_site_does_not_know_is_not_guessed(self):
        assert find_place("Atlantis") is None

    def test_the_link_of_a_place_folds_its_diacritics(self):
        assert place_slug("Kraków") == "krakow"
        assert place_slug("Wrocław") == "wroclaw"
        assert place_slug("Gdańsk") == "gdansk"
        assert place_slug("Old Town") == "old-town"
        assert place_slug("Śródmieście") == "srodmiescie"

    def test_a_place_is_found_by_its_link(self):
        place = find_place_by_slug("krakow")
        assert place is not None
        assert place.name == "Kraków"

    def test_a_link_that_names_no_place_is_not_guessed(self):
        assert find_place_by_slug("atlantis") is None

    def test_a_district_is_found_by_its_link(self):
        place = find_place_by_slug("warszawa")
        assert place is not None
        district = find_district_by_slug(place, "srodmiescie")
        assert district is not None
        assert district.name == "Śródmieście"
        assert "Marszałkowska" in district.streets

    def test_a_district_the_city_does_not_have_is_not_guessed(self):
        place = find_place_by_slug("krakow")
        assert place is not None
        assert find_district_by_slug(place, "srodmiescie") is None


class TestTheFigures:
    """What the figures of a place are measured from."""

    def test_the_median_is_the_median_price_per_square_metre(self):
        sales = [
            a_sale(area=50.0, price=500_000.0),
            a_sale(area=50.0, price=600_000.0),
            a_sale(area=50.0, price=700_000.0),
        ]
        figures = place_figures(sales, "Kraków")
        assert figures.median_price_per_sqm == 12_000.0
        assert figures.sample_size == 3

    def test_the_sample_and_the_period_belong_together(self):
        sales = [
            a_sale(days_ago=10),
            a_sale(days_ago=100),
            a_sale(days_ago=200),
        ]
        figures = place_figures(sales, "Kraków")
        assert figures.sample_size == 3
        assert figures.period_start == date.today() - timedelta(days=200)
        assert figures.period_end == date.today() - timedelta(days=10)

    def test_the_comparables_are_the_most_recent_sales(self):
        sales = [a_sale(days_ago=days, price=100_000.0 + days) for days in (10, 40, 80)]
        figures = place_figures(sales, "Kraków")
        assert len(figures.comparables) == 3
        assert figures.comparables[0].transaction_date == date.today() - timedelta(days=10)

    def test_a_capped_sample_says_so(self):
        sales = [a_sale(days_ago=days) for days in (10, 20, 30)]
        figures = place_figures(sales, "Kraków", sample_capped=True)
        assert any("most recent" in note for note in figures.notes)

    def test_a_thin_sample_says_so(self):
        figures = place_figures([a_sale()], "Kraków")
        assert any("too few" in note for note in figures.notes)
        assert figures.confidence == "low"

    def test_a_place_the_register_holds_nothing_for_has_no_figures(self):
        figures = place_figures([], "Atlantis")
        assert figures.has_figures is False
        assert figures.median_price_per_sqm is None
        assert figures.sample_size == 0


async def store_sales(session, sales):
    """Write the given sales into the register's own table."""
    from data.rcn.rcn_models import normalize_text
    from db.models import PropertyTransaction

    rows = []
    for index, sale in enumerate(sales):
        rows.append(
            PropertyTransaction(
                external_id=f"ext-{index}",
                city=sale.address.city,
                city_norm=normalize_text(sale.address.city),
                street=sale.address.street,
                street_norm=normalize_text(sale.address.street),
                number=sale.address.number,
                area_sqm=sale.area_sqm,
                rooms=sale.rooms,
                price_brutto=sale.price,
                transaction_date=sale.transaction_date,
                market_type=sale.market,
            )
        )
    session.add_all(rows)
    await session.commit()


@pytest.mark.asyncio
class TestTheProvider:
    """The register behind the place pages."""

    async def _store(self, session, sales):
        await store_sales(session, sales)

    async def test_a_city_is_measured_from_the_sales_of_the_whole_city(self, db_session):
        from agents.services.valuation import RcnValuationProvider

        await self._store(
            db_session,
            [
                a_sale(street="FLORIANSKA", price=500_000.0),
                a_sale(street="GRODZKA", price=700_000.0),
            ],
        )
        outcome = await RcnValuationProvider(db_session).place_outcome("Kraków")
        assert outcome.sample_size == 2
        assert outcome.comparison_area == "Kraków"
        assert outcome.median_price_per_sqm is not None

    async def test_a_district_is_measured_from_the_sales_of_its_own_streets(self, db_session):
        from agents.services.valuation import RcnValuationProvider

        await self._store(
            db_session,
            [
                a_sale(street="FLORIANSKA", price=500_000.0),
                a_sale(street="GRODZKA", price=700_000.0),
                a_sale(street="BRONOWICKA", price=900_000.0),
            ],
        )
        outcome = await RcnValuationProvider(db_session).place_outcome("Kraków", "Old Town")
        # Floriańska and Grodzka are streets of Kraków's Old Town; Bronowicka
        # is a street of Bronowice and belongs to another comparison.
        assert outcome.sample_size == 2
        assert outcome.district == "Old Town"
        assert outcome.comparison_area == "Old Town, Kraków"

    async def test_a_city_the_register_does_not_know_is_not_guessed(self, db_session):
        from agents.services.valuation import RcnValuationProvider

        outcome = await RcnValuationProvider(db_session).place_outcome("Atlantis")
        assert outcome.has_figures is False
        assert outcome.notes

    async def test_only_the_places_the_register_covers_are_listed(self, db_session):
        """The catalogue names what the register covers - nothing else.

        A city or a district the register holds no sale for has no page, so
        it must not be in the catalogue: the catalogue is what the sitemap
        and the pages link from.
        """
        from agents.services.valuation import RcnValuationProvider

        await self._store(db_session, [a_sale(street="FLORIANSKA", price=500_000.0)])

        covered = await RcnValuationProvider(db_session).covered_places()
        names = [place.name for place, _ in covered]
        assert names == ["Kraków"]

        districts = [district.name for _, districts in covered for district in districts]
        # Floriańska is a street of Kraków's Old Town, and of no other
        # district of it.
        assert districts == ["Old Town"]

    async def test_a_place_the_register_holds_nothing_for_has_no_link(self, db_session):
        from agents.services.valuation import RcnValuationProvider

        await self._store(db_session, [a_sale(street="FLORIANSKA", price=500_000.0)])

        outcome = await RcnValuationProvider(db_session).place_outcome("Kraków")
        assert outcome.districts == ["Old Town"]


@pytest.mark.asyncio
class TestTheEndpoints:
    """The endpoints the pages read."""

    async def _client(self, session):
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        from api.routers import places
        from db.database import get_db

        app = FastAPI()
        app.include_router(places.router, prefix="/api/v1")

        async def override_get_db():
            yield session

        app.dependency_overrides[get_db] = override_get_db
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    async def test_the_catalogue_names_the_places_the_register_covers(self, db_session):
        await store_sales(db_session, [a_sale(street="FLORIANSKA", price=500_000.0)])

        async with await self._client(db_session) as client:
            response = await client.get("/api/v1/places")

        assert response.status_code == 200
        places = response.json()["places"]
        assert [place["slug"] for place in places] == ["krakow"]
        assert [district["slug"] for district in places[0]["districts"]] == ["old-town"]

    async def test_a_place_answers_with_its_figures(self, db_session):
        await store_sales(
            db_session,
            [
                a_sale(street="FLORIANSKA", price=500_000.0),
                a_sale(street="GRODZKA", price=700_000.0),
            ],
        )

        async with await self._client(db_session) as client:
            response = await client.get("/api/v1/places/krakow")

        assert response.status_code == 200
        body = response.json()
        assert body["place"] == "Kraków"
        assert body["sample_size"] == 2
        assert body["registered_count"] == 2
        assert body["median_price_per_sqm"] is not None
        assert body["period_start"] and body["period_end"]
        assert len(body["comparables"]) == 2

    async def test_a_district_answers_with_its_own_figures(self, db_session):
        await store_sales(
            db_session,
            [
                a_sale(street="FLORIANSKA", price=500_000.0),
                a_sale(street="BRONOWICKA", price=900_000.0),
            ],
        )

        async with await self._client(db_session) as client:
            response = await client.get("/api/v1/places/krakow/old-town")

        assert response.status_code == 200
        body = response.json()
        assert body["district"] == "Old Town"
        assert body["district_slug"] == "old-town"
        assert body["sample_size"] == 1
        assert body["comparison_area"] == "Old Town, Kraków"

    async def test_a_place_the_register_holds_nothing_for_has_no_page(self, db_session):
        await store_sales(db_session, [a_sale(street="FLORIANSKA", price=500_000.0)])

        async with await self._client(db_session) as client:
            response = await client.get("/api/v1/places/wroclaw")

        assert response.status_code == 404

    async def test_a_place_the_site_does_not_know_is_not_guessed(self, db_session):
        async with await self._client(db_session) as client:
            response = await client.get("/api/v1/places/atlantis")

        assert response.status_code == 404
