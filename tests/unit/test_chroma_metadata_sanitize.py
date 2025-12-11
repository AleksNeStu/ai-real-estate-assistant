from vector_store.chroma_store import ChromaPropertyStore
from data.schemas import Property, PropertyType, ListingType


def test_property_to_document_metadata_is_primitives(tmp_path):
    store = ChromaPropertyStore(persist_directory=str(tmp_path))
    p = Property(
        id="p1",
        city="Warsaw",
        price=5000,
        rooms=2,
        property_type=PropertyType.APARTMENT,
        listing_type=ListingType.RENT,
    )
    doc = store.property_to_document(p)
    md = doc.metadata
    # Ensure no nested extras key
    assert "chroma_dp" not in md
    # Check types are allowed
    for k, v in md.items():
        assert (v is None) or isinstance(v, (str, int, float, bool)), f"Key {k} has invalid type {type(v)}"

