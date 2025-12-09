import os
import pytest
from unittest.mock import patch

from vector_store.chroma_store import ChromaPropertyStore
from data.schemas import Property, PropertyCollection, PropertyType


def make_property(pid: str, city: str, price: float, rooms: float, desc: str = "") -> Property:
    return Property(
        id=pid,
        city=city,
        price=price,
        rooms=rooms,
        bathrooms=1,
        area_sqm=50,
        property_type=PropertyType.APARTMENT,
        has_parking=True,
        is_furnished=True,
        description=desc,
    )


def test_store_initializes_without_embeddings(monkeypatch, tmp_path):
    monkeypatch.setenv("FORCE_FASTEMBED", "0")

    # Force _create_embeddings to return None
    with patch.object(ChromaPropertyStore, "_create_embeddings", return_value=None):
        store = ChromaPropertyStore(persist_directory=str(tmp_path))
        stats = store.get_stats()
        assert stats["embedding_provider"] == "none"
        assert store.vector_store is None


def test_property_to_document_metadata_types(monkeypatch, tmp_path):
    with patch.object(ChromaPropertyStore, "_create_embeddings", return_value=None):
        store = ChromaPropertyStore(persist_directory=str(tmp_path))

    p = make_property("p1", "Krakow", 900, 2, "Nice flat")
    doc = store.property_to_document(p)
    md = doc.metadata
    assert md["city"] == "Krakow"
    assert isinstance(md["rooms"], float)
    assert isinstance(md["bathrooms"], float)
    assert md["has_parking"] is True
    assert md["property_type"] in ("apartment", PropertyType.APARTMENT.value)


def test_add_and_search_fallback_without_vector_store(monkeypatch, tmp_path):
    with patch.object(ChromaPropertyStore, "_create_embeddings", return_value=None):
        store = ChromaPropertyStore(persist_directory=str(tmp_path))

    coll = PropertyCollection(properties=[
        make_property("p1", "Krakow", 900, 2, "balcony garden"),
        make_property("p2", "Warsaw", 1200, 3, "garage"),
    ], total_count=2)

    added = store.add_property_collection(coll)
    assert added == 2

    results = store.search("garden balcony", k=5)
    # Fallback scoring counts token matches; first doc should be relevant
    assert results and results[0][0].metadata["id"] == "p1"


def test_clear_resets_cache(monkeypatch, tmp_path):
    with patch.object(ChromaPropertyStore, "_create_embeddings", return_value=None):
        store = ChromaPropertyStore(persist_directory=str(tmp_path))

    coll = PropertyCollection(properties=[
        make_property("p1", "Krakow", 900, 2),
        make_property("p2", "Warsaw", 1200, 3),
    ], total_count=2)

    store.add_property_collection(coll)
    assert store.get_stats()["total_documents"] == 2
    store.clear()
    assert store.get_stats()["total_documents"] == 0

