"""The catalogue is a set of listings, and a source of record refreshes its own.

The register publishes the prices people paid and the starosta corrects a
deed where it stands, so the catalogue has to take the newer listing under
the id of the one it holds - a catalogue that kept the old listing would
say the flat was sold for a price the register no longer publishes.

Every other source publishes a snapshot of what it held when it was read,
so a listing it already published stays as it is.
"""

from typing import Optional

import pytest

from data.schemas import Property, PropertyCollection, PropertyType
from services import property_import


def make_property(pid: str = "p1", price: float = 900.0) -> Property:
    """A listing with the fields the catalogue needs."""
    return Property(
        id=pid,
        city="Krakow",
        price=price,
        rooms=2,
        bathrooms=1,
        area_sqm=50,
        property_type=PropertyType.APARTMENT,
        has_parking=True,
        is_furnished=True,
        description="a flat",
    )


class _Catalogue:
    """The cache of the catalogue, held in memory."""

    def __init__(self) -> None:
        self.collection: Optional[PropertyCollection] = None

    def load(self) -> Optional[PropertyCollection]:
        return self.collection

    def save(self, collection: PropertyCollection) -> None:
        self.collection = collection


@pytest.fixture
def catalogue(monkeypatch) -> _Catalogue:
    """The cache of the catalogue, without a file behind it."""
    cache = _Catalogue()
    monkeypatch.setattr(property_import, "load_collection", cache.load)
    monkeypatch.setattr(property_import, "save_collection", cache.save)
    return cache


def test_a_source_of_record_refreshes_the_listing_the_catalogue_holds(catalogue: _Catalogue):
    """The register publishes the flat again with the price it was registered under."""
    catalogue.save(PropertyCollection(properties=[make_property("p1", 900.0)], total_count=1))

    added = property_import.save_imported_properties(
        [make_property("p1", 950.0)], "the register", "register", refresh=True
    )

    # A listing that was refreshed is not a new listing.
    assert added == 0
    assert catalogue.collection is not None
    assert [p.price for p in catalogue.collection.properties] == [950.0]
    assert len(catalogue.collection.properties) == 1


def test_a_source_that_is_not_of_record_leaves_the_listing_as_it_is(catalogue: _Catalogue):
    """A file source publishes a snapshot: the listing that was there stays."""
    catalogue.save(PropertyCollection(properties=[make_property("p1", 900.0)], total_count=1))

    added = property_import.save_imported_properties([make_property("p1", 950.0)], "a file", "file")

    assert added == 0
    assert catalogue.collection is not None
    assert [p.price for p in catalogue.collection.properties] == [900.0]


def test_a_listing_that_is_not_there_yet_is_added(catalogue: _Catalogue):
    """A listing the catalogue does not hold is written beside the others."""
    added = property_import.save_imported_properties(
        [make_property("p1", 900.0), make_property("p2", 700.0)],
        "the register",
        "register",
    )

    assert added == 2
    assert catalogue.collection is not None
    assert len(catalogue.collection.properties) == 2
    assert catalogue.collection.total_count == 2


def test_the_same_listing_twice_is_one_listing(catalogue: _Catalogue):
    """The register reads its sales most recent first, so the first one is the listing."""
    added = property_import.save_imported_properties(
        [make_property("p1", 950.0), make_property("p1", 500.0)],
        "the register",
        "register",
        refresh=True,
    )

    assert added == 1
    assert catalogue.collection is not None
    assert len(catalogue.collection.properties) == 1
    assert catalogue.collection.properties[0].price == 950.0
