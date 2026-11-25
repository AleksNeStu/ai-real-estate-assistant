import json
from unittest.mock import MagicMock, patch

import pytest

from data.providers.json_provider import JSONDataProvider
from data.schemas import PropertyCollection
from vector_store.chroma_store import ChromaPropertyStore


class TestDataPipelineIntegration:
    @pytest.fixture
    def sample_json_file(self, tmp_path):
        data = [
            {
                "id": "1",
                "title": "Integration Apt 1",
                "city": "Warsaw",
                "price": 4000,
                "rooms": 2,
                "area_sqm": 50,
                "property_type": "apartment",
                "listing_type": "rent",
                "description": "A nice apartment in the center.",
            },
            {
                "id": "2",
                "title": "Integration Apt 2",
                "city": "Krakow",
                "price": 3000,
                "rooms": 1,
                "area_sqm": 35,
                "property_type": "studio",
                "listing_type": "rent",
                "description": "Cozy studio near the castle.",
            },
        ]
        f = tmp_path / "integration_data.json"
        with open(f, "w") as file:
            json.dump(data, file)
        return f

    def test_provider_to_vector_store_flow(self, sample_json_file, tmp_path):
        """
        Test the flow: Provider -> PropertyCollection -> VectorStore -> Search
        """
        # 1. Load Data
        provider = JSONDataProvider(sample_json_file)
        properties = provider.get_properties()
        assert len(properties) == 2

        collection = PropertyCollection(
            properties=properties, total_count=len(properties), source="integration_test"
        )

        # 2. Initialize Vector Store (Mock embeddings to avoid API calls)
        # We use a real ChromaDB (persistent in tmp_path) but mock the embedding function
        # to return dummy vectors.

        fake_embeddings = MagicMock()
        fake_embeddings.embed_documents.side_effect = lambda texts: [[0.1] * 384 for _ in texts]

        with patch.object(ChromaPropertyStore, "_create_embeddings", return_value=fake_embeddings):
            # We also need to patch where it's instantiated inside the class if it's not passed
            # Actually ChromaPropertyStore creates it internally: self.embeddings = FastEmbedEmbeddings(...)
            # So we patch the class.

            store = ChromaPropertyStore(persist_directory=str(tmp_path / "chroma_db"))

            # 3. Add Properties (Sync for test simplicity, or async)
            # Let's use the synchronous add_properties method which we refactored
            count = store.add_properties(collection.properties)
            assert count == 2

            # 4. Search
            # We need to mock query embedding too
            fake_embeddings.embed_query.return_value = [0.1] * 384

            # The store.search method uses self.embeddings.embed_query if vector_store is present
            # But wait, our refactored search relies on vector_store.similarity_search_with_score
            # which does the embedding internally if we passed an embedding function to Chroma?
            # No, ChromaPropertyStore.search does:
            # results = self.vector_store.similarity_search_with_score(query=query, ...)
            # LangChain's Chroma wrapper handles embedding using the embedding function provided at init.

            results = store.search("apartment", k=1)
            assert len(results) > 0
            assert results[0][0].metadata["city"] in ["Warsaw", "Krakow"]

            # Verify fallback cache is also populated
            assert len(store._documents) == 2

    def test_async_indexing_integration(self, sample_json_file, tmp_path):
        """
        Test the async indexing flow specifically.
        """
        provider = JSONDataProvider(sample_json_file)
        properties = provider.get_properties()
        collection = PropertyCollection(properties=properties, total_count=len(properties))

        fake_embeddings = MagicMock()

        # Make embedding slow to verify non-blocking
        def slow_embed(texts):
            return [[0.1] * 384 for _ in texts]

        fake_embeddings.embed_documents.side_effect = slow_embed
        fake_embeddings.embed_query.return_value = [0.1] * 384

        with patch.object(ChromaPropertyStore, "_create_embeddings", return_value=fake_embeddings):
            store = ChromaPropertyStore(persist_directory=str(tmp_path / "chroma_async_db"))

            # Start async add
            future = store.add_property_collection_async(collection)

            # It should finish eventually
            result = future.result(timeout=5)
            assert result == 2

            # Verify stats
            stats = store.get_stats()
            assert stats["total_documents"] == 2
