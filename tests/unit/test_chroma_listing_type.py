from unittest.mock import patch
from vector_store.chroma_store import ChromaPropertyStore
from data.schemas import Property, PropertyType, ListingType


def test_property_to_document_includes_listing_type(tmp_path):
    with patch.object(ChromaPropertyStore, "_create_embeddings", return_value=None):
        store = ChromaPropertyStore(persist_directory=str(tmp_path))

    p = Property(city="Warsaw", price=5000, rooms=2, property_type=PropertyType.APARTMENT, listing_type=ListingType.RENT)
    doc = store.property_to_document(p)
    md = doc.metadata
    assert md.get("listing_type") == "rent"

