"""Regression tests for the vector-store coordinate keys.

The vector store writes the coordinates as `lat`/`lon` - the geo filters in
`vector_store/chroma_store.py` query exactly those keys - while the Property
schema names them `latitude`/`longitude`. Before the normalisation every
listing that came back from the vector store arrived with null coordinates:
the map stayed empty and the city overview showed no average price.
"""

from langchain_core.documents import Document

from api.routers.cma import _document_to_property
from api.routers.favorites import _document_to_property_dict
from data.schemas import Property, normalize_property_metadata
from vector_store.chroma_store import ChromaPropertyStore

# What the vector store actually holds - taken from a live collection.
STORED_METADATA = {
    "id": "prop-0001",
    "city": "Warsaw",
    "district": "Wola",
    "price": 1141046.0,
    "rooms": 1.0,
    "bathrooms": 1.0,
    "area_sqm": 97.0,
    "property_type": "townhouse",
    "listing_type": "sale",
    "currency": "PLN",
    "has_parking": False,
    "has_garden": False,
    "has_pool": False,
    "has_garage": False,
    "has_elevator": False,
    "year_built": 2021,
    "price_per_sqm": 11763.36,
    "source_url": "https://demo-real-estate.example.com/property/1",
    "lat": 52.23639887511031,
    "lon": 20.98516901227777,
}


def test_normalize_reads_the_stored_lat_lon_keys():
    normalized = normalize_property_metadata(STORED_METADATA)
    assert normalized["latitude"] == 52.23639887511031
    assert normalized["longitude"] == 20.98516901227777


def test_normalize_keeps_an_explicit_latitude():
    normalized = normalize_property_metadata({"latitude": 52.0, "lon": 21.0})
    assert normalized["latitude"] == 52.0
    assert normalized["longitude"] == 21.0


def test_normalize_does_not_overwrite_a_set_latitude():
    normalized = normalize_property_metadata({"latitude": 52.0, "lat": 10.0, "lon": 21.0})
    assert normalized["latitude"] == 52.0


def test_normalize_does_not_mutate_the_input():
    original = dict(STORED_METADATA)
    normalize_property_metadata(original)
    assert original == STORED_METADATA


def test_normalize_without_coordinates_stays_empty():
    normalized = normalize_property_metadata({"id": "p1", "city": "Krakow"})
    assert normalized.get("latitude") is None
    assert normalized.get("longitude") is None


def test_search_result_property_carries_the_coordinates():
    """The search router validates the metadata straight into a Property."""
    prop = Property.model_validate(normalize_property_metadata(STORED_METADATA))
    assert prop.latitude == 52.23639887511031
    assert prop.longitude == 20.98516901227777


def test_favorites_property_dict_carries_the_coordinates():
    doc = Document(page_content="A townhouse in Wola.", metadata=dict(STORED_METADATA))
    data = _document_to_property_dict(doc)
    assert data["latitude"] == 52.23639887511031
    assert data["longitude"] == 20.98516901227777


def test_cma_property_carries_the_coordinates():
    doc = Document(page_content="A townhouse in Wola.", metadata=dict(STORED_METADATA))
    prop = _document_to_property(doc)
    assert prop.latitude == 52.23639887511031
    assert prop.longitude == 20.98516901227777


def test_the_writer_keeps_the_lat_lon_keys_the_geo_filters_query(tmp_path):
    """The geo filters query `lat`/`lon`, so the writer must not rename them."""
    store = ChromaPropertyStore(persist_directory=str(tmp_path))
    prop = Property(
        id="p1",
        city="Warsaw",
        price=500000,
        rooms=2,
        latitude=52.23,
        longitude=21.01,
    )
    metadata = store.property_to_document(prop).metadata
    assert metadata["lat"] == 52.23
    assert metadata["lon"] == 21.01
    assert "latitude" not in metadata
