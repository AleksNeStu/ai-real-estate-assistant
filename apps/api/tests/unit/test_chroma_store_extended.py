"""
Extended unit tests for ChromaPropertyStore covering methods with no existing coverage.

Covers: search(), hybrid_search(), get_properties_by_ids(), delete_by_source(),
delete_by_source_type(), get_stats(), add_property_collection(), add_property_collection_async(),
search_by_metadata(), _build_chroma_filter(), _build_geo_filter(), _build_bbox_filter(),
_haversine(), _point_in_polygon(), add_properties() with vector store,
get_retriever(), __repr__(), get_vector_store() module function.
"""

from concurrent.futures import Future
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document

from data.schemas import Property, PropertyCollection, PropertyType
from vector_store.chroma_store import (
    ChromaPropertyStore,
    VectorStoreUnavailable,
    VectorStoreWriteError,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_property(
    pid: str = "p1",
    city: str = "Krakow",
    price: float = 900.0,
    rooms: float = 2.0,
    desc: str = "Nice flat",
    *,
    latitude: float | None = None,
    longitude: float | None = None,
    source_url: str | None = None,
) -> Property:
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
        latitude=latitude,
        longitude=longitude,
        source_url=source_url,
    )


def _make_store(tmp_path, *, embeddings=None, vector_store=None):
    """Create a ChromaPropertyStore with mocked internals."""
    with (
        patch.object(ChromaPropertyStore, "_create_embeddings", return_value=embeddings),
        patch.object(ChromaPropertyStore, "_initialize_vector_store", return_value=vector_store),
    ):
        return ChromaPropertyStore(persist_directory=str(tmp_path))


def _mock_vector_store():
    vs = MagicMock()
    vs._collection = MagicMock()
    vs._collection.count.return_value = 0
    vs._collection.get.return_value = {"ids": []}
    return vs


def _mock_embeddings():
    emb = MagicMock()
    emb.embed_documents.side_effect = lambda texts: [[0.1] * 384 for _ in texts]
    return emb


# ===================================================================
# search() with vector store
# ===================================================================


class TestSearchWithVectorStore:
    """Tests for search() when the vector store is available."""

    def test_search_returns_vector_results(self, tmp_path):
        vs = _mock_vector_store()
        doc = Document(page_content="apt in Krakow", metadata={"id": "p1", "city": "Krakow"})
        vs.similarity_search_with_score.return_value = [(doc, 0.15)]

        store = _make_store(tmp_path, embeddings=_mock_embeddings(), vector_store=vs)
        results = store.search("apartment Krakow", k=3)

        assert len(results) == 1
        assert results[0][0].metadata["id"] == "p1"
        assert results[0][1] == 0.15
        vs.similarity_search_with_score.assert_called_once()

    def test_search_passes_chroma_filter_for_user_filters(self, tmp_path):
        vs = _mock_vector_store()
        vs.similarity_search_with_score.return_value = []

        store = _make_store(tmp_path, embeddings=_mock_embeddings(), vector_store=vs)

        user_filter = {"min_price": 500, "max_price": 1500, "city": "Krakow"}
        store.search("flat", k=5, filter=user_filter)

        call_args = vs.similarity_search_with_score.call_args
        chroma_filter = call_args.kwargs.get("filter") or call_args[1].get("filter")
        assert chroma_filter is not None
        assert "$and" in chroma_filter

    def test_search_keeps_existing_chroma_filter(self, tmp_path):
        vs = _mock_vector_store()
        vs.similarity_search_with_score.return_value = []

        store = _make_store(tmp_path, embeddings=_mock_embeddings(), vector_store=vs)

        chroma_filter = {"$and": [{"city": "Warsaw"}]}
        store.search("flat", k=5, filter=chroma_filter)

        call_args = vs.similarity_search_with_score.call_args
        passed_filter = call_args.kwargs.get("filter") or call_args[1].get("filter")
        assert passed_filter == chroma_filter

    def test_search_fallback_with_city_filter(self, tmp_path):
        """When vector store raises, fallback text search applies city filter."""
        store = _make_store(tmp_path, embeddings=None, vector_store=None)

        doc1 = Document(
            page_content="nice garden in Krakow", metadata={"id": "p1", "city": "Krakow"}
        )
        doc2 = Document(
            page_content="nice garden in Warsaw", metadata={"id": "p2", "city": "Warsaw"}
        )
        store._documents = [doc1, doc2]

        results = store.search("garden", k=5, filter={"city": "Krakow"})
        assert len(results) == 1
        assert results[0][0].metadata["id"] == "p1"

    def test_search_fallback_no_matching_docs_returns_empty(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        store._documents = []

        results = store.search("nonexistent", k=5)
        assert results == []


# ===================================================================
# hybrid_search()
# ===================================================================


class TestHybridSearch:
    """Tests for hybrid_search() combining vector and keyword scoring."""

    def _store_with_vs(self, tmp_path, search_results):
        vs = _mock_vector_store()
        vs.similarity_search_with_score.return_value = search_results
        store = _make_store(tmp_path, embeddings=_mock_embeddings(), vector_store=vs)
        return store

    def test_hybrid_search_basic(self, tmp_path):
        doc = Document(
            page_content="apartment in Krakow with garden",
            metadata={"id": "p1", "city": "Krakow", "price": 900},
        )
        store = self._store_with_vs(tmp_path, [(doc, 0.2)])

        results = store.hybrid_search("apartment Krakow garden", k=5)
        assert len(results) == 1
        assert results[0][0].metadata["id"] == "p1"
        # Combined score should be positive
        assert results[0][1] > 0

    def test_hybrid_search_empty_query(self, tmp_path):
        doc = Document(page_content="some content", metadata={"id": "p1", "price": 500})
        store = self._store_with_vs(tmp_path, [(doc, 0.5)])

        results = store.hybrid_search("", k=5)
        assert len(results) == 1

    def test_hybrid_search_no_results(self, tmp_path):
        store = self._store_with_vs(tmp_path, [])
        results = store.hybrid_search("nothing", k=5)
        assert results == []

    def test_hybrid_search_with_geo_radius(self, tmp_path):
        doc1 = Document(
            page_content="apt near center",
            metadata={"id": "p1", "lat": 50.06, "lon": 19.94},
        )
        doc2 = Document(
            page_content="apt far away",
            metadata={"id": "p2", "lat": 51.0, "lon": 20.0},
        )
        # Krakow center ~50.06, 19.94
        store = self._store_with_vs(tmp_path, [(doc1, 0.1), (doc2, 0.2)])

        results = store.hybrid_search("apt", k=5, lat=50.06, lon=19.94, radius_km=10)
        # doc2 is ~100km away so should be filtered out
        ids = [r[0].metadata["id"] for r in results]
        assert "p1" in ids
        assert "p2" not in ids

    def test_hybrid_search_with_polygon(self, tmp_path):
        # Polygon approximating a small area around Krakow center
        polygon = [
            [19.93, 50.05],
            [19.95, 50.05],
            [19.95, 50.07],
            [19.93, 50.07],
        ]
        doc_inside = Document(
            page_content="apt inside",
            metadata={"id": "p1", "lat": 50.06, "lon": 19.94},
        )
        doc_outside = Document(
            page_content="apt outside",
            metadata={"id": "p2", "lat": 52.0, "lon": 21.0},
        )
        store = self._store_with_vs(tmp_path, [(doc_inside, 0.1), (doc_outside, 0.2)])

        results = store.hybrid_search("apt", k=5, polygon=polygon)
        ids = [r[0].metadata["id"] for r in results]
        assert "p1" in ids
        assert "p2" not in ids

    def test_hybrid_search_sort_by_price(self, tmp_path):
        doc1 = Document(
            page_content="cheap flat",
            metadata={"id": "p1", "price": 500},
        )
        doc2 = Document(
            page_content="expensive flat",
            metadata={"id": "p2", "price": 2000},
        )
        store = self._store_with_vs(tmp_path, [(doc1, 0.1), (doc2, 0.2)])

        results_desc = store.hybrid_search("flat", k=5, sort_by="price", sort_order="desc")
        assert results_desc[0][0].metadata["price"] == 2000

        results_asc = store.hybrid_search("flat", k=5, sort_by="price", sort_order="asc")
        assert results_asc[0][0].metadata["price"] == 500

    def test_hybrid_search_sort_by_relevance(self, tmp_path):
        doc1 = Document(
            page_content="cheap flat",
            metadata={"id": "p1", "price": 500},
        )
        doc2 = Document(
            page_content="expensive flat",
            metadata={"id": "p2", "price": 2000},
        )
        store = self._store_with_vs(tmp_path, [(doc1, 0.1), (doc2, 0.2)])

        results = store.hybrid_search("flat", k=5, sort_by="relevance")
        # Default sort by combined_score descending
        assert len(results) == 2

    def test_hybrid_search_with_filters(self, tmp_path):
        vs = _mock_vector_store()
        doc = Document(
            page_content="flat in Warsaw",
            metadata={"id": "p1", "city": "Warsaw", "price": 900},
        )
        vs.similarity_search_with_score.return_value = [(doc, 0.1)]
        store = _make_store(tmp_path, embeddings=_mock_embeddings(), vector_store=vs)

        filters = {"city": "Warsaw", "min_price": 500, "max_price": 1500}
        results = store.hybrid_search("flat", filters=filters, k=5)
        assert len(results) == 1

    def test_hybrid_search_with_ranking_weights(self, tmp_path):
        doc = Document(
            page_content="apartment with garden",
            metadata={"id": "p1"},
        )
        store = self._store_with_vs(tmp_path, [(doc, 0.2)])

        rw = MagicMock()
        rw.alpha = 0.9

        results = store.hybrid_search("apartment", k=5, ranking_weights=rw)
        assert len(results) == 1

    def test_hybrid_search_with_bbox_filter(self, tmp_path):
        doc1 = Document(
            page_content="apt",
            metadata={"id": "p1", "lat": 50.06, "lon": 19.94},
        )
        store = self._store_with_vs(tmp_path, [(doc1, 0.1)])

        results = store.hybrid_search(
            "apt",
            k=5,
            min_lat=50.0,
            max_lat=51.0,
            min_lon=19.0,
            max_lon=20.0,
        )
        assert len(results) == 1

    def test_hybrid_search_geo_radius_filters_out_distant(self, tmp_path):
        """All results are outside the radius, should return empty."""
        doc = Document(
            page_content="far away apt",
            metadata={"id": "p1", "lat": 52.0, "lon": 21.0},
        )
        store = self._store_with_vs(tmp_path, [(doc, 0.1)])

        results = store.hybrid_search("apt", k=5, lat=50.06, lon=19.94, radius_km=1)
        assert results == []


# ===================================================================
# get_properties_by_ids()
# ===================================================================


class TestGetPropertiesByIds:
    """Tests for get_properties_by_ids()."""

    def test_fetches_from_chroma(self, tmp_path):
        vs = _mock_vector_store()
        vs._collection.get.return_value = {
            "ids": ["p1", "p2"],
            "documents": ["doc1 text", "doc2 text"],
            "metadatas": [{"id": "p1"}, {"id": "p2"}],
        }
        store = _make_store(tmp_path, embeddings=_mock_embeddings(), vector_store=vs)

        results = store.get_properties_by_ids(["p1", "p2"])
        assert len(results) == 2
        assert results[0].page_content == "doc1 text"
        assert results[1].metadata["id"] == "p2"

    def test_fallback_to_cache_when_no_vs(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        doc1 = Document(page_content="text1", metadata={"id": "p1"})
        doc2 = Document(page_content="text2", metadata={"id": "p2"})
        store._documents = [doc1, doc2]

        results = store.get_properties_by_ids(["p1"])
        assert len(results) == 1
        assert results[0].metadata["id"] == "p1"

    def test_a_read_that_cannot_be_answered_is_not_an_empty_one(self, tmp_path):
        """An empty catalogue and an unreadable one are not the same answer."""
        vs = _mock_vector_store()
        vs._collection.get.side_effect = Exception("chroma error")
        store = _make_store(tmp_path, embeddings=_mock_embeddings(), vector_store=vs)

        with pytest.raises(VectorStoreUnavailable):
            store.get_properties_by_ids(["p1"])

    def test_handles_empty_chroma_response(self, tmp_path):
        vs = _mock_vector_store()
        vs._collection.get.return_value = {"ids": [], "documents": [], "metadatas": []}
        store = _make_store(tmp_path, embeddings=_mock_embeddings(), vector_store=vs)

        results = store.get_properties_by_ids(["nonexistent"])
        assert results == []

    def test_handles_none_documents_in_response(self, tmp_path):
        vs = _mock_vector_store()
        vs._collection.get.return_value = {
            "ids": ["p1"],
            "documents": None,
            "metadatas": None,
        }
        store = _make_store(tmp_path, embeddings=_mock_embeddings(), vector_store=vs)

        results = store.get_properties_by_ids(["p1"])
        assert len(results) == 1
        assert results[0].page_content == ""


# ===================================================================
# delete_by_source() and delete_by_source_type()
# ===================================================================


class TestDeleteMethods:
    """Tests for delete_by_source() and delete_by_source_type()."""

    def test_delete_by_source_calls_vector_store(self, tmp_path):
        vs = _mock_vector_store()
        store = _make_store(tmp_path, embeddings=_mock_embeddings(), vector_store=vs)

        store.delete_by_source("https://example.com/listing")
        vs.delete.assert_called_once_with(filter={"source_url": "https://example.com/listing"})

    def test_delete_by_source_no_vs_does_nothing(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        # Should not raise
        store.delete_by_source("https://example.com/listing")

    def test_delete_by_source_handles_error(self, tmp_path):
        vs = _mock_vector_store()
        vs.delete.side_effect = Exception("delete failed")
        store = _make_store(tmp_path, embeddings=_mock_embeddings(), vector_store=vs)

        # Should not raise, just log
        store.delete_by_source("https://example.com/listing")

    def test_delete_by_source_type_calls_vector_store(self, tmp_path):
        vs = _mock_vector_store()
        store = _make_store(tmp_path, embeddings=_mock_embeddings(), vector_store=vs)

        store.delete_by_source_type("csv")
        vs.delete.assert_called_once_with(filter={"source_platform": "csv"})

    def test_delete_by_source_type_no_vs_does_nothing(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        store.delete_by_source_type("portal")


# ===================================================================
# get_stats()
# ===================================================================


class TestGetStats:
    """Tests for get_stats() with various embedding types."""

    def test_stats_with_openai_embeddings(self, tmp_path):
        emb = MagicMock()
        emb.__class__.__name__ = "OpenAIEmbeddings"
        emb.model = "text-embedding-3-small"
        vs = _mock_vector_store()
        vs._collection.count.return_value = 42
        store = _make_store(tmp_path, embeddings=emb, vector_store=vs)

        stats = store.get_stats()
        assert stats["embedding_provider"] == "openai"
        assert stats["embedding_model"] == "text-embedding-3-small"
        assert stats["db_document_count"] == 42
        assert stats["total_documents"] == 42

    def test_stats_with_fastembed_embeddings(self, tmp_path):
        emb = MagicMock()
        emb.__class__.__name__ = "FastEmbedEmbeddings"
        emb.model_name = "BAAI/bge-small-en-v1.5"
        vs = _mock_vector_store()
        vs._collection.count.return_value = 10
        store = _make_store(tmp_path, embeddings=emb, vector_store=vs)

        stats = store.get_stats()
        assert stats["embedding_provider"] == "fastembed"
        assert stats["embedding_model"] == "BAAI/bge-small-en-v1.5"
        assert stats["db_document_count"] == 10

    def test_stats_without_embeddings(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)

        stats = store.get_stats()
        assert stats["embedding_provider"] == "none"
        assert stats["embedding_model"] == "none"
        assert stats["total_documents"] == 0

    def test_stats_with_cache_only(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        store._documents = [Document(page_content="t", metadata={"id": "1"})]

        stats = store.get_stats()
        assert stats["total_documents"] == 1
        assert stats["cache_document_count"] == 1
        assert stats["db_document_count"] == 0

    def test_stats_db_count_zero_falls_back_to_cache(self, tmp_path):
        vs = _mock_vector_store()
        vs._collection.count.return_value = 0
        store = _make_store(tmp_path, embeddings=_mock_embeddings(), vector_store=vs)
        store._documents = [Document(page_content="t", metadata={"id": "1"})]

        stats = store.get_stats()
        assert stats["total_documents"] == 1

    def test_stats_returns_collection_name(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        stats = store.get_stats()
        assert stats["collection_name"] == "properties"


# ===================================================================
# add_property_collection() with replace_existing
# ===================================================================


class TestAddPropertyCollection:
    """Tests for add_property_collection() and add_property_collection_async() variants."""

    def test_add_collection_with_replace_clears_first(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        store._documents = [Document(page_content="old", metadata={"id": "old"})]

        coll = PropertyCollection(
            properties=[make_property("p1", "Krakow", 900, 2, "new")],
            total_count=1,
        )
        added = store.add_property_collection(coll, replace_existing=True)
        assert added == 1
        assert len(store._documents) == 1
        assert store._documents[0].metadata["id"] == "p1"

    def test_add_collection_without_replace(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)

        coll = PropertyCollection(
            properties=[
                make_property("p1", "Krakow", 900, 2),
                make_property("p2", "Warsaw", 1200, 3),
            ],
            total_count=2,
        )
        added = store.add_property_collection(coll, replace_existing=False)
        assert added == 2

    def test_add_collection_async_returns_existing_future(self, tmp_path):
        vs = _mock_vector_store()
        store = _make_store(tmp_path, embeddings=_mock_embeddings(), vector_store=vs)

        fake_future = MagicMock(spec=Future)
        fake_future.done.return_value = False
        store._index_future = fake_future

        coll = PropertyCollection(properties=[], total_count=0)
        result = store.add_property_collection_async(coll)
        assert result is fake_future

    def test_add_collection_async_completed_resubmits(self, tmp_path):
        vs = _mock_vector_store()
        store = _make_store(tmp_path, embeddings=_mock_embeddings(), vector_store=vs)

        old_future = MagicMock(spec=Future)
        old_future.done.return_value = True
        store._index_future = old_future

        coll = PropertyCollection(
            properties=[make_property("p1", "Krakow", 900, 2)],
            total_count=1,
        )
        new_future = store.add_property_collection_async(coll)
        assert new_future is not old_future
        assert new_future.result(timeout=5) == 1


# ===================================================================
# add_properties() with real vector store path
# ===================================================================


class TestAddPropertiesWithVectorStore:
    """Tests for add_properties() that go through the vector store path."""

    def test_adds_with_embeddings(self, tmp_path):
        vs = _mock_vector_store()
        vs._collection.get.return_value = {"ids": []}
        emb = _mock_embeddings()
        store = _make_store(tmp_path, embeddings=emb, vector_store=vs)

        props = [make_property("p1", "Krakow", 900, 2, "nice")]
        added = store.add_properties(props)
        assert added == 1
        vs._collection.add.assert_called_once()
        call_kw = vs._collection.add.call_args.kwargs
        assert call_kw["ids"] == ["p1"]
        assert len(call_kw["embeddings"]) == 1
        assert len(call_kw["embeddings"][0]) == 384

    def test_skips_duplicates(self, tmp_path):
        vs = _mock_vector_store()
        vs._collection.get.return_value = {"ids": ["p1"]}
        emb = _mock_embeddings()
        store = _make_store(tmp_path, embeddings=emb, vector_store=vs)

        props = [make_property("p1", "Krakow", 900, 2)]
        added = store.add_properties(props)
        assert added == 1  # cached in memory
        vs._collection.add.assert_not_called()

    def test_fallback_to_add_documents_when_no_embeddings_obj(self, tmp_path):
        vs = _mock_vector_store()
        vs._collection.get.return_value = {"ids": []}
        store = _make_store(tmp_path, embeddings=None, vector_store=vs)

        props = [make_property("p1", "Krakow", 900, 2)]
        store.add_properties(props)
        # With no embeddings, should use add_documents fallback
        vs.add_documents.assert_called_once()

    def test_add_properties_empty_list(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        assert store.add_properties([]) == 0

    def test_batching_respects_batch_size(self, tmp_path):
        vs = _mock_vector_store()
        vs._collection.get.return_value = {"ids": []}
        emb = _mock_embeddings()
        store = _make_store(tmp_path, embeddings=emb, vector_store=vs)

        props = [make_property(f"p{i}", "Krakow", 900 + i, 2) for i in range(5)]
        added = store.add_properties(props, batch_size=2)
        assert added == 5
        assert vs._collection.add.call_count == 3  # batches of 2,2,1


# ===================================================================
# add_properties() with a source of record
# ===================================================================


class TestAddPropertiesRefresh:
    """A source of record refreshes the listings it already published.

    The register publishes the prices people paid and the starosta corrects
    a deed where it stands, so the store has to take the newer listing under
    the id of the one it holds - a store that kept the old listing would
    offer a price the register no longer publishes.
    """

    def test_the_newer_listing_is_written_under_the_same_id(self, tmp_path):
        vs = _mock_vector_store()
        vs._collection.get.return_value = {"ids": ["p1"]}
        store = _make_store(tmp_path, embeddings=_mock_embeddings(), vector_store=vs)

        store.add_properties([make_property("p1", "Krakow", 950)], refresh=True)

        vs._collection.upsert.assert_called_once()
        call_kw = vs._collection.upsert.call_args.kwargs
        assert call_kw["ids"] == ["p1"]
        assert call_kw["metadatas"][0]["price"] == 950.0

    def test_a_refreshed_listing_is_not_a_new_one(self, tmp_path):
        vs = _mock_vector_store()
        vs._collection.get.return_value = {"ids": []}
        store = _make_store(tmp_path, embeddings=_mock_embeddings(), vector_store=vs)

        # The store takes the listing in.
        assert store.add_properties([make_property("p1", "Krakow", 900)]) == 1
        # The source publishes it again with another price: the listing was
        # there before, so it is not a new one.
        assert store.add_properties([make_property("p1", "Krakow", 950)], refresh=True) == 0

    def test_a_listing_that_is_not_refreshed_is_left_as_it_is(self, tmp_path):
        vs = _mock_vector_store()
        vs._collection.get.return_value = {"ids": ["p1"]}
        store = _make_store(tmp_path, embeddings=_mock_embeddings(), vector_store=vs)

        store.add_properties([make_property("p1", "Krakow", 950)])

        vs._collection.upsert.assert_not_called()
        vs._collection.add.assert_not_called()

    def test_the_first_of_two_listings_of_the_same_id_is_the_listing(self, tmp_path):
        """The register reads its sales most recent first."""
        vs = _mock_vector_store()
        vs._collection.get.return_value = {"ids": ["p1"]}
        store = _make_store(tmp_path, embeddings=_mock_embeddings(), vector_store=vs)

        store.add_properties(
            [
                make_property("p1", "Krakow", 950),
                make_property("p1", "Krakow", 500),
            ],
            refresh=True,
        )

        call_kw = vs._collection.upsert.call_args.kwargs
        assert call_kw["ids"] == ["p1"]
        assert len(call_kw["documents"]) == 1
        assert call_kw["metadatas"][0]["price"] == 950.0

    def test_two_listings_without_an_id_of_their_own_are_one_listing(self, tmp_path):
        """A listing without an identity cannot be told from another one."""
        vs = _mock_vector_store()
        vs._collection.get.return_value = {"ids": []}
        store = _make_store(tmp_path, embeddings=_mock_embeddings(), vector_store=vs)

        first = Property(city="Krakow", price=900.0, description="A flat without an id")
        second = Property(city="Krakow", price=950.0, description="Another flat without an id")

        store.add_properties([first, second], refresh=True)

        # The first one of the two is the listing: a listing without an id of
        # its own cannot be recognised, so the write carries one of them and
        # not both - two of them would be two writes under one id.
        call_kw = vs._collection.upsert.call_args.kwargs
        assert len(call_kw["documents"]) == 1
        assert call_kw["metadatas"][0]["price"] == 900.0

    def test_the_fallback_cache_carries_the_refreshed_listing(self, tmp_path):
        """The cache is what the store reads when the collection is away."""
        store = _make_store(tmp_path, embeddings=None, vector_store=None)

        store.add_properties([make_property("p1", "Krakow", 900)])
        store.add_properties([make_property("p1", "Krakow", 950)], refresh=True)

        assert len(store._documents) == 1
        assert store._documents[0].metadata["price"] == 950.0

    def test_a_write_that_fails_leaves_the_listing_the_cache_had(self, tmp_path):
        """The cache and the collection do not say different things about a listing."""
        vs = _mock_vector_store()
        vs._collection.get.return_value = {"ids": []}
        store = _make_store(tmp_path, embeddings=_mock_embeddings(), vector_store=vs)

        store.add_properties([make_property("p1", "Krakow", 900)])
        # The collection refuses the write.
        vs._collection.upsert.side_effect = RuntimeError("the collection is away")

        # The write that did not land is reported as a failure - a catalogue
        # that could not be written is not a catalogue that holds nothing.
        with pytest.raises(VectorStoreWriteError):
            store.add_properties([make_property("p1", "Krakow", 950)], refresh=True)

        # The cache keeps the listing it had, so the price the product shows
        # is the price the collection holds.
        assert store._documents[0].metadata["price"] == 900.0

    def test_a_listing_put_in_the_cache_by_another_road_is_found(self, tmp_path):
        """A listing the index does not name is found by its id."""
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        store.add_properties([make_property("p1", "Krakow", 900)])
        # The index of the cache does not know where the listing sits.
        store._doc_positions.clear()

        store.add_properties([make_property("p1", "Krakow", 950)], refresh=True)

        assert store._documents[0].metadata["price"] == 950.0
        assert store._doc_positions["p1"] == 0

    def test_a_place_that_names_another_listing_is_not_used(self, tmp_path):
        """The index does not point at another listing by mistake."""
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        store.add_properties([make_property("p1", "Krakow", 900)])
        # The place of the listing names another listing.
        store._doc_positions["p1"] = 5

        store.add_properties([make_property("p1", "Krakow", 950)], refresh=True)

        assert store._documents[0].metadata["price"] == 950.0
        assert len(store._documents) == 1

    def test_the_collection_without_embeddings_takes_the_newer_listing(self, tmp_path):
        """The write of the collection is an upsert, so the listing is replaced."""
        vs = _mock_vector_store()
        vs._collection.get.return_value = {"ids": []}
        store = _make_store(tmp_path, embeddings=None, vector_store=vs)

        store.add_properties([make_property("p1", "Krakow", 900)])
        store.add_properties([make_property("p1", "Krakow", 950)], refresh=True)

        vs.add_documents.assert_called()
        assert store._documents[0].metadata["price"] == 950.0

    def test_a_listing_the_cache_holds_the_id_of_but_not_the_listing_is_left_alone(self, tmp_path):
        """A listing the cache does not hold is not replaced by nothing."""
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        # The cache knows the id of the listing but does not hold it.
        store._doc_ids.add("p1")

        store.add_properties([make_property("p1", "Krakow", 950)], refresh=True)

        assert store._documents == []

    def test_clearing_the_store_forgets_the_places_of_the_listings(self, tmp_path):
        """A store that was cleared holds no listing, so it knows no place."""
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        store.add_properties([make_property("p1", "Krakow", 900)])
        assert store._doc_positions

        store.clear()

        assert store._doc_positions == {}
        assert store._documents == []

    def test_a_store_that_could_not_be_cleared_forgets_the_places_too(self, tmp_path):
        """Even a clear that failed leaves no place behind."""
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        store.add_properties([make_property("p1", "Krakow", 900)])
        store._get_vector_store = MagicMock(side_effect=RuntimeError("the collection is away"))

        store.clear()

        assert store._doc_positions == {}
        assert store._documents == []


# ===================================================================
# search_by_metadata()
# ===================================================================


class TestSearchByMetadata:
    """Tests for search_by_metadata()."""

    def test_search_by_metadata_with_vector_store(self, tmp_path):
        vs = _mock_vector_store()
        doc1 = Document(
            page_content="flat", metadata={"id": "p1", "city": "Krakow", "price": 900, "rooms": 2.0}
        )
        doc2 = Document(
            page_content="flat",
            metadata={"id": "p2", "city": "Krakow", "price": 1500, "rooms": 3.0},
        )
        vs.similarity_search.return_value = [doc1, doc2]

        store = _make_store(tmp_path, embeddings=_mock_embeddings(), vector_store=vs)
        results = store.search_by_metadata(city="Krakow", min_price=500, max_price=1000, k=5)
        assert len(results) == 1
        assert results[0].metadata["id"] == "p1"

    def test_search_by_metadata_with_min_rooms(self, tmp_path):
        vs = _mock_vector_store()
        doc1 = Document(page_content="flat", metadata={"id": "p1", "price": 900, "rooms": 3.0})
        doc2 = Document(page_content="flat", metadata={"id": "p2", "price": 800, "rooms": 1.0})
        vs.similarity_search.return_value = [doc1, doc2]

        store = _make_store(tmp_path, embeddings=_mock_embeddings(), vector_store=vs)
        results = store.search_by_metadata(min_rooms=2.0, k=5)
        assert len(results) == 1
        assert results[0].metadata["id"] == "p1"

    def test_search_by_metadata_fallback_no_vs(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        doc1 = Document(
            page_content="flat",
            metadata={
                "id": "p1",
                "city": "Krakow",
                "price": 900,
                "rooms": 2.0,
                "has_parking": True,
            },
        )
        doc2 = Document(
            page_content="flat",
            metadata={
                "id": "p2",
                "city": "Warsaw",
                "price": 1200,
                "rooms": 3.0,
                "has_parking": False,
            },
        )
        store._documents = [doc1, doc2]

        results = store.search_by_metadata(city="Krakow", has_parking=True, k=5)
        assert len(results) == 1
        assert results[0].metadata["id"] == "p1"

    def test_search_by_metadata_fallback_filters_price(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        doc1 = Document(
            page_content="flat",
            metadata={"id": "p1", "price": 500, "rooms": 2.0},
        )
        doc2 = Document(
            page_content="flat",
            metadata={"id": "p2", "price": 2000, "rooms": 2.0},
        )
        store._documents = [doc1, doc2]

        results = store.search_by_metadata(min_price=300, max_price=1000, k=5)
        assert len(results) == 1
        assert results[0].metadata["id"] == "p1"

    def test_search_by_metadata_fallback_skips_no_price(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        doc = Document(page_content="flat", metadata={"id": "p1", "rooms": 2.0})
        store._documents = [doc]

        results = store.search_by_metadata(min_price=100, k=5)
        assert results == []

    def test_search_by_metadata_fallback_respects_k(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        docs = [
            Document(
                page_content="flat",
                metadata={"id": f"p{i}", "price": 500.0 + i, "rooms": 2.0},
            )
            for i in range(10)
        ]
        store._documents = docs

        results = store.search_by_metadata(min_price=0, max_price=10000, k=3)
        assert len(results) == 3

    def test_search_by_metadata_has_parking_false(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        doc1 = Document(
            page_content="flat",
            metadata={"id": "p1", "price": 900, "rooms": 2.0, "has_parking": True},
        )
        doc2 = Document(
            page_content="flat",
            metadata={"id": "p2", "price": 800, "rooms": 2.0, "has_parking": False},
        )
        store._documents = [doc1, doc2]

        results = store.search_by_metadata(has_parking=False, k=5)
        assert len(results) == 1
        assert results[0].metadata["id"] == "p2"


# ===================================================================
# _build_chroma_filter()
# ===================================================================


class TestBuildChromaFilter:
    """Tests for _build_chroma_filter()."""

    def test_empty_filter_returns_none(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        assert store._build_chroma_filter({}) is None

    def test_single_condition_no_and(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        result = store._build_chroma_filter({"city": "Krakow"})
        assert result == {"city": "Krakow"}

    def test_multiple_conditions_use_and(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        result = store._build_chroma_filter({"city": "Krakow", "min_price": 500})
        assert "$and" in result

    def test_price_range_conditions(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        result = store._build_chroma_filter({"min_price": 500, "max_price": 1500})
        assert "$and" in result
        conditions = result["$and"]
        assert {"price": {"$gte": 500.0}} in conditions
        assert {"price": {"$lte": 1500.0}} in conditions

    def test_rooms_filter(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        result = store._build_chroma_filter({"rooms": 3})
        assert result == {"rooms": {"$gte": 3.0}}

    def test_year_built_range(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        result = store._build_chroma_filter({"year_built_min": 2000, "year_built_max": 2020})
        conditions = result["$and"]
        assert {"year_built": {"$gte": 2000}} in conditions
        assert {"year_built": {"$lte": 2020}} in conditions

    def test_amenity_filters(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        result = store._build_chroma_filter({"has_parking": True, "has_garden": False})
        conditions = result["$and"]
        assert {"has_parking": True} in conditions
        assert {"has_garden": False} in conditions

    def test_energy_ratings_single(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        result = store._build_chroma_filter({"energy_ratings": ["A"]})
        assert result == {"energy_cert": "A"}

    def test_energy_ratings_multiple(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        result = store._build_chroma_filter({"energy_ratings": ["A", "B"]})
        assert result == {"energy_cert": {"$in": ["A", "B"]}}

    def test_property_type_filter(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        result = store._build_chroma_filter({"property_type": PropertyType.HOUSE})
        assert result == {"property_type": "house"}


# ===================================================================
# Geo helpers: _build_geo_filter, _build_bbox_filter, _haversine, _point_in_polygon
# ===================================================================


class TestGeoHelpers:
    """Tests for geographic filter helpers."""

    def test_build_geo_filter(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        conditions = store._build_geo_filter(50.06, 19.94, 10.0)
        assert len(conditions) == 4
        # Should have lat/lon gte/lte conditions
        keys = [list(c.keys())[0] for c in conditions]
        assert "lat" in keys
        assert "lon" in keys

    def test_build_geo_filter_clamps_lat(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        # Near the pole, should clamp to avoid division by zero
        conditions = store._build_geo_filter(89.5, 0.0, 10.0)
        assert len(conditions) == 4

    def test_build_bbox_filter_all_params(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        conditions = store._build_bbox_filter(50.0, 51.0, 19.0, 20.0)
        assert len(conditions) == 4

    def test_build_bbox_filter_partial(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        conditions = store._build_bbox_filter(50.0, None, 19.0, None)
        assert len(conditions) == 2

    def test_build_bbox_filter_all_none(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        conditions = store._build_bbox_filter(None, None, None, None)
        assert conditions == []

    def test_haversine_known_distance(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        # Krakow (50.06, 19.94) to Warsaw (52.23, 21.01) ~260 km
        dist = store._haversine(50.06, 19.94, 52.23, 21.01)
        assert 250 < dist < 280

    def test_haversine_zero_distance(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        dist = store._haversine(50.0, 20.0, 50.0, 20.0)
        assert dist == 0.0

    def test_point_in_polygon_inside(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        # Simple square: lon 0-1, lat 0-1
        polygon = [[0, 0], [1, 0], [1, 1], [0, 1]]
        assert store._point_in_polygon(0.5, 0.5, polygon) is True

    def test_point_in_polygon_outside(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        polygon = [[0, 0], [1, 0], [1, 1], [0, 1]]
        assert store._point_in_polygon(2.0, 2.0, polygon) is False

    def test_point_in_polygon_too_few_points(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        assert store._point_in_polygon(0.5, 0.5, [[0, 0], [1, 0]]) is False


# ===================================================================
# get_retriever()
# ===================================================================


class TestGetRetriever:
    """Tests for get_retriever()."""

    def test_returns_vector_retriever_when_db_has_docs(self, tmp_path):
        vs = _mock_vector_store()
        vs._collection.count.return_value = 5
        mock_retriever = MagicMock()
        vs.as_retriever.return_value = mock_retriever

        store = _make_store(tmp_path, embeddings=_mock_embeddings(), vector_store=vs)
        retriever = store.get_retriever(k=3)

        assert retriever is mock_retriever
        vs.as_retriever.assert_called_once()

    def test_returns_fallback_retriever_when_no_docs(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        doc = Document(page_content="apartment Krakow garden", metadata={"id": "p1"})
        store._documents = [doc]

        retriever = store.get_retriever(k=3)
        results = retriever.invoke("apartment Krakow")
        assert len(results) == 1
        assert results[0].metadata["id"] == "p1"


# ===================================================================
# __repr__()
# ===================================================================


class TestRepr:
    def test_repr_format(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        r = repr(store)
        assert "ChromaPropertyStore" in r
        assert "properties" in r


# ===================================================================
# get_vector_store() module-level function
# ===================================================================


class TestGetVectorStoreModuleFunction:
    """Tests for the module-level get_vector_store() function."""

    def test_uses_settings_embedding_model(self, tmp_path):
        from vector_store import chroma_store as mod

        with (
            patch.object(ChromaPropertyStore, "_create_embeddings", return_value=None),
            patch.object(ChromaPropertyStore, "_initialize_vector_store", return_value=None),
            patch.object(mod, "settings") as mock_settings,
        ):
            mock_settings.embedding_model = "test-model"
            store = mod.get_vector_store(persist_directory=str(tmp_path))
            assert isinstance(store, ChromaPropertyStore)


# ===================================================================
# _get_vector_store() thread-local behavior
# ===================================================================


class TestGetVectorStoreInternal:
    """Tests for the _get_vector_store() thread-local resolution."""

    def test_returns_main_when_thread_local_none(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        store.vector_store = "main_store"
        store._vector_store_local.store = None
        assert store._get_vector_store() == "main_store"

    def test_returns_thread_local_when_set(self, tmp_path):
        store = _make_store(tmp_path, embeddings=None, vector_store=None)
        store.vector_store = "main_store"
        store._vector_store_local.store = "thread_store"
        assert store._get_vector_store() == "thread_store"


# ===================================================================
# clear() with vector store
# ===================================================================


class TestClearWithVectorStore:
    def test_clear_resets_vector_store(self, tmp_path):
        vs = _mock_vector_store()
        new_vs = _mock_vector_store()
        new_vs._collection.count.return_value = 0

        store = _make_store(tmp_path, embeddings=_mock_embeddings(), vector_store=vs)
        store._initialize_vector_store = MagicMock(return_value=new_vs)
        store._documents = [Document(page_content="t", metadata={"id": "1"})]

        store.clear()
        vs.delete_collection.assert_called_once()
        assert store.vector_store is new_vs
        assert len(store._documents) == 0
