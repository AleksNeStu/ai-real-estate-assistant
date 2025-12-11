from unittest.mock import patch
from vector_store.chroma_store import ChromaPropertyStore
from vector_store.hybrid_retriever import HybridPropertyRetriever
from data.schemas import Property, PropertyType, ListingType, PropertyCollection


def test_hybrid_retriever_filters_rent_vs_sale(tmp_path):
    with patch.object(ChromaPropertyStore, "_create_embeddings", return_value=None):
        store = ChromaPropertyStore(persist_directory=str(tmp_path))

    props = [
        Property(id="r1", city="Warsaw", price=5000, rooms=2, property_type=PropertyType.APARTMENT, listing_type=ListingType.RENT, description="balcony"),
        Property(id="s1", city="Krakow", price=95000, rooms=3, property_type=PropertyType.APARTMENT, listing_type=ListingType.SALE, description="garage"),
    ]
    coll = PropertyCollection(properties=props, total_count=len(props))
    store.add_property_collection(coll)

    retr = HybridPropertyRetriever(vector_store=store, k=5, search_type="mmr")

    rent_docs = retr.get_relevant_documents("for rent balcony")
    assert any(d.metadata.get("listing_type") == "rent" for d in rent_docs)
    assert all(d.metadata.get("listing_type") == "rent" for d in rent_docs)

    sale_docs = retr.get_relevant_documents("for sale")
    assert any(d.metadata.get("listing_type") == "sale" for d in sale_docs)
    assert all(d.metadata.get("listing_type") == "sale" for d in sale_docs)
