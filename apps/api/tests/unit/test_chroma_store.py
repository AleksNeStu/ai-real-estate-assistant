import threading
from unittest.mock import MagicMock, patch

from langchain_core.documents import Document

from data.schemas import Property, PropertyCollection, PropertyType
from vector_store.chroma_store import ChromaPropertyStore


def make_property(pid: str, city: str, price: float, rooms: float, desc: str = "") -> Property:
    return Property(  # type: ignore[call-arg]
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

    coll = PropertyCollection(
        properties=[
            make_property("p1", "Krakow", 900, 2, "balcony garden"),
            make_property("p2", "Warsaw", 1200, 3, "garage"),
        ],
        total_count=2,
    )

    added = store.add_property_collection(coll)
    assert added == 2

    results = store.search("garden balcony", k=5)
    # Fallback scoring counts token matches; first doc should be relevant
    assert results and results[0][0].metadata["id"] == "p1"


def test_clear_resets_cache(monkeypatch, tmp_path):
    with patch.object(ChromaPropertyStore, "_create_embeddings", return_value=None):
        store = ChromaPropertyStore(persist_directory=str(tmp_path))

    coll = PropertyCollection(
        properties=[
            make_property("p1", "Krakow", 900, 2),
            make_property("p2", "Warsaw", 1200, 3),
        ],
        total_count=2,
    )

    store.add_property_collection(coll)
    assert store.get_stats()["total_documents"] == 2
    store.clear()
    assert store.get_stats()["total_documents"] == 0


def test_clear_removes_the_stale_index_directories(monkeypatch, tmp_path):
    """A cleared collection leaves its index behind on disk - that is a trap.

    ChromaDB's delete_collection drops the rows but keeps the collection's
    HNSW directory in the persist directory. A later query can then meet a
    segment that is gone and answer with an empty list while the catalogue
    holds the documents. The store removes those directories with the
    collection.
    """
    with patch.object(ChromaPropertyStore, "_create_embeddings", return_value=None):
        store = ChromaPropertyStore(persist_directory=str(tmp_path))

    # A collection id, and something that is not one.
    stale = tmp_path / "68f35189-f923-46ac-83e3-ba41ee031dbc"
    stale.mkdir()
    (stale / "segment.bin").write_bytes(b"index")
    other = tmp_path / "not-a-collection"
    other.mkdir()

    store.clear()

    assert not stale.exists()
    assert other.exists()


def test_clear_keeps_the_persist_database(monkeypatch, tmp_path):
    """The store's own database file is not an index and must survive."""
    with patch.object(ChromaPropertyStore, "_create_embeddings", return_value=None):
        store = ChromaPropertyStore(persist_directory=str(tmp_path))

    database = tmp_path / "chroma.sqlite3"
    database.write_bytes(b"sqlite")

    store.clear()

    assert database.exists()


def test_search_concurrent_with_embedding(tmp_path, monkeypatch):
    """
    Test that search does not block while embeddings are being generated.
    """
    started_embedding = threading.Event()
    allow_finish_embedding = threading.Event()

    # Mock Vector Store
    fake_vector_store = MagicMock()
    fake_vector_store._collection = MagicMock()
    fake_vector_store._collection.count.return_value = 0
    fake_vector_store._collection.get.return_value = {"ids": []}

    # Mock Embeddings
    fake_embeddings = MagicMock()

    def embed_side_effect(texts):
        started_embedding.set()
        # Simulate heavy CPU work
        allow_finish_embedding.wait(timeout=5)
        return [[0.1] * 384 for _ in texts]

    fake_embeddings.embed_documents.side_effect = embed_side_effect

    with (
        patch.object(ChromaPropertyStore, "_create_embeddings", return_value=fake_embeddings),
        patch.object(
            ChromaPropertyStore, "_initialize_vector_store", return_value=fake_vector_store
        ),
    ):
        store = ChromaPropertyStore(persist_directory=str(tmp_path))

    coll = PropertyCollection(
        properties=[
            make_property("p1", "Krakow", 900, 2, "balcony garden"),
            make_property("p2", "Warsaw", 1200, 3, "garage"),
        ],
        total_count=2,
    )

    # Start async indexing
    fut = store.add_property_collection_async(coll, replace_existing=False)

    # Wait for embedding to start
    assert started_embedding.wait(timeout=5), "Embedding did not start"

    # Now search should NOT block even though embedding is "stuck"
    # Because embedding happens OUTSIDE the lock
    # And search only needs the lock which is free

    # Mock search result on vector store (simulating previous data or concurrent read)
    fake_vector_store.similarity_search_with_score.return_value = [
        (Document(page_content="vs", metadata={"id": "vs"}), 0.1)
    ]

    # This call should return immediately
    results = store.search("anything", k=1)

    assert len(results) == 1
    assert results[0][0].metadata["id"] == "vs"

    # Finish embedding
    allow_finish_embedding.set()

    # Wait for job to finish
    added = fut.result(timeout=5)
    assert added == 2

    # Verify add was called
    assert fake_vector_store._collection.add.called


def test_get_vector_store_prefers_thread_local_store(tmp_path):
    fake_vector_store = MagicMock()
    with (
        patch.object(ChromaPropertyStore, "_create_embeddings", return_value=MagicMock()),
        patch.object(
            ChromaPropertyStore, "_initialize_vector_store", return_value=fake_vector_store
        ),
    ):
        store = ChromaPropertyStore(persist_directory=str(tmp_path))

    store.vector_store = "main"
    store._vector_store_local.store = "thread"
    assert store._get_vector_store() == "thread"

    store._vector_store_local.store = None
    assert store._get_vector_store() == "main"


def test_async_indexing_uses_thread_local_store_when_vector_store_is_mock(tmp_path):
    fake_vector_store = MagicMock()
    fake_vector_store._collection = MagicMock()
    fake_vector_store._collection.count.return_value = 0
    fake_vector_store._collection.get.return_value = {"ids": []}

    fake_embeddings = MagicMock()
    fake_embeddings.embed_documents.side_effect = lambda texts: [[0.1] * 384 for _ in texts]

    with (
        patch.object(ChromaPropertyStore, "_create_embeddings", return_value=fake_embeddings),
        patch.object(
            ChromaPropertyStore, "_initialize_vector_store", return_value=fake_vector_store
        ),
    ):
        store = ChromaPropertyStore(persist_directory=str(tmp_path))

    store._initialize_vector_store = MagicMock(side_effect=AssertionError("unexpected reinit"))

    coll = PropertyCollection(
        properties=[
            make_property("p1", "Krakow", 900, 2, "balcony garden"),
            make_property("p2", "Warsaw", 1200, 3, "garage"),
        ],
        total_count=2,
    )
    fut = store.add_property_collection_async(coll, replace_existing=False)
    assert fut.result(timeout=5) == 2
    assert fake_vector_store._collection.add.called


def test_async_indexing_reinitializes_when_vector_store_is_chroma_instance(tmp_path, monkeypatch):
    import vector_store.chroma_store as chroma_store_module

    class DummyChroma:
        pass

    monkeypatch.setattr(chroma_store_module, "Chroma", DummyChroma)

    with (
        patch.object(ChromaPropertyStore, "_create_embeddings", return_value=MagicMock()),
        patch.object(ChromaPropertyStore, "_initialize_vector_store", return_value=MagicMock()),
    ):
        store = ChromaPropertyStore(persist_directory=str(tmp_path))

    store.vector_store = DummyChroma()
    store._vector_store_local.store = store.vector_store
    store._initialize_vector_store = MagicMock(return_value=MagicMock())
    store.add_property_collection = MagicMock(return_value=0)

    coll = PropertyCollection(properties=[], total_count=0)
    fut = store.add_property_collection_async(coll, replace_existing=False)
    assert fut.result(timeout=5) == 0
    assert store._initialize_vector_store.called
