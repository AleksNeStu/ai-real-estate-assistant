"""A catalogue that could not be written is not a catalogue that holds nothing.

The store used to log the failure of a batch and carry on, and to answer an
empty list when the collection could not be read. Both answers are the same
answer the collection gives when it holds nothing, so a caller - and a test -
could not tell a catalogue that is empty from a catalogue that is broken.

The failure is the answer now: a write that landed only in part raises, and a
read that could not be answered raises unless the cache can answer it.
"""

from unittest.mock import MagicMock, patch

import pytest

from data.schemas import Property, PropertyCollection, PropertyType
from vector_store.chroma_store import (
    ChromaPropertyStore,
    VectorStoreUnavailable,
    VectorStoreWriteError,
)


def make_property(pid: str, city: str = "Krakow") -> Property:
    return Property(  # type: ignore[call-arg]
        id=pid,
        city=city,
        price=900,
        rooms=2,
        bathrooms=1,
        area_sqm=50,
        property_type=PropertyType.APARTMENT,
        description="a flat with a balcony",
    )


def a_store_with_a_failing_collection(tmp_path, failing_method: str) -> ChromaPropertyStore:
    """A store whose collection fails on one method and answers on the rest."""
    with patch.object(ChromaPropertyStore, "_create_embeddings", return_value=None):
        store = ChromaPropertyStore(persist_directory=str(tmp_path))

    collection = MagicMock()
    if failing_method == "add":
        collection.add.side_effect = RuntimeError("the collection is not answering")
        collection.upsert.side_effect = RuntimeError("the collection is not answering")
    else:
        collection.get.side_effect = RuntimeError("the collection is not answering")

    vector_store = MagicMock()
    vector_store._collection = collection
    if failing_method == "add":
        # The store writes through the collection when it has embeddings and
        # through the vector store when it has none; both have to fail.
        vector_store.add_documents.side_effect = RuntimeError("the collection is not answering")
    store.vector_store = vector_store
    store._vector_store_local.store = vector_store
    return store


class TestAWriteThatLandedOnlyInPart:
    def test_the_write_says_so_instead_of_reporting_success(self, tmp_path):
        store = a_store_with_a_failing_collection(tmp_path, "add")

        collection = PropertyCollection(
            properties=[make_property("p1"), make_property("p2")],
            total_count=2,
        )

        with pytest.raises(VectorStoreWriteError) as failure:
            store.add_property_collection(collection)

        # The message names what did not land, so the caller can say it.
        assert "could not be written" in str(failure.value)
        assert "listings did not land" in str(failure.value)


class TestAReadThatCouldNotBeAnswered:
    def test_an_unreadable_catalogue_is_not_an_empty_one(self, tmp_path):
        store = a_store_with_a_failing_collection(tmp_path, "get")

        with pytest.raises(VectorStoreUnavailable):
            store.get_properties_by_ids(["p1"])

    def test_the_cache_answers_when_the_collection_cannot(self, tmp_path):
        store = a_store_with_a_failing_collection(tmp_path, "get")

        # The cache is what the store falls back to when the collection is
        # not there at all, so it is what it falls back to when the
        # collection fails.
        store._documents.append(store.property_to_document(make_property("p1")))

        documents = store.get_properties_by_ids(["p1"])

        assert [doc.metadata["id"] for doc in documents] == ["p1"]
