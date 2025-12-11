from vector_store.hybrid_retriever import create_retriever, AdvancedPropertyRetriever
from vector_store.chroma_store import ChromaPropertyStore


def test_factory_returns_advanced_when_geo_params_present():
    store = ChromaPropertyStore(persist_directory="chroma_db_test")
    retriever = create_retriever(
        vector_store=store,
        k=5,
        search_type="mmr",
        center_lat=52.23,
        center_lon=21.01,
        radius_km=10.0,
    )
    assert isinstance(retriever, AdvancedPropertyRetriever)
    assert retriever.center_lat == 52.23
    assert retriever.center_lon == 21.01
    assert retriever.radius_km == 10.0

