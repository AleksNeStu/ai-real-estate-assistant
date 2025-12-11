from vector_store.hybrid_retriever import AdvancedPropertyRetriever
from vector_store.chroma_store import ChromaPropertyStore
from langchain_core.documents import Document


def test_retriever_geo_radius_filters_docs():
    docs = [
        Document(page_content="Warsaw apt", metadata={"city":"Warsaw","lat":52.23,"lon":21.01,"price":5000}),
        Document(page_content="Krakow apt", metadata={"city":"Krakow","lat":50.06,"lon":19.94,"price":4400}),
    ]
    store = ChromaPropertyStore(persist_directory="chroma_db_test")
    retr = AdvancedPropertyRetriever(vector_store=store, center_lat=52.23, center_lon=21.01, radius_km=10.0)
    filtered = retr._filter_by_geo(docs)
    assert len(filtered) == 1
    assert filtered[0].metadata["city"] == "Warsaw"
