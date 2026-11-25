"""A source of record writes its newer listing over the one the catalogue holds.

The catalogue has two homes: the Chroma collection the product reads, and the
JSON cache a reindex rebuilds the collection from. The register is the source
of record for the price of a deed - the starosta corrects a deed where it
stands and the register publishes the flat again - so a deed the register
corrects has to reach both of them, and the two have to say the same thing
about it.

This test drives the real store and the real cache. The only things replaced
are the embeddings - a stand-in, so the test needs no model and no network -
and the place the cache lives.
"""

from unittest.mock import MagicMock, patch

import pytest

from data.schemas import Property
from services.property_import import save_imported_properties
from utils import property_cache
from vector_store.chroma_store import ChromaPropertyStore

DEED_ID = "rcn-18806-2026"
REGISTERED_PRICE = 790_000.0
CORRECTED_PRICE = 812_500.0

# The id of a second listing, used where a test needs the cache to hold more
# than one listing.
OTHER_ID = "rcn-18807-2026"


def _listing(price: float, listing_id: str = DEED_ID) -> Property:
    """A listing of the register: a flat that changed hands at a price."""
    return Property(
        id=listing_id,
        title="Flat on Bronowicka",
        description="A flat that changed hands at the price the register published.",
        city="Kraków",
        district="Bronowice",
        property_type="apartment",
        listing_type="sale",
        rooms=3.0,
        area_sqm=64.0,
        price=price,
        currency="PLN",
    )


@pytest.fixture
def store(tmp_path, monkeypatch) -> ChromaPropertyStore:
    """The real store, with a stand-in for the embeddings.

    The store is the real one - a real Chroma collection - and the embeddings
    are a stand-in, so the test needs neither a model nor a network. The
    embedding is forced on, because the store keeps its distance from the
    fastembed model on Windows otherwise, and a test that behaves differently
    on two platforms is a test that proves nothing.

    The persistence is forced on for the same reason. Without it the store
    falls back to an in-memory collection, and every store in the process
    shares that one collection - so the deed the previous test wrote is
    still in it when this test starts, and the test reads the previous
    test's price instead of the one it wrote. The directory of the test is
    the collection's own, so each test reads and writes its own catalogue.
    """
    monkeypatch.setenv("CHROMA_FORCE_FASTEMBED", "1")
    monkeypatch.setenv("CHROMA_FORCE_PERSIST", "1")
    fake_embeddings = MagicMock()
    fake_embeddings.embed_documents.side_effect = lambda texts: [[0.1] * 384 for _ in texts]
    fake_embeddings.embed_query.return_value = [0.1] * 384
    with patch("vector_store.chroma_store._FastEmbedEmbeddings", return_value=fake_embeddings):
        return ChromaPropertyStore(persist_directory=str(tmp_path / "chroma_db"))


@pytest.fixture
def cache(tmp_path, monkeypatch):
    """The real cache, in the temporary directory of the test."""
    cache_dir = tmp_path / "app_cache"
    monkeypatch.setattr(property_cache, "CACHE_DIR", cache_dir)
    monkeypatch.setattr(property_cache, "CACHE_FILE", cache_dir / "properties.json")
    monkeypatch.setattr(property_cache, "PREV_CACHE_FILE", cache_dir / "properties_prev.json")
    return cache_dir


def _cached_price(listing_id: str = DEED_ID) -> float:
    """The price the cache carries for a listing."""
    cached = property_cache.load_collection()
    assert cached is not None
    listings = [p for p in cached.properties if p.id == listing_id]
    assert len(listings) == 1, f"the listing is not one listing: {len(listings)}"
    return float(listings[0].price or 0)


def _collection_price(store: ChromaPropertyStore, listing_id: str = DEED_ID) -> float:
    """The price the collection carries for a listing."""
    documents = store.get_properties_by_ids([listing_id])
    assert len(documents) == 1, f"the listing is not one listing: {len(documents)}"
    return float(documents[0].metadata.get("price") or 0)


def test_the_corrected_deed_replaces_the_listing_in_the_collection(store):
    """The register publishes the flat again - the collection carries the new price."""
    store.add_properties([_listing(REGISTERED_PRICE)])
    assert _collection_price(store) == REGISTERED_PRICE

    # The starosta corrects the deed where it stands, and the register
    # publishes the flat again with the price it was registered under.
    added = store.add_properties([_listing(CORRECTED_PRICE)], refresh=True)

    # The listing was there before, so it is not a new one.
    assert added == 0
    assert _collection_price(store) == CORRECTED_PRICE

    # And the collection holds one listing, not two.
    assert len(store.get_properties_by_ids([DEED_ID])) == 1


def test_the_same_listing_twice_is_one_listing(store):
    """The register reads its sales most recent first - the first one is the listing."""
    added = store.add_properties([_listing(REGISTERED_PRICE), _listing(CORRECTED_PRICE)])

    assert added == 1
    assert len(store.get_properties_by_ids([DEED_ID])) == 1
    # The first one of the two is the listing.
    assert _collection_price(store) == REGISTERED_PRICE


def test_the_store_writes_the_newer_listing_over_the_one_it_holds(store):
    """A listing of record is written under the id of the listing the store holds."""
    store.add_properties([_listing(REGISTERED_PRICE)])
    store.add_properties([_listing(CORRECTED_PRICE)], refresh=True)

    # The collection holds one listing, under the id of the deed.
    ids = store.vector_store._collection.get(include=[]).get("ids", [])
    assert ids == [DEED_ID]
    assert _collection_price(store) == CORRECTED_PRICE


def test_the_store_without_a_collection_refreshes_its_cache(store):
    """A deployment whose collection is unavailable still offers the new price.

    The cache is what the store falls back to, so a listing that was
    refreshed has to be refreshed in it too.
    """
    # The collection is unreachable: the store keeps the listings in its cache.
    store.vector_store = None
    store._vector_store_local.store = None

    store.add_properties([_listing(REGISTERED_PRICE)])
    store.add_properties([_listing(CORRECTED_PRICE)], refresh=True)

    cached = [doc for doc in store._documents if doc.metadata.get("id") == DEED_ID]
    assert len(cached) == 1
    assert float(cached[0].metadata.get("price") or 0) == CORRECTED_PRICE


def test_the_store_without_embeddings_writes_the_newer_listing_over_the_one_it_holds(store):
    """A store that embeds nothing still writes the newer listing in its place."""
    store.add_properties([_listing(REGISTERED_PRICE)])

    # The deployment that cannot embed keeps the collection and writes the
    # listing without a vector of its own.
    store.embeddings = None
    store.add_properties([_listing(CORRECTED_PRICE)], refresh=True)

    assert _collection_price(store) == CORRECTED_PRICE
    ids = store.vector_store._collection.get(include=[]).get("ids", [])
    assert ids == [DEED_ID]


def test_a_listing_the_cache_holds_under_another_place_is_found_by_its_id(store):
    """The store finds a listing by its id when the place it remembers is wrong."""
    store.add_properties([_listing(REGISTERED_PRICE), _listing(700_000.0, OTHER_ID)])

    # The place the store remembers names the other listing.
    store._doc_positions[DEED_ID] = 1

    store.add_properties([_listing(CORRECTED_PRICE)], refresh=True)

    cached = [doc for doc in store._documents if doc.metadata.get("id") == DEED_ID]
    assert len(cached) == 1
    assert float(cached[0].metadata.get("price") or 0) == CORRECTED_PRICE
    # The other listing is where it was.
    other = [doc for doc in store._documents if doc.metadata.get("id") == OTHER_ID]
    assert float(other[0].metadata.get("price") or 0) == 700_000.0


def test_a_listing_that_came_in_by_another_road_is_found_by_its_id(store):
    """A listing the cache holds without a place of its own is found anyway."""
    store.add_properties([_listing(REGISTERED_PRICE)])
    store._doc_positions.pop(DEED_ID, None)

    store.add_properties([_listing(CORRECTED_PRICE)], refresh=True)

    cached = [doc for doc in store._documents if doc.metadata.get("id") == DEED_ID]
    assert len(cached) == 1
    assert float(cached[0].metadata.get("price") or 0) == CORRECTED_PRICE


def test_a_listing_the_cache_holds_the_id_of_but_not_the_listing_is_left_alone(store):
    """A listing that is not in the cache is not put into it beside the others."""
    store.add_properties([_listing(REGISTERED_PRICE)])

    # The cache holds the id of the listing, but not the listing itself.
    store._documents = [doc for doc in store._documents if doc.metadata.get("id") != DEED_ID]

    store.add_properties([_listing(CORRECTED_PRICE)], refresh=True)

    # The cache does not grow: a listing it does not hold is not added to it
    # beside the others.
    assert [doc for doc in store._documents if doc.metadata.get("id") == DEED_ID] == []


def test_the_store_forgets_the_places_of_its_listings_when_it_is_cleared(store):
    """The store starts empty - no listing and no place of a listing."""
    store.add_properties([_listing(REGISTERED_PRICE)])
    assert store._doc_positions

    store.clear()

    assert store._documents == []
    assert store._doc_ids == set()
    assert store._doc_positions == {}


def test_the_store_forgets_its_cache_even_when_the_collection_cannot_be_cleared(store, monkeypatch):
    """A collection that cannot be cleared does not keep the cache alive."""
    store.add_properties([_listing(REGISTERED_PRICE)])

    def _unreachable():
        raise RuntimeError("the collection cannot be reached")

    monkeypatch.setattr(store, "_get_vector_store", _unreachable)

    store.clear()

    assert store._documents == []
    assert store._doc_positions == {}


def test_the_cache_carries_the_price_the_register_publishes(cache):
    """The cache is the catalogue's record - a corrected deed reaches it."""
    added = save_imported_properties([_listing(REGISTERED_PRICE)], "the register", "register")
    assert added == 1
    assert _cached_price() == REGISTERED_PRICE

    # The register publishes the flat again with the corrected price.
    added = save_imported_properties(
        [_listing(CORRECTED_PRICE)], "the register", "register", refresh=True
    )

    # A listing that was there before is not a new one.
    assert added == 0
    assert _cached_price() == CORRECTED_PRICE

    # The catalogue is a set of listings.
    cached = property_cache.load_collection()
    assert cached is not None
    assert len(cached.properties) == 1


def test_the_same_listing_twice_is_one_listing_in_the_cache(cache):
    """The same listing twice in one import is one listing."""
    added = save_imported_properties(
        [_listing(REGISTERED_PRICE), _listing(CORRECTED_PRICE)], "the register", "register"
    )

    assert added == 1
    cached = property_cache.load_collection()
    assert cached is not None
    assert len(cached.properties) == 1
    assert _cached_price() == REGISTERED_PRICE


def test_the_collection_and_the_cache_say_the_same_thing_about_a_deed(store, cache):
    """The two homes of the catalogue carry the same price for the same deed."""
    save_imported_properties([_listing(REGISTERED_PRICE)], "the register", "register")
    store.add_properties([_listing(REGISTERED_PRICE)])

    save_imported_properties([_listing(CORRECTED_PRICE)], "the register", "register", refresh=True)
    store.add_properties([_listing(CORRECTED_PRICE)], refresh=True)

    assert _collection_price(store) == _cached_price() == CORRECTED_PRICE
