from vector_store.chroma_store import ChromaPropertyStore
from data.schemas import Property, PropertyType, PropertyCollection
from unittest.mock import patch


def make_prop(pid, city, price, rooms, desc="garden balcony"):
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


def test_get_retriever_fallback_returns_docs(tmp_path):
    with patch.object(ChromaPropertyStore, "_create_embeddings", return_value=None):
        store = ChromaPropertyStore(persist_directory=str(tmp_path))

    coll = PropertyCollection(properties=[
        make_prop("p1", "Krakow", 900, 2, "garden balcony"),
        make_prop("p2", "Warsaw", 1200, 3, "garage"),
    ], total_count=2)
    store.add_property_collection(coll)

    retr = store.get_retriever(search_type="mmr", k=1, fetch_k=2)
    docs = retr.get_relevant_documents("balcony garden")
    assert docs and docs[0].metadata.get("id") == "p1"
