"""The demo catalogue has to look like a catalogue of homes (Task #35).

The catalogue used to be 250 rows of numbers that were drawn independently
of each other: a 192 m2 loft with one bathroom on the ninth floor of an
eight-floor building. The title, the address and the description never
reached the vector store either, so a visitor saw 250 cards that all said
"Untitled Property".
"""

import pytest

from alembic.demo_data_generator import (
    CITY_PRICE_PER_SQM,
    CITY_RENT_PER_SQM,
    SQ_M_PER_ROOM,
    build_demo_listing,
)
from data.schemas import Property
from vector_store.chroma_store import ChromaPropertyStore

LISTINGS = [build_demo_listing(i) for i in range(300)]


def test_every_listing_has_a_title_an_address_and_a_description():
    for listing in LISTINGS:
        assert listing["title"], "a listing without a title shows as Untitled Property"
        assert listing["address"], "a listing without an address shows no place"
        assert listing["description"], "a listing without a description shows no text"
        assert len(listing["title"]) > 5


def test_the_floor_is_a_floor_of_the_building():
    for listing in LISTINGS:
        assert listing["floor"] >= 1
        assert listing["floor"] <= listing["total_floors"]


def test_the_bathrooms_do_not_outnumber_the_rooms():
    for listing in LISTINGS:
        assert 1 <= listing["bathrooms"] <= listing["rooms"]


def test_the_area_follows_the_number_of_rooms():
    for listing in LISTINGS:
        low, high = SQ_M_PER_ROOM[listing["property_type"]]
        per_room = listing["area_sqm"] / listing["rooms"]
        assert low - 1 <= per_room <= high + 1, (
            f"{listing['property_type']} with {listing['rooms']} rooms "
            f"and {listing['area_sqm']} m2"
        )


def test_the_price_follows_the_area():
    for listing in LISTINGS:
        city = listing["city"]
        if listing["listing_type"] == "sale":
            rate = CITY_PRICE_PER_SQM[city]
        else:
            rate = CITY_RENT_PER_SQM[city]
        actual = listing["price"] / listing["area_sqm"]
        assert rate * 0.8 <= actual <= rate * 1.25, (
            f"{listing['price']} PLN for {listing['area_sqm']} m2 in {city} "
            f"({actual:.0f} per m2, expected about {rate})"
        )


def test_the_amenities_follow_the_building():
    for listing in LISTINGS:
        if listing["total_floors"] < 4:
            assert not listing["has_elevator"]
        if listing["floor"] == 1:
            assert not listing["has_balcony"]
        if listing["property_type"] not in ("house", "townhouse"):
            assert not listing["has_garden"]


def test_the_description_names_the_listing():
    for listing in LISTINGS[:50]:
        assert listing["title"] in listing["description"]
        assert listing["city"] in listing["description"]


def test_the_search_text_leads_with_the_title_and_the_address():
    listing = LISTINGS[0]
    prop = Property.model_validate(listing)
    text = prop.to_search_text()
    assert listing["title"] in text
    assert listing["address"] in text
    assert f"Property in {listing['city']}" in text


def test_the_vector_store_keeps_the_title_the_address_and_the_description():
    listing = LISTINGS[0]
    prop = Property.model_validate(listing)
    document = ChromaPropertyStore.property_to_document(None, prop)  # type: ignore[arg-type]

    assert document.metadata["title"] == listing["title"]
    assert document.metadata["address"] == listing["address"]
    assert document.metadata["description"] == listing["description"]
    assert document.metadata["floor"] == listing["floor"]
    assert document.metadata["total_floors"] == listing["total_floors"]


def test_a_listing_without_a_title_still_reaches_the_store():
    """A listing of another source may carry no title - it must not break."""
    prop = Property(
        id="prop-x",
        city="Krakow",
        price=1000,
        currency="PLN",
        property_type="apartment",
        listing_type="rent",
    )
    document = ChromaPropertyStore.property_to_document(None, prop)  # type: ignore[arg-type]

    assert "title" not in document.metadata
    assert "address" not in document.metadata
    assert document.page_content.startswith("Property in Krakow")


@pytest.mark.parametrize("index", [0, 1, 2])
def test_the_listing_validates(index):
    prop = Property.model_validate(build_demo_listing(index))
    assert prop.city
    assert prop.price and prop.price > 0
